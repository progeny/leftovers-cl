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
resolve.py

Contains functionality for resolving abstract package references.
"""

from pdk.cache import Cache
from pdk.component import ComponentDescriptor, PackageReference
from pdk.channels import ChannelData
from pdk.exceptions import CommandLineError

def do_updatechannels(args):
    '''Read channels.xml and update the remote channel data. (depot)'''
    if len(args) > 0:
        raise CommandLineError, 'updatechannels takes no arguments'

    ChannelData.rebuild_cached()

def do_resolve(args):
    """resolve resolves abstract package references

    If the command succeeds, the component will be modified in place.
    Abstract references will be rewritten to concrete references, and
    missing constraint elements will be placed.

    The command takes a single component descriptor followed by zero
    or more channel names.

    If not channel names are given, resolve uses all channels to
    resolve references.
    """
    if len(args) < 1:
        raise CommandLineError, 'component descriptor required'
    component_name = args[0]
    descriptor = ComponentDescriptor(component_name)
    channel_names = args[1:]
    channels = ChannelData.load_cached()
    for channel in channels.get_channels(channel_names):
        resolve(descriptor, channel)

def do_download(args):
    '''Command line entry point to downloading missing packages.'''
    cache = Cache()
    channels = ChannelData.load_cached()

    descriptor = ComponentDescriptor(args[0])
    for ref in descriptor.iter_package_refs():
        if ref.blob_id and ref.blob_id not in cache:
            base_uri, filename = channels.find_by_blob_id(ref.blob_id)
            cache.import_file(base_uri, filename, ref.blob_id)
            package = ref.load(cache)
            if hasattr(package, 'extra_file'):
                for blob_id, filename in package.extra_file:
                    cache.import_file(base_uri, filename, blob_id)

def resolve(descriptor, channel):
    """Resolve abstract references by searching the given path."""
    refs = []
    for index, ref in descriptor.enumerate_package_refs():
        refs.append((ref, index))

    for channel_item in channel:
        ghost_package = channel_item[0]
        for ref_index, ref_tuple in enumerate(refs):
            ref, contents_index = ref_tuple
            if ref.rule.condition.evaluate(ghost_package):
                new_ref = PackageReference.from_package(ghost_package)
                new_ref.rule.predicates = ref.rule.predicates
                descriptor.contents[contents_index] = new_ref
                del refs[ref_index]
                break
    descriptor.write()
