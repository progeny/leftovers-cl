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
from sets import Set
from cStringIO import StringIO
from urlparse import urlsplit
from rfc822 import Message
from gzip import GzipFile
from md5 import md5
from xml.parsers.expat import ExpatError
from pdk.exceptions import InputError, SemanticError
from pdk.util import cpath, gen_file_fragments, get_remote_file, \
     shell_command, Framer, make_fs_framer, make_ssh_framer
from pdk.yaxml import parse_yaxml_file
from pdk.package import deb, udeb, dsc, get_package_type, \
     UnknownPackageTypeError

def quote(raw):
    '''Create a valid filename which roughly resembles the raw string.'''
    return re.sub(r'[^A-Za-z0-9.-]+', '_', raw)

class URLCacheAdapter(object):
    '''A cache adapter which downloads raw files via curl or direct copy.
    '''
    def __init__(self):
        self.blob_finders = {}

    def assign(self, blob_finders):
        '''Assign the given blob_finders {blob_id: url} to this adapter.'''
        self.blob_finders.update(blob_finders)

    def adapt(self):
        '''Get a framer ready to stream blobs to a cache.

        Actually the framer strems zero blobs, as the "remote" side of
        the framer is downloading files directly into the cache.
        '''
        framer = Framer(*shell_command('pdk remote adapt'))
        for blob_id, url in self.blob_finders.iteritems():
            framer.write_frame(blob_id)
            framer.write_frame(url)
        framer.write_frame('end-adapt')
        framer.end_stream()
        return framer

class LocalWorkspaceCacheAdapter(object):
    '''A cache adapter for working with a remote workspace on this machine.
    '''
    def __init__(self, path):
        self.path = path
        self.blob_ids = Set()

    def assign(self, blob_ids):
        '''Assign the given blob_ids to this adapter.'''
        self.blob_ids = blob_ids

    def adapt(self):
        '''Return a framer ready to stream the assigned blobs.'''
        framer = Framer(*shell_command('pdk remote listen %s'
                                         % self.path))
        framer.write_stream(['pull-blobs'])
        framer.write_stream(self.blob_ids)
        framer.write_stream(['done'])
        return framer

class SshWorkspaceCacheAdapter(object):
    '''A cache adapter for working with a remote workspace via ssh.
    '''
    def __init__(self, host, path):
        self.host = host
        self.path = path
        self.blob_ids = Set()

    def assign(self, blob_ids):
        '''Assign the given blob_ids to this adapter.'''
        self.blob_ids = blob_ids

    def adapt(self):
        '''Return a framer ready to stream the assigned blobs.'''
        framer = Framer(*shell_command('ssh %s pdk remote listen %s'
                                         % (self.host, self.path)))
        framer.write_stream(['pull-blobs'])
        framer.write_stream(self.blob_ids)
        framer.write_stream(['done'])
        return framer

class FileLocator(object):
    '''Represents a resource which can be imported into the cache.'''
    def __init__(self, base_uri, filename, expected_blob_id):
        self.base_uri = base_uri
        self.filename = filename
        self.blob_id = expected_blob_id

    def make_extra_file_locator(self, filename, expected_blob_id, dummy):
        '''Make a new locator which shares the base_uri or this locator.'''
        return FileLocator(self.base_uri, filename, expected_blob_id)

    def __cmp__(self, other):
        return cmp((self.base_uri, self.filename, self.blob_id),
                   (other.base_uri, other.filename, other.blob_id))

    def get_full_url(self):
        '''Get the full url for the located file.'''
        parts = [ p for p in (self.base_uri, self.filename) if p ]
        return '/'.join(parts)

class CacheFileLocator(object):
    '''Represents a remote cached resource for import into this cache.'''
    def __init__(self, base_uri, filename, expected_blob_id):
        self.base_uri = base_uri
        self.filename = filename
        self.blob_id = expected_blob_id

    def make_extra_file_locator(self, dummy, expected_blob_id, world):
        '''Make a new locator for the given extra file.

        Hunt for the expected_blob_id in the world instead of looking
        for the given filename.
        '''
        return world.find_by_blob_id(expected_blob_id)

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
    def __init__(self, full_path, channel_file, strategy, cache_adapter):
        self.full_path = full_path
        self.channel_file = channel_file
        self.strategy = strategy
        self.cache_adapter = cache_adapter

    def get_identity(self):
        '''Return an identity tuple for this object.'''
        return (self.strategy.package_type, self.full_path)

    def update(self):
        '''Grab the remote file and store it locally.'''
        get_remote_file(self.full_path, self.channel_file, True)

    def iter_package_info(self):
        '''Iterate over ghost_package, blob_id, locator for this section.'''
        if not os.path.exists(self.channel_file):
            return
        gunzipped = GzipFile(self.channel_file)

        control_iterator = self.iter_apt_deb_control(gunzipped)
        for package in \
                self.iter_as_packages(control_iterator):
            locator = self.strategy.get_locator(package)
            package.contents['blob-id'] = locator.blob_id
            yield package, locator.blob_id, locator

        gunzipped.close()

    def iter_apt_deb_control(handle):
        """Given a file like object, yield its deb control-like stanzas."""
        control = ''
        for line in handle:
            control += line
            if not line.rstrip():
                yield control
                control = ''
    iter_apt_deb_control = staticmethod(iter_apt_deb_control)

    def iter_as_packages(self, control_iterator):
        """For each control or header, yield a stream of package objects."""
        for control in control_iterator:
            yield self.strategy.package_type.parse(control, None)

    def assign_to_cache_adapter(self, blob_ids):
        '''Note available blobs and urls in the cache adapter.'''
        blob_finder = {}
        remaining_ids = Set(blob_ids)
        for package, blob_id, locator in self.iter_package_info():
            if blob_id in remaining_ids:
                remaining_ids.remove(blob_id)
                blob_finder[blob_id] = locator.get_full_url()
            if hasattr(package, 'extra_file'):
                for extra_blob_id, extra_filename in package.extra_file:
                    if extra_blob_id in remaining_ids:
                        remaining_ids.remove(extra_blob_id)
                        make_extra = locator.make_extra_file_locator
                        extra_locator = make_extra(extra_filename,
                                                   extra_blob_id, None)
                        blob_finder[extra_blob_id] = \
                            extra_locator.get_full_url()
        self.cache_adapter.assign(blob_finder)
        return self.cache_adapter, remaining_ids

make_comparable(AptDebSection, ('full_path', 'base_path'))

class AptDebBinaryStrategy(object):
    '''Handle get_locator and package_type for AptDebSection

    Used for Packages files.
    '''
    package_type = deb

    def __init__(self, base_path):
        self.base_path = base_path

    def get_locator(self, package):
        """Return base, filename, blob_id for a package"""
        fields = Message(StringIO(package.raw))
        return FileLocator(self.base_path, fields['filename'], \
                           'md5:' + fields['md5sum'])

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

    def __init__(self, base_path):
        self.base_path = base_path

    def get_locator(self, package):
        """Return base, filename, blob_id for a package"""
        for md5_sum, filename in package.extra_file:
            fields = Message(StringIO(package.raw))
            if filename.endswith('.dsc'):
                base = self.base_path + fields['directory']
                return FileLocator(base, filename, md5_sum)
        raise SemanticError, 'no dsc found'

class DirectorySection(object):
    '''Section object for dealing with local directories as channels.'''
    def __init__(self, full_path, cache_adapter):
        self.full_path = full_path
        self.cache_adapter = cache_adapter

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
                locator = FileLocator(url, candidate, None)
                package = package_type.parse(control, blob_id)
                yield package, blob_id, locator

    def assign_to_cache_adapter(self, blob_ids):
        '''Note available blobs and urls in the cache adapter.'''
        blob_finder = {}
        remaining_ids = Set(blob_ids)
        for package, blob_id, locator in self.iter_package_info():
            if blob_id in remaining_ids:
                remaining_ids.remove(blob_id)
                blob_finder[blob_id] = locator.get_full_url()
            if hasattr(package, 'extra_file'):
                for extra_blob_id, extra_filename in package.extra_file:
                    if extra_blob_id in remaining_ids:
                        remaining_ids.remove(extra_blob_id)
                        make_extra = locator.make_extra_file_locator
                        extra_locator = make_extra(extra_filename,
                                                   extra_blob_id, None)
                        blob_finder[extra_blob_id] = \
                            extra_locator.get_full_url()
        self.cache_adapter.assign(blob_finder)
        return self.cache_adapter, remaining_ids

make_comparable(DirectorySection, ('full_path',))

