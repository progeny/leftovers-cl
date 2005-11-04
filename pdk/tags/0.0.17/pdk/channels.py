#   Copyright 2005 Progeny Linux Systems, Inc.
#
#   This file is part of PDK.
#
#   PDK is free software; you can redistribute it and/or modify it
#   under the terms of the GNU General Public License as published by
#   the Free Software Foundation; either version 2 of the License, or
#   (at your option) any later version.
#
#   PDK is distributed in the hope that it will be useful, but WITHOUT
#   ANY WARRANTY; without even the implied warranty of MERCHANTABILITY
#   or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public
#   License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with PDK; if not, write to the Free Software Foundation,
#   Inc., 51 Franklin St, Fifth Floor, Boston, MA 02110-1301 USA

"""
The outside world is divided into remote workspaces and channels.

Both of these break down into sections, which contain information about
available packages.

Remote workspaces are treated purely as piles of downloadable
blobs. Channels contain more information about the packages available,
and are useful as sources for resolving.

The result of parsing configuration is a WorldData object.

OutsideWorldFactory consumes WorldData to create OutsideWorld.

OutsideWorld is able to filter all known packages by channel name and
provides a filtered iterator to do so.

OutsideWorld is also able to provide appropriate locator objects for a
given blob_id.

Locators take care of providing urls where packages may be
downloaded. They also take care of finding new locators for extra
files needed by dsc packages.

"""

import os
pjoin = os.path.join
import re
from urlparse import urlsplit
from gzip import GzipFile
from md5 import md5
import apt_pkg
from xml.parsers.expat import ExpatError
from pdk.exceptions import InputError, SemanticError
from pdk.util import cpath, gen_file_fragments, get_remote_file, \
     shell_command, Framer, make_fs_framer, make_ssh_framer, cached_property
from pdk.yaxml import parse_yaxml_file
from pdk.package import deb, udeb, dsc, get_package_type, \
     UnknownPackageTypeError
from pdk.meta import ComponentMeta

def quote(raw):
    '''Create a valid filename which roughly resembles the raw string.'''
    return re.sub(r'[^A-Za-z0-9.-]+', '_', raw)

class MissingChannelDataError(SemanticError):
    '''Raised when a required channel data file is missing.

    Only used for real channels, not remote workspaces.
    '''
    pass

class LoaderFactory(tuple):
    '''Captures parameters to later create a cache loader.

    cls is the cache loader class. Remaining parameters are passed to
    the constructor of the cache loader.

    The objects should be memory efficient, comparable, and hashable.
    '''
    def __new__(cls, loader_class, *params):
        return tuple.__new__(cls, (loader_class, tuple(params)))

    def create_loader(self, locators):
        '''Create a locator with the captured pa'''
        loader_class, params = self
        return loader_class(locators = locators, *params)

class URLCacheLoader(object):
    '''A cache loader which downloads raw files via curl or direct copy.
    '''
    def __init__(self, locators):
        self.locators = locators

    def load(self, cache):
        '''Import assigned blobs into the cache.

        Actually the framer strems zero blobs, as the "remote" side of
        the framer is downloading files directly into the cache.
        '''
        for locator in self.locators:
            if locator.blob_id not in cache:
                cache.import_file(locator)

class LocalWorkspaceCacheLoader(object):
    '''A cache loader for working with a remote workspace on this machine.
    '''
    def __init__(self, path, locators):
        self.path = path
        self.locators = locators

    def load(self, cache):
        '''Use a framer to stream the assigned blobs into a cache.'''
        blob_ids = [ l.blob_id for l in self.locators ]
        framer = Framer(*shell_command('pdk remote listen %s'
                                         % self.path))
        framer.write_stream(['pull-blobs'])
        framer.write_stream(blob_ids)
        framer.write_stream(['done'])
        cache.import_from_framer(framer)

