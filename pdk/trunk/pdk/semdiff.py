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
from itertools import chain
from pdk.cache import Cache
from pdk.component import ComponentDescriptor
from pdk.version_control import cat
from pdk.channels import ChannelData
from pdk.package import Package
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

def list_merge(iter_old, iter_new):
    """Perform a list merge on the two iterables.

    Iterable; yields change, item
    Change is one of ('add', 'drop')
    """
    old = list(iter_old)
    new = list(iter_new)
    old.sort()
    new.sort()

    if old and new:
        left = old.pop(0)
        right = new.pop(0)
        while old and new:
            if left == right:
                left = old.pop(0)
                right = new.pop(0)
                continue
            elif left < right:
                yield ('drop', left)
                left = old.pop(0)
            else:
                yield ('add', right)
                right = new.pop(0)
    for left in old:
        yield('drop', left)
    for right in new:
        yield('add', right)

def get_meta_key(package):
    """Returns a tuple representing a key for merging meta elements.

    Notably, it does not contain version.
    """
    return (package.name, package.type, package.arch)

def get_joinable_meta_list(meta):
    """Take meta and get an iterable suitable for feeding to list_merge."""
    for package in meta:
        if not isinstance(package, Package):
            continue
        predicates = meta[package]
        new_key = get_meta_key(package)
        for predicate, target in predicates.iteritems():
            yield new_key, predicate, target

def iter_diffs_meta(old_meta, new_meta):
    """Detect additions and drops of metadata items.

    Package versions are _not_ considered when comparing metadata.
    """
    old_joinable = get_joinable_meta_list(old_meta)
    new_joinable = get_joinable_meta_list(new_meta)

    old_joinable = list(old_joinable)
    new_joinable = list(new_joinable)

    event_names = {'add': 'meta-add', 'drop': 'meta-drop'}
    for event_type, item in list_merge(old_joinable, new_joinable):
        yield (event_names[event_type], item, None)


def add_my_options(parser):
    '''Set up the parser options for the semdiff command.'''
    parser.add_option(
                         "-c"
                         , "--channel"
                         , action="append"
                         , dest="channels"
                         , type="string"
                         , help="A channel name."
                     )

def do_semdiff(argv):
    """Return bar separated lines representing meaningful component changes.

    Diff works against version control, two arbitrary components, or a
    component and a set of channels.

    Usage: pdk semdiff [-c channel]* component [component]

    Note: When comparing against version control, only the named
    component is retrieved from version control. Sub components are
    found in the work area.

    -c can be specified multiple times to compare against a set of
     channels.
    """
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
        old_meta = {}
        new_meta = {}
    elif len(args) == 1:
        ref = args[0]
        old_desc = ComponentDescriptor(ref, cat(ref))
        new_desc = ComponentDescriptor(ref)
        old_component = old_desc.load(cache)
        new_component = new_desc.load(cache)
        old_package_list = old_component.direct_packages
        new_package_list = new_component.direct_packages
        old_meta = old_component.meta
        new_meta = new_component.meta
    elif len(args) == 2:
        ref = args[1]
        old_desc = ComponentDescriptor(args[0])
        new_desc = ComponentDescriptor(args[1])
        old_component = old_desc.load(cache)
        new_component = new_desc.load(cache)
        old_package_list = old_component.direct_packages
        new_package_list = new_component.direct_packages
        old_meta = old_component.meta
        new_meta = new_component.meta
    else:
        raise CommandLineError("Argument list is invalid")

    diffs = iter_diffs(old_package_list, new_package_list)
    diffs_meta = iter_diffs_meta(old_meta, new_meta)
    for action, primary, secondary in chain(diffs, diffs_meta):
        if action in ('add', 'drop'):
            print '|'.join([action,
                            primary.type,
                            primary.name,
                            primary.version.full_version,
                            primary.arch,
                            ref])
        elif action in ('meta-add', 'meta-drop'):
            key, predicate, target = primary
            name, type_str, arch = key
            print '|'.join([action,
                            type_str,
                            name,
                            arch,
                            predicate,
                            target])
        else:
            old_package, new_package = primary, secondary
            print '|'.join([action,
                            old_package.type,
                            old_package.name,
                            old_package.version.full_version,
                            new_package.version.full_version,
                            old_package.arch,
                            ref])
