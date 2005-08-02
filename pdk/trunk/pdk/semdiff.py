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
semdiff.py

Houses functionality used in calculating and outputting semantic diffs.
"""

import optparse
from sets import Set
from pdk.cache import Cache
from pdk.component import ComponentDescriptor
from pdk.version_control import cat
from pdk.channels import ChannelData
from pdk.exceptions import CommandLineError

def index_by_fields(packages, fields):
    """Scan packages, return a dict indexed by the given fields."""
    index = {}
    for package in packages:
        key = tuple([ getattr(package, f) for f in fields ])
        if not key in index:
            index[key] = []
        index[key].append(package)
    return index

def permute(old_packages, new_packages, anchor_fields):
    """Permute all old and new packages sharing anchor fields."""
    old_index = index_by_fields(old_packages, anchor_fields)
    new_index = index_by_fields(new_packages, anchor_fields)

    all_anchors = Set(old_index.keys()) | Set(new_index.keys())
    for anchor in all_anchors:
        for old_package in old_index.get(anchor, [None]):
            for new_package in new_index.get(anchor, [None]):
                yield old_package, new_package

def iter_diffs(old_package_list, new_package_list):
    """Permute component packages together properly and yield actions.

    Tuples yielded are of the form (action, primary, secondary).

    Action may be one of add, drop upgrade, downgrade, or unchanged.

    For add and drop, primary is the added or dropped package, secondary
    is None.

    For upgrade, downgrade, and unchanged, primary is the preexisting
    package, and secondary is the current package.
    """
    permutations = permute(old_package_list, new_package_list,
                           ('name', 'arch', 'type'))
    for old_package, new_package in permutations:
        if not old_package:
            yield 'add', new_package, None
            continue
        if not new_package:
            yield 'drop', old_package, None
            continue

        compared = cmp(old_package.version, new_package.version)
        if compared < 0:
            action = 'upgrade'
        elif compared > 0:
            action = 'downgrade'
        else:
            action = 'unchanged'

        yield action, old_package, new_package

def add_my_options(parser):
    '''Set up the parser options for the add command.'''
    parser.add_option(
                         "-c"
                         , "--channel"
                         , action="append"
                         , dest="channels"
                         , type="string"
                         , help="A channel name."
                     )

def do_semdiff(argv):
    """Entry point from the command line."""
    cache = Cache()
    parser = optparse.OptionParser()
    add_my_options(parser)
    opts, args = parser.parse_args(args=argv)

    if opts.channels:
        ref = args[0]
        desc = ComponentDescriptor(args[0])
        component = desc.load(cache)
        old_package_list = component.direct_packages
        channels = ChannelData.load_cached()
        new_package_list = []
        for channel in channels.get_channels(opts.channels):
            package_list = [ t[0] for t in channel ]
            new_package_list.extend(package_list)
    elif len(args) == 1:
        ref = args[0]
        old_desc = ComponentDescriptor(ref, cat(ref))
        new_desc = ComponentDescriptor(ref)
        old_component = old_desc.load(cache)
        new_component = new_desc.load(cache)
        old_package_list = old_component.direct_packages
        new_package_list = new_component.direct_packages
    elif len(args) == 2:
        ref = args[1]
        old_desc = ComponentDescriptor(args[0])
        new_desc = ComponentDescriptor(args[1])
        old_component = old_desc.load(cache)
        new_component = new_desc.load(cache)
        old_package_list = old_component.direct_packages
        new_package_list = new_component.direct_packages
    else:
        raise CommandLineError("Argument list is invalid")

    diffs = iter_diffs(old_package_list, new_package_list)
    for action, primary, secondary in diffs:
        if action in ('add', 'drop'):
            print '|'.join([action,
                            primary.type,
                            primary.name,
                            primary.version.full_version,
                            primary.arch,
                            ref])
        else:
            old_package, new_package = primary, secondary
            print '|'.join([action,
                            old_package.type,
                            old_package.name,
                            old_package.version.full_version,
                            new_package.version.full_version,
                            old_package.arch,
                            ref])