class RemoteWorkspaceSection(object):
    '''Read the remote cache_info list from a source.'''
    def __init__(self, path, channel_file):
        self.full_path = path
        self.channel_file = channel_file

        parts = urlsplit(self.full_path)
        if parts[1]:
            self.cache_adapter = SshWorkspaceCacheAdapter(parts[1],
                                                          parts[2])
        else:
            self.cache_adapter = LocalWorkspaceCacheAdapter(self.full_path)

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
            locator = CacheFileLocator(cache_url, blob_path, blob_id)
            yield None, blob_id, locator

    def assign_to_cache_adapter(self, blob_ids):
        '''Note available blobs in the cache adapter.'''
        found_ids = Set()
        remaining_ids = Set(blob_ids)
        for dummy, blob_id, dummy in self.iter_package_info():
            if blob_id in blob_ids:
                remaining_ids.remove(blob_id)
                found_ids.add(blob_id)
        self.cache_adapter.assign(found_ids)
        return self.cache_adapter, remaining_ids

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
        url_adapter = URLCacheAdapter()
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
                                            strategy, url_adapter)
            elif type_value == 'dir':
                yield DirectorySection(path, url_adapter)
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

class OutsideWorld(object):
    '''This object represents the world outside the workspace.

    To use find_by_blob_id, first call update_blob_id_locator.
    '''
    def __init__(self, sections):
        self.sections = sections
        self.by_blob_id = None

    def get_workspace_section(self, name):
        '''Get the named workspace section.'''
        if name not in self.sections:
            raise SemanticError('%s is not known workspace' % name)
        section = self.sections[name][0]
        if section.__class__ != RemoteWorkspaceSection:
            raise SemanticError('%s is a channel, not a workspace' % name)
        return section

    def get_cache_adapters(self, blob_ids):
        '''Get a set of cache adapters for the given blob_ids.

        Each adapter roughly corresponds to a download session.
        '''
        remaining_blob_ids = Set(blob_ids)
        cache_adapters = []
        for section in self.iter_sections():
            cache_adapter, remaining_blob_ids = \
                section.assign_to_cache_adapter(remaining_blob_ids)
            cache_adapters.append(cache_adapter)

        if remaining_blob_ids:
            if len(remaining_blob_ids) > 2:
                ellipsis = ' ...'
            else:
                ellipsis = ''
            raise SemanticError, \
                  "could not find %s%s in any channel" \
                  % (list(remaining_blob_ids)[0], ellipsis)

        return cache_adapters

    def fetch_world_data(self):
        '''Update all remote source and channel data.'''
        for section in self.iter_sections():
            section.update()

    def update_blob_id_locator(self):
        '''Index blob_ids from local source and channel data.'''
        self.by_blob_id = {}
        for dummy, blob_id, locator in self.iter_raw_package_info():
            self.by_blob_id[blob_id] = locator

    def iter_sections(self, section_names = None):
        '''Iterate over stored sections for the given section_names.'''
        if not section_names:
            section_names = self.sections.keys()
            section_names.sort()
        for name in section_names:
            try:
                for section in self.sections[name]:
                    yield section
            except KeyError, e:
                raise InputError("Unknown channel %s." % str(e))

    def iter_raw_package_info(self, section_names = None):
        '''Iterate over raw package_info from sections.

        Sections are filtered by the given section_names.
        '''
        for section in self.iter_sections(section_names):
            if hasattr(section, 'channel_file'):
                if not os.path.exists(section.channel_file):
                    message = 'Missing cached data. ' + \
                              'Consider running pdk channel update.'
                    raise SemanticError(message)
            for item in  section.iter_package_info():
                yield item

    def iter_package_info(self, section_names = None):
        '''Iterate over package and locator from sections.

        Sections are filtered by the given section_names.
        '''
        package_info = self.iter_raw_package_info(section_names)
        for ghost_package, dummy, locator in package_info:
            # ghost_package is a pdk.package.Package object but we don't
            # have a file in the cache backing it.
            if not ghost_package:
                continue
            found_filename = os.path.basename(locator.filename)
            ghost_package.contents['found_filename'] = found_filename
            yield ghost_package, locator

    def iter_packages(self, section_names = None):
        '''Iterate over packages given from sections.

        Sections are filtered by the given section_names.
        '''
        for package, dummy in self.iter_package_info(section_names):
            yield package

    def find_by_blob_id(self, blob_id):
        '''Return a locator for the given blob_id.'''
        return self.by_blob_id[blob_id]