class SshWorkspaceCacheLoader(object):
    '''A cache loader for working with a remote workspace via ssh.
    '''
    def __init__(self, host, path, locators):
        self.host = host
        self.path = path
        self.locators = locators

    def load(self, cache):
        '''Use a framer to stream the assigned blobs into a cache.'''
        blob_ids = [ l.blob_id for l in self.locators ]
        framer = Framer(*shell_command('ssh %s pdk remote listen %s'
                                         % (self.host, self.path)))
        framer.write_stream(['pull-blobs'])
        framer.write_stream(blob_ids)
        framer.write_stream(['done'])
        cache.import_from_framer(framer)

class FileLocator(object):
    '''Represents a resource which can be imported into the cache.'''
    def __init__(self, base_uri, filename, expected_blob_id, factory):
        self.base_uri = base_uri
        self.filename = filename
        self.blob_id = expected_blob_id
        self.loader_factory = factory

    def make_extra_file_locator(self, filename, expected_blob_id):
        '''Make a new locator which shares the base_uri or this locator.'''
        return FileLocator(self.base_uri, filename, expected_blob_id,
                           self.loader_factory)

    def __cmp__(self, other):
        return cmp((self.base_uri, self.filename, self.blob_id),
                   (other.base_uri, other.filename, other.blob_id))

    def get_full_url(self):
        '''Get the full url for the located file.'''
        parts = [ p for p in (self.base_uri, self.filename) if p ]
        return '/'.join(parts)

class CacheFileLocator(object):
    '''Represents a remote cached resource for import into this cache.'''
    def __init__(self, base_uri, filename, expected_blob_id, factory):
        self.base_uri = base_uri
        self.filename = filename
        self.blob_id = expected_blob_id
        self.loader_factory = factory

    def __cmp__(self, other):
        return cmp((self.base_uri, self.filename, self.blob_id),
                   (other.base_uri, other.filename, other.blob_id))

    def get_full_url(self):
        '''Get the full url for the located file.'''
        parts = [ p for p in (self.base_uri, self.filename) if p ]
        return '/'.join(parts)

def make_comparable(cls, id_fields = None):
    '''Makes a class comparable on the given identity fields.

    If the id_fields are omitted then the class must provide a
    get_identity method which returns a tuple of values.
    '''
    if hasattr(cls, 'get_identity'):
        get_identity = cls.get_identity
    else:
        def get_identity(self):
            '''Return a tuple representing the "identity" of the object.'''
            identity = []
            for field in id_fields:
                identity.append(getattr(self, field))
            return tuple(identity)

    def __cmp__(self, other):
        class_cmp = cmp(self.__class__, other.__class__)
        if class_cmp:
            return class_cmp
        self_id = get_identity(self)
        other_id = get_identity(other)
        return cmp(self_id, other_id)

    def __hash__(self):
        return hash(get_identity(self))

    def __repr__(self):
        return '<%s %r>' % (self.__class__.__name__, get_identity(self))

    cls.__cmp__ = __cmp__
    cls.__hash__ = __hash__
    cls.__repr__ = __repr__
    cls.__str__ = __repr__

class AptDebSection(object):
    '''Section for managing a single Packages or Sources file.

    Requires a strategy object which controls whether the url will
    be treated as Packages or Sources.
    '''

    def __init__(self, full_path, channel_file, strategy):
        self.full_path = full_path
        self.channel_file = channel_file
        self.strategy = strategy

    def get_identity(self):
        '''Return an identity tuple for this object.'''
        return (self.strategy.package_type, self.full_path)

    def update(self):
        '''Grab the remote file and store it locally.'''
        get_remote_file(self.full_path, self.channel_file, True)

    def iter_package_info(self):
        '''Iterate over ghost_package, blob_id, locator for this section.'''
        if not os.path.exists(self.channel_file):
            raise MissingChannelDataError, self.channel_file
        tags_iterator = self.iter_apt_tags()
        for package in \
                self.iter_as_packages(tags_iterator):
            locator = self.strategy.get_locator(package)
            package.blob_id = locator.blob_id
            yield package, locator.blob_id, locator
            if hasattr(package, 'extra_file'):
                for extra_blob_id, extra_filename in package.extra_file:
                    make_extra = locator.make_extra_file_locator
                    extra_locator = make_extra(extra_filename,
                                               extra_blob_id)
                    yield None, extra_blob_id, extra_locator

    def iter_apt_tags(self):
        '''Iterate over apt tag section objects in self.channel_file.'''
        handle = os.popen('gunzip <%s' % self.channel_file)
        apt_iterator = apt_pkg.ParseTagFile(handle)
        while apt_iterator.Step():
            yield apt_iterator.Section
        handle.close()

    def iter_as_packages(self, tags_iterator):
        """For each control or header, yield a stream of package objects."""
        for tags in tags_iterator:
            meta = ComponentMeta()
            yield self.strategy.package_type.parse_tags(meta, tags, None)

make_comparable(AptDebSection, ('full_path', 'base_path'))

class AptDebBinaryStrategy(object):
    '''Handle get_locator and package_type for AptDebSection

    Used for Packages files.
    '''
    package_type = deb
    loader_factory = LoaderFactory(URLCacheLoader)

    def __init__(self, base_path):
        self.base_path = base_path

    def get_locator(self, package):
        """Return base, filename, blob_id for a package"""
        return FileLocator(self.base_path, package.raw_filename,
                           package.blob_id, self.loader_factory)

class AptUDebBinaryStrategy(AptDebBinaryStrategy):
    '''Handle get_locator and package_type for AptDebSection

    Used for Packages files in debian-installer sections. (udebs)
    '''
    package_type = udeb

class AptDebSourceStrategy(object):
    '''Handle get_locator and package_type for AptDebSection

    Used for Sources files.
    '''
    package_type = dsc
    loader_factory = LoaderFactory(URLCacheLoader)

    def __init__(self, base_path):
        self.base_path = base_path

    def get_locator(self, package):
        """Return base, filename, blob_id for a package"""
        base = self.base_path + package.directory
        return FileLocator(base, package.raw_filename, package.blob_id,
                           self.loader_factory)

class DirectorySection(object):
    '''Section object for dealing with local directories as channels.'''

    loader_factory = LoaderFactory(URLCacheLoader)

    def __init__(self, full_path):
        self.full_path = full_path

    def update(self):
        """Since the files are local, don't bother storing workspace state.
        """
        pass

    def iter_package_info(self):
        '''Iterate over ghost_package, blob_id, locator for this section.

        The directory is visited recursively and in a repeatable order.
        '''
        for root, dirnames, files in os.walk(self.full_path,
                                             topdown = True):
            dirnames.sort()
            files.sort()
            for candidate in files:
                full_path = pjoin(root, candidate)
                try:
                    package_type = get_package_type(filename = candidate)
                except UnknownPackageTypeError:
                    # if we don't know the the file is, we skip it.
                    continue
                control = package_type.extract_header(full_path)
                iterator = gen_file_fragments(full_path)
                md51_digest = md5()
                for block in iterator:
                    md51_digest.update(block)
                blob_id = 'md5:' + md51_digest.hexdigest()
                url = 'file://' + cpath(root)
                locator = FileLocator(url, candidate, None,
                                      self.loader_factory)
                meta = ComponentMeta()
                package = package_type.parse(meta, control, blob_id)
                yield package, blob_id, locator
                if hasattr(package, 'extra_file'):
                    for extra_blob_id, extra_filename in package.extra_file:
                        make_extra = locator.make_extra_file_locator
                        extra_locator = make_extra(extra_filename,
                                                   extra_blob_id)
                        yield None, extra_blob_id, extra_locator


make_comparable(DirectorySection, ('full_path',))

