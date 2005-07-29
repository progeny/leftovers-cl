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
add

Incorporate packages into the local workspace.
Part of the PDK suite
"""
__revision__ = '$Progeny$'

import sys
from pdk.util import assert_python_version
assert_python_version()
import optparse
from pdk.cache import Cache, calculate_checksums
from pdk.component import ComponentDescriptor, PackageReference
from pdk.package import get_package_type
from pdk.util import split_pipe, path


def add_my_options(parser):
    """
    Set up the parser options for the add command.
    """
    parser.add_option( 
                         "-f"
                         , "--file-list"
                         , action="store"
                         , dest="filename"
                         , type="string"
                         , help="Input filename, or `-` for stdin"
                     )
    parser.add_option( 
                         "-e"
                         , "--encoding"
                         , action="store"
                         , dest="encoding"
                         , type="string"
                         , help="Input filename, or `-` for stdin"
                     )

    parser.add_option( 
                         "-a"
                         , "--add"
                         , action="store_true"
                         , dest="include_existing_packages"
                         , help="Keep existing packages"
                         , default=True
                     )

    parser.add_option( 
                         "-r"
                         , "--replace"
                         , action="store_false"
                         , dest="include_existing_packages"
                         , help="Mark existing packages for removal"
                     )

def bail(message=None, exitval=1):
    """Exit after printing an error message and the usage message"""
    if message:
        print >> sys.stderr, message
    sys.exit(exitval)


def add(argv):
    """
    'add' brings files into an installed pdk database.

    If the command succeeds, the argument package files will
    be placed in the local package dictionary, and the descriptor
    file for the argument component will contain references
    to those entries in the package dictionary.

    If an earlier version of an added package file already
    exists in the argument component, the component descriptor
    will retain a reference to the old version, which will be
    marked for removal (with "precedes").  These references
    can be removed manually, or by using the "apply" command.

    If the -r option is used, this marking is skipped, and the 
    older package references are just removed from the package
    descriptor.
    
    usage:
    add comp:component [file list]

    options:
    -f [arg], --file [arg]
    where [arg] is the name of a file which contains the 
    filenames of the package files to add
    
    -e, --encoding
    
    -a, --string
    
    -r, --replace
    Remove superceded package references from the component descriptor
    
    -h, --help
    prints this message
    """
    my_parser = optparse.OptionParser()
    add_my_options(my_parser)
    component = None
    data = {}
    opts, args = my_parser.parse_args(args=argv)

    if opts.filename:
        data.update(split_pipe(open(opts.filename)))

    if opts.encoding:
        print >> sys.stderr, "encoding: ", str(opts.encoding)

    if len(args) > 0:
        component = args.pop(0)
        files = args
        files = [ f for f in files if f ]
        data[component] = files

    if len(data) == 0:
        bail('No component data given.')

    cache = Cache()

    for component, files in data.iteritems():
        packages = []
        for filename in files:
            try:
                blob_id = calculate_checksums(filename)[0]
                package_type = get_package_type(filename = filename)
                package_type_string = package_type.type_string
                cache.import_file('', filename, blob_id)
                package = cache.load_package(blob_id, package_type_string)
                if hasattr(package, 'extra_file'):
                    for blob_id, extra_filename in package.extra_file:
                        extra_path = path(filename)['..'][extra_filename]()
                        cache.import_file('', extra_path, blob_id)
                packages.append(package)
            except UnicodeError, message:
                print >> sys.stderr, "Invalid character in filename.",
                print >> sys.stderr, message
        if len(packages) == 0:
            bail('No data to output.')
        descriptor = ComponentDescriptor(component)
        if opts.include_existing_packages:
            loaded_component = descriptor.load(cache)
            # only add packages if they are not already present.
            blob_ids_to_avoid = [ p.blob_id for p in
                                  loaded_component.direct_packages ]
            packages_to_add = [ p for p in packages
                                if p.blob_id not in blob_ids_to_avoid ]
            refs = [ PackageReference.from_package(p)
                     for p in packages_to_add ]
            descriptor.contents.extend(refs)
        else:
            refs = [ PackageReference.from_package(p) for p in packages ]
            descriptor.contents = refs
        descriptor.write()

# vim:ai:et:sts=4:sw=4:tw=0:
