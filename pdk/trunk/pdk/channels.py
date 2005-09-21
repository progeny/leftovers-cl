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
channels.py

Channels are ways to acquire packages.

The only class here designed for use outside of this module is
OutsideWorld.

Channel objects are transient. They only exist long enough to acquire
and parse their index or package data, which may be remote. They behave
as iterators, and do not need to be persistent.

Persistence of all the channels is managed by the OutsideWorld class.
"""

import os
pjoin = os.path.join
import rfc822
import pycurl
from cStringIO import StringIO
from urlparse import urlsplit, urlunsplit
from rfc822 import Message
import cPickle
from gzip import GzipFile
from md5 import md5
from itertools import chain
from xml.parsers.expat import ExpatError
from pdk.exceptions import InputError, SemanticError
from pdk.util import cpath, gen_file_fragments
from pdk.yaxml import parse_yaxml_file
from pdk.package import get_package_type, UnknownPackageTypeError
from pdk.progress import ConsoleProgress, CurlAdapter

class FileLocator(object):
    '''Represents a resource which can be imported into the cache.'''
    def __init__(self, base_uri, filename, expected_blob_id):
        self.base_uri = base_uri
        self.filename = filename
        self.blob_id = expected_blob_id

    def make_extra_file_locator(self, filename, expected_blob_id):
        '''Make a new locator which shares the base_uri or this locator.'''
        return FileLocator(self.base_uri, filename, expected_blob_id)

    def __cmp__(self, other):
        return cmp((self.base_uri, self.filename, self.blob_id),
                   (other.base_uri, other.filename, other.blob_id))

class CacheFileLocator(object):
    '''Represents a remote cached resource for import into this cache.'''
    def __init__(self, base_uri, filename, expected_blob_id, outside_world):
        self.base_uri = base_uri
        self.filename = filename
        self.blob_id = expected_blob_id
        self.outside_world = outside_world

    def make_extra_file_locator(self, dummy, expected_blob_id):
        '''Make a new locator for the given extra file.

        Hunt for the expected_blob_id in the world instead of looking
        for the given filename.
        '''
        return self.outside_world.find_by_blob_id(expected_blob_id)

    def __cmp__(self, other):
        return cmp((self.base_uri, self.filename, self.blob_id),
                   (other.base_uri, other.filename, other.blob_id))

class PackageDirChannel(object):
    """Generate package objects for every package found in a dir tree.

    yields three-tuple (package object, uri, unpathed filename)
    """
    def __init__(self, path):
        self.path = path

    def __iter__(self):
        for root, dirnames, files in os.walk(self.path, topdown = True):
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
                yield package_type.parse(control, blob_id), locator

class AptDebChannel(object):
    '''Generate package objects for every stanza in an apt source.'''
    def __init__(self, path, dist, components, archs):
        self.path = path
        self.dist = dist
        self.components = components
        self.archs = archs

    def iter_apt_deb_control(handle):
        """Given a file like object, yield its deb control-like stanzas."""
        control = ''
        for line in handle:
            control += line
            if not line.rstrip():
                yield control
                control = ''
    iter_apt_deb_control = staticmethod(iter_apt_deb_control)

    def iter_as_packages(control_iterator, package_type):
        """For each control or header, yield a stream of package objects."""
        for control in control_iterator:
            yield package_type.parse(control, None)
    iter_as_packages = staticmethod(iter_as_packages)

    def __iter__(self):
        for component in self.components:
            for arch in self.archs:
                for item in self.iter_apt_deb_slice(component, arch):
                    yield item

    def iter_apt_deb_slice(self, component, arch):
        '''Generate metadata for a single url, dist, component, and arch.'''
        # The navigation of the repo, loading of files, and parsing of 
        # the Sources, Packages, et al, are a SIDE EFFECT of an 
        # iterator wrapper? Hmmmm....
        if arch == 'source':
            target = 'Sources.gz'
            arch_specific = 'source'
            package_type = get_package_type(format='dsc')
            def get_download_info(package):
                """Return base, filename, blob_id for a package"""
                for md5_sum, filename in package.extra_file:
                    fields = Message(StringIO(package.raw))
                    if filename.endswith('.dsc'):
                        base = self.path + fields['directory']
                        return FileLocator(base, filename, md5_sum)
                raise SemanticError, 'no dsc found'
        else:
            target = 'Packages.gz'
            arch_specific = 'binary-%s' % arch
            package_type = get_package_type(format='deb')
            def get_download_info(package):
                """Return base, filename, blob_id for a package"""
                fields = Message(StringIO(package.raw))
                return FileLocator(self.path, fields['filename'], \
                                   'md5:' + fields['md5sum'])

        tag_file = StringIO()
        url = self.path + pjoin('dists', self.dist, component,
                                    arch_specific, target)
        curl = pycurl.Curl()
        curl.setopt(curl.URL, url)
        curl.setopt(curl.WRITEFUNCTION, tag_file.write)
        progress = ConsoleProgress(url)
        adapter = CurlAdapter(progress)
        curl.setopt(curl.NOPROGRESS, False)
        curl.setopt(curl.PROGRESSFUNCTION, adapter.callback)
        curl.perform()
        tag_file.reset()
        gunzipped = GzipFile(fileobj = tag_file)

        control_iterator = self.iter_apt_deb_control(gunzipped)
        for package in \
                self.iter_as_packages(control_iterator, package_type):
            locator = get_download_info(package)
            package.contents['blob-id'] = locator.blob_id
            yield package, locator

class RemoteSource(object):
    '''Read the remote cache_info list from a source.'''
    def __init__(self, path, outside_world):
        self.path = path
        self.outside_world = outside_world

    def __iter__(self):
        cache_index = StringIO()
        raw_url = self.path
        scheme, netloc, raw_path, query, fragment = urlsplit(raw_url)
        if not scheme:
            scheme = 'file://'
        path_parts = raw_path.split('/')
        del path_parts[-1]
        index_path = '/'.join(path_parts + ['cache', 'blob_list.gz'])
        index_url = urlunsplit((scheme, netloc, index_path, query,
                                fragment))
        cache_path = '/'.join(path_parts + ['cache'])
        cache_url = urlunsplit((scheme, netloc, cache_path, query,
                                fragment))
        curl = pycurl.Curl()
        curl.setopt(curl.URL, index_url)
        curl.setopt(curl.WRITEFUNCTION, cache_index.write)
        progress = ConsoleProgress(cache_url)
        adapter = CurlAdapter(progress)
        curl.setopt(curl.NOPROGRESS, False)
        curl.setopt(curl.PROGRESSFUNCTION, adapter.callback)
        curl.perform()
        cache_index.reset()
        gunzipped = GzipFile(fileobj = cache_index)
        for line in gunzipped:
            blob_id, blob_path = line.strip().split()
            locator = CacheFileLocator(cache_url, blob_path, blob_id,
                                       self.outside_world)
            yield blob_id, locator

def create_channel(name, data_dict):
    ''' Create a channel from the given data_dict.

    Expects a data_dict containing at least "path" and "type"
    keys. Other keys may be required depending on the type.

    If type is "dir", then only "path" is required. Path should refer
    to a directory containing packages.

    If type is "apt-deb", then the following keys should be present:
      { "path": http url
        "dist": dist_name
        "archs": space separated list of archs **including "source".**
        "components": space separated list of apt components }
    All parameters for apt-deb should be in a form similar to
    sources.list. (except archs)

    '''
    type_value = None
    try:
        type_value = data_dict['type']
    except KeyError, message:
        raise InputError('%s has no type' % name)

    try:
        path = data_dict['path']
        if type_value == 'apt-deb':
            if path[-1] != "/":
                raise InputError, "path in channels.xml must end in a slash"
            dist = data_dict['dist']
            components = data_dict['components'].split()
            archs = data_dict['archs'].split()
            return AptDebChannel(path, dist, components, archs)
        elif type_value == 'dir':
            return PackageDirChannel(path)
        else:
            raise InputError('channel %s has unrecognized type %s'
                             % (name, type_value))
    except KeyError, field:
        message = 'channel "%s" missing field "%s"' % (name, str(field))
        raise InputError(message)

class OutsideWorld(object):
    '''This object holds the downloaded state of all channels.
    And loads the state.
    And writest the state.
    And returns a list of channels.
    And indexes all files by blob ids.

    It is intended to be loaded from a pickle file or rebuilt completely
    and saved to a pickle file.
    '''

    def __init__(self):
        self.by_blob_id = {}            # A flat space of all blobs
        self.by_channel_name = {}       # tuples by channel name


    def update_index(workspace):
        '''Download new metadata and rewrite the pickle file.'''
        try:
            channels = parse_yaxml_file(workspace.channel_data_source)
        except ExpatError, message:
            raise InputError("In %s, %s" % (workspace.channel_data_source,
                                            message))
        except IOError, error:
            if error.errno == 2:
                # treat missing channels.xml as no channels needed.
                channels = {}

        outside_world = OutsideWorld()
        for name, data in channels.items():
            channel = create_channel(name, data)
            outside_world.update_with_channel(name, iter(channel))

        for name in os.listdir(workspace.sources_dir):
            source_file = os.path.join(workspace.sources_dir, name)
            lookup = rfc822.Message(open(source_file))
            path = lookup['URL']
            source = RemoteSource(path, outside_world)
            outside_world.update_with_source(iter(source))
        outside_world.dump(workspace.outside_world_store)
    update_index = staticmethod(update_index)

    def load_cached(workspace):
        '''Read channel data from the pickle file.'''
        result = None
        try:
            result = cPickle.load(open(workspace.outside_world_store))
        except IOError, error:
            if error.errno == 2:
                message = 'Missing "%s."\n' + \
                          'Consider running pdk channel update.'
                raise SemanticError(message % workspace.outside_world_store)
        return result
    load_cached = staticmethod(load_cached)

    def update_with_channel(self, channel_name, channel_iterator):
        '''Collect and index the contents of a channel.'''
        self.by_channel_name[channel_name] = []
        for ghost_package, locator in channel_iterator:
            # ghost_package is a pdk.package.Package object but we don't
            # have a file in the cache backing it.
            found_filename = os.path.basename(locator.filename)
            ghost_package.contents['found_filename'] = found_filename
            self.by_channel_name[channel_name].append(ghost_package)
            self.by_blob_id[ghost_package.blob_id] = locator

    def update_with_source(self, source_iterator):
        '''Collect and index the contents of a source.'''
        for blob_id, locator in source_iterator:
            self.by_blob_id[blob_id] = locator

    def find_by_blob_id(self, blob_id):
        '''Find a package locator by blob_id.'''
        return self.by_blob_id[blob_id]

    def get_package_list(self, channel_names):
        '''Get a list of packages added under the given channel names.'''
        if not channel_names:
            channel_names = self.by_channel_name.keys()
        try:
            package_lists = [ self.by_channel_name[n]
                              for n in channel_names ]
        except KeyError, e:
            raise InputError("Unknown channel %s." % str(e))
        return list(chain(*package_lists))

    def dump(self, filename):
        '''Dump this object to the given file.'''
        cPickle.dump(self, open(filename, 'w'), 2)