class RemoteWorkspaceSection(object):
    '''Read the remote cache_info list from a source.'''
    def __init__(self, path, channel_file):
        self.full_path = path
        self.channel_file = channel_file

        parts = urlsplit(self.full_path)
        if parts[1]:
            self.loader_factory = LoaderFactory(SshWorkspaceCacheLoader,
                                                parts[1], parts[2])
        else:
            self.loader_factory = LoaderFactory(LocalWorkspaceCacheLoader,
                                                self.full_path)

    def update(self):
        '''A noop for this section type.

        Remote workspaces are updated at pull time.
        '''
        pass

    def iter_package_info(self):
        '''Iterate over blob_id, locator for this section.

        The package object is set to None as it is not know for this kind
        of section.
        '''
        cache_url = '/'.join([self.full_path, 'cache'])
        if not os.path.exists(self.channel_file):
            return
        gunzipped = GzipFile(self.channel_file)

        for line in gunzipped:
            blob_id, blob_path = line.strip().split()
            locator = CacheFileLocator(cache_url, blob_path, blob_id,
                                       self.loader_factory)
            yield None, blob_id, locator

    def get_framer(self):
        '''Get a framer suitable for communicating with this workspace.'''
        path = self.full_path
        parts = urlsplit(path)
        if parts[0] == 'file' and parts[1]:
            framer = make_ssh_framer(parts[1], parts[2])
        else:
            framer = make_fs_framer(path)
        return framer

make_comparable(RemoteWorkspaceSection, ('full_path',))

class WorldData(object):
    """Represents all configuration data known about the outside world.

    Contructed from a dict in in the form of:
        world_dict = {
            'local': { 'type': 'dir',
                       'path': '.../directory' },
            'remote': { 'type': 'apt-deb',
                        'path': 'http://baseaptrepo/',
                        'dist': 'stable',
                        'components': 'main contrib non-free',
                        'archs': 'source i386' },
            'source': { 'type': 'source',
                        'path': 'http://pathtosource/' }
         }

    Use this object as an iterator to get at the more useful form of the
    data.

    iter(world_data) -> [ name, data_dict]
    data_dict is the individual data_dict for the given channel or source.
    Each data_dict must have keys type and path. Certain types may require
    more keys.
    """
    def __init__(self, world_dict):
        self.world_dict = world_dict

    def load_from_stored(channel_data_file):
        '''Load and construct an object from file stored in a workspace.'''
        try:
            channels = parse_yaxml_file(channel_data_file)
        except ExpatError, message:
            raise InputError("In %s, %s" % (channel_data_file, message))
        except IOError, error:
            if error.errno == 2:
                channels = {}
        return WorldData(channels)

    load_from_stored = staticmethod(load_from_stored)

    def __iter__(self):
        for key, value in self.world_dict.iteritems():
            yield key, value

