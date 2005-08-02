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
"""

import os
import pycurl
from cStringIO import StringIO
from rfc822 import Message
from cPickle import dump, load
from gzip import GzipFile
from md5 import md5
from xml.parsers.expat import ExpatError
from pdk.exceptions import InputError
from pdk.util import path, cpath, gen_file_fragments, find_base_dir
from pdk.yaxml import parse_yaxml_file
from pdk.package import get_package_type, UnknownPackageType
from pdk.progress import ConsoleProgress, CurlAdapter

def gen_apt_deb_control(handle):
    """Given a file like object, yield its deb control-like stanzas."""
    control = ''
    for line in handle:
        control += line
        if not line.rstrip():
            yield control
            control = ''

def gen_packages(control_iterator, package_type):
    """For each control or header, yield a package object."""
    for control in control_iterator:
        yield package_type.parse(control, None)

def gen_package_dir(channel_data):
    """Generate package objects for every package found in a dir tree."""
    directory = channel_data['path']
    for root, dummy, files in os.walk(directory):
        for candidate in files:
            full_path = path(root)[candidate]()
            try:
                package_type = get_package_type(filename = candidate)
            except UnknownPackageType:
                # if we don't know the the file is, we skip it.
                continue
            control = package_type.extract_header(full_path)
            iterator = gen_file_fragments(full_path)
            md51_digest = md5()
            for block in iterator:
                md51_digest.update(block)
            blob_id = 'md5:' + md51_digest.hexdigest()
            url = 'file://' + cpath(root)()
            yield package_type.parse(control, blob_id), url, candidate

def gen_apt_deb_dir(channel_data):
    '''Generate package objects for every stanza in an apt source.

    expect channel_data to be a dict:
      { "path": http url
        "dist": dist_name
        "archs": space separated list of archs **including "source".**
        "components": space separated list of apt components
    All parameters in channel_data should be in a form similar to
    sources.list. (except archs)
    '''
    base_url = channel_data['path']
    dist = channel_data['dist']
    components = channel_data['components'].split()
    archs = channel_data['archs'].split()
    for component in components:
        for arch in archs:
            for item in gen_apt_deb_slice(base_url, dist, component, arch):
                yield item

def gen_apt_deb_slice(base_url, dist, component, arch):
    '''Generate metadata for a single url, dist, component, and arch.'''
    if arch == 'source':
        target = 'Sources.gz'
        arch_specific = 'source'
        package_type = get_package_type(format='dsc')
        def get_download_info(package):
            """Return base, filename, blob_id for a package"""
            for md5_sum, filename in package.extra_file:
                fields = Message(StringIO(package.raw))
                if filename.endswith('.dsc'):
                    base = base_url + fields['directory']
                    return base, filename, md5_sum
            raise ChannelError, 'no dsc found'
    else:
        target = 'Packages.gz'
        arch_specific = 'binary-%s' % arch
        package_type = get_package_type(format='deb')
        def get_download_info(package):
            """Return base, filename, blob_id for a package"""
            fields = Message(StringIO(package.raw))
            return base_url, fields['filename'], \
                'md5:' + fields['md5sum']

    tag_file = StringIO()
    url = base_url + path('dists')[dist][component][arch_specific][target]()
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

    control_iterator = gen_apt_deb_control(gunzipped)
    for package in gen_packages(control_iterator, package_type):
        base_uri, filename, blob_id = get_download_info(package)
        package.contents['blob-id'] = blob_id
        yield package, base_uri, filename

class ChannelError(StandardError):
    """Raise when an error is encountered while working with a channel."""
    pass

channel_data_source_global = os.path.join(
    find_base_dir() or "."
    , 'channels.xml'
    )
channel_data_cache_global = channel_data_source_global + '.cache'

class ChannelData(object):
    '''This object holds the downloaded state of channels.

    It is intended to be loaded from a pickle file or rebuilt completely
    and saved to a pickle file.
    '''
    def __init__(self):
        self.by_blob_id = {}
        self.by_channel_name = {}

    def rebuild_cached(channel_data_source = channel_data_source_global,
                       channel_data_cache = channel_data_cache_global):
        '''Download new metadata and rewrite the pickle file.'''
        try:
            channels = parse_yaxml_file(channel_data_source)
        except ExpatError, message:
            raise InputError("In %s, %s" % (channel_data_source, message))

        type_lookup = {'dir': gen_package_dir, 'apt-deb': gen_apt_deb_dir}

        channel_data = ChannelData()
        for name, data in channels.items():
            channel_generator = type_lookup[data['type']]
            channel_data.add(name, channel_generator(data))
        channel_data.dump(channel_data_cache)
    rebuild_cached = staticmethod(rebuild_cached)

    def load_cached(channel_data_cache = channel_data_cache_global):
        '''Load the instance of this object from the pickle file.'''
        return load(open(channel_data_cache))
    load_cached = staticmethod(load_cached)

    def add(self, channel_name, channel_iterator):
        '''Collect and index the contents of a channel.'''
        channel = list(channel_iterator)
        self.by_channel_name[channel_name] = channel
        for ghost_package, base_uri, filename in channel:
            self.by_blob_id[ghost_package.blob_id] = (base_uri, filename)

    def find_by_blob_id(self, blob_id):
        '''Find a (base_uri, filename) tuple by blob_id.'''
        return self.by_blob_id[blob_id]

    def get_channels(self, channel_names):
        '''Get a list of channels added under the given names.'''
        if not channel_names:
            channel_names = self.by_channel_name.keys()
        return [ self.by_channel_name[n] for n in channel_names ]

    def dump(self, filename):
        '''Dump this object to the given file.'''
        dump(self, open(filename, 'w'), 2)