class OutsideWorldFactory(object):
    """Creates an OutsideWorld object from WorldData and a channel_dir."""
    def __init__(self, world_data, channel_dir):
        self.world_data = world_data
        self.channel_dir = channel_dir

    def create(self):
        """Create and return the OutsideWorld object."""
        sections = {}

        for name, data_dict in self.world_data:
            sections[name] = []
            for section in self.iter_sections(name, data_dict):
                sections[name].append(section)

        return OutsideWorld(sections)

    def get_channel_file(self, path):
        """Get the full path to the file representing the given path."""
        return os.path.join(self.channel_dir, quote(path))

    def iter_sections(self, channel_name, data_dict):
        """Create sections for the given channel name and dict."""
        type_value = None
        try:
            type_value = data_dict['type']
        except KeyError, message:
            raise InputError('%s has no type' % channel_name)

        try:
            path = data_dict['path']
            if type_value == 'apt-deb':
                if path[-1] != "/":
                    message = "path in channels.xml must end in a slash"
                    raise InputError, message
                dist = data_dict['dist']
                components = data_dict['components'].split()
                archs = data_dict['archs'].split()
                for component in components:
                    for arch in archs:
                        # note that '/debian-installer' is treated as
                        # kind of "magic" here, because it is a magic name
                        # in debian repos.
                        if arch == 'source':
                            if '/debian-installer' in component:
                                continue
                            arch_part = 'source'
                            filename = 'Sources.gz'
                            strategy = AptDebSourceStrategy(path)
                        else:
                            arch_part = 'binary-%s' % arch
                            filename = 'Packages.gz'
                            if '/debian-installer' in component:
                                strategy = AptUDebBinaryStrategy(path)
                            else:
                                strategy = AptDebBinaryStrategy(path)

                        parts = [path[:-1], 'dists', dist, component,
                                 arch_part, filename]
                        full_path = '/'.join(parts)
                        channel_file = self.get_channel_file(full_path)
                        yield AptDebSection(full_path, channel_file,
                                            strategy)
            elif type_value == 'dir':
                yield DirectorySection(path)
            elif type_value == 'source':
                yield RemoteWorkspaceSection(path,
                                             self.get_channel_file(path))
            else:
                raise InputError('channel %s has unrecognized type %s'
                                 % (channel_name, type_value))
        except KeyError, field:
            message = 'channel "%s" missing field "%s"' % (channel_name,
                                                           str(field))
            raise InputError(message)

class WorldItem(object):
    '''Represents a single package/locator item in the outside world.

    Some items have no package object.

    When package is present it is a "ghost", meaning we can query it
    like a pdk.package.Package object, but we do not have a file in
    the cache backing it.
    '''
    def __init__(self, section_name, package, blob_id, locator):
        self.section_name = section_name
        self.package = package
        self.blob_id = blob_id
        self.locator = locator

class OutsideWorld(object):
    '''This object represents the world outside the workspace.'''
    def __init__(self, sections):
        self.sections = sections

    def get_workspace_section(self, name):
        '''Get the named workspace section.'''
        if name not in self.sections:
            raise SemanticError('%s is not known workspace' % name)
        section = self.sections[name][0]
        if section.__class__ != RemoteWorkspaceSection:
            raise SemanticError('%s is a channel, not a workspace' % name)
        return section

    def get_cache_loaders(self, blob_ids):
        '''Get a set of cache loaders for the given blob_ids.

        Each loader roughly corresponds to a download session.
        '''
        locators = []
        by_blob_id = self.all_package_info.by_blob_id
        for blob_id in blob_ids:
            if blob_id in by_blob_id:
                locators.append(by_blob_id[blob_id].locator)
            else:
                raise SemanticError, \
                      "could not find %s in any channel" % blob_id

        by_factory = {}
        for locator in locators:
            locator_list = by_factory.setdefault(locator.loader_factory, [])
            locator_list.append(locator)

        cache_loaders = []
        for factory, locators in by_factory.iteritems():
            cache_loaders.append(factory.create_loader(locators))
        return cache_loaders

    def get_backed_cache(self, cache):
        '''Return a ChannelBackedCache for this object and the given cache.
        '''
        return ChannelBackedCache(self, cache)

    def fetch_world_data(self):
        '''Update all remote source and channel data.'''
        for dummy, section in self.iter_sections():
            section.update()

    def __create_all_package_info(self):
        '''Capture the full state of all sections. Index it.

        Returns a tuple containing the raw data + all indexes.
        '''
        data = IndexedWorldData.build(self.iter_sections())
        return data
    all_package_info = cached_property('all_package_info',
                                       __create_all_package_info)

    def get_limited_index(self, given_section_names):
        '''Return IndexedWorldData like object but limited by channel names.
        '''
        section_names = [ t[0]
                          for t in self.iter_sections(given_section_names) ]
        return LimitedWorldDataIndex(self.all_package_info, section_names)

    def iter_sections(self, section_names = None):
        '''Iterate over stored sections for the given section_names.'''
        if not section_names:
            section_names = self.sections.keys()
            section_names.sort()
        for name in section_names:
            try:
                for section in self.sections[name]:
                    yield name, section
            except KeyError, e:
                raise InputError("Unknown channel %s." % str(e))

class ChannelBackedCache(object):
    '''Impersonate a cache but use both channels and cache to load packages.
    '''
    def __init__(self, world, cache):
        self.world = world
        self.cache = cache

    def load_package(self, meta, blob_id, type_string):
        '''Behave like Cache.load_packages.

        Tries to load from local cache before looking for a package object
        in the channels.
        '''
        if blob_id in self.cache:
            return self.cache.load_package(meta, blob_id, type_string)

        by_blob_id = self.world.all_package_info.by_blob_id
        if blob_id in by_blob_id:
            item = by_blob_id[blob_id]
            if item.package:
                return item.package

        message = "Can't find package (%s, %s).\n" % (type_string, blob_id)
        message += 'Consider reverting and reattempting this command.'
        raise SemanticError(message)

class IndexedWorldData(object):
    '''Wrap up storing all the channel data.

    Provides a number of field indexes on an otherwise too large list
    of WorldDataItems.
    '''
    def __init__(self, raw_package_info, field_indexes, by_blob_id):
        self.raw_package_info = raw_package_info
        self.field_indexes = field_indexes
        self.by_blob_id = by_blob_id

    def get_candidates(self, key_field, key, section_names):
        '''Get a list of WorldDataItems.

        Use the index named by key_field, with the given key. Return
        only the list of items found by that key.
        '''
        index = self.field_indexes[key_field]

        candidate_list = index.get(key, [])
        for item in candidate_list:
            if item.section_name in section_names:
                yield item

    def build(sections_iterator):
        '''Build up IndexedWorldData from the data in the given sections.
        '''
        raw_package_info = []
        field_indexes = {}
        indexed_fields = ('name', 'sp-name', 'source-rpm', 'filename')
        for field in indexed_fields:
            field_indexes[field] = {}
        by_blob_id = {}
        try:
            for section_name, section in sections_iterator:
                section_iterator = section.iter_package_info()
                for ghost, blob_id, locator in section_iterator:
                    item = WorldItem(section_name, ghost, blob_id, locator)
                    raw_package_info.append(item)

                    if ghost:
                        found_filename = os.path.basename(locator.filename)
                        ghost.contents.set('', 'found_filename',
                                           found_filename)
                        for field in indexed_fields:
                            try:
                                key = ghost[field]
                            except KeyError:
                                continue
                            index = field_indexes[field]
                            package_list = index.setdefault(key, [])
                            package_list.append(item)

                    if blob_id not in by_blob_id or \
                       not by_blob_id[blob_id].package:
                        by_blob_id[blob_id] = item

            return IndexedWorldData(raw_package_info, field_indexes,
                                    by_blob_id)
        except MissingChannelDataError:
            message = 'Missing cached data. ' + \
                      'Consider running pdk channel update. ' + \
                      '(%s)' % section_name
            raise SemanticError(message)

    build = staticmethod(build)

class LimitedWorldDataIndex(object):
    '''Essentially impersonate IndexedWorldData but filter outputs.

    Does basically everything IndexedWorldData does, but all outputs are
    filtered by the given list of channel names.
    '''
    def __init__(self, data_index, channel_names):
        self.data_index = data_index
        self.channel_names = channel_names

    def get_candidates(self, key_field, key):
        '''See IndexedWorldData.get_candidates.

        Filters output by self.channel_names.
        '''
        return self.data_index.get_candidates(key_field, key,
                                              self.channel_names)

    def get_all_candidates(self):
        '''Get a list of all package candidates filtered by channel name.'''
        for item in self.data_index.raw_package_info:
            if item.section_name in self.channel_names:
                yield item
