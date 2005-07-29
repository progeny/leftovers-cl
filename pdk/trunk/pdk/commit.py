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
commit

Submit local pdk database changes to the parent database
"""
__revision__ = '$Progeny$'

from pdk.util import assert_python_version
assert_python_version()
##import optparse
##from pdk.cache import Cache
##from pdk.component import ComponentDescriptor
##from pdk.util import split_pipe


def add_my_options(parser):
    """
    Set up the parser options for the commit command.
    """
    parser.add_option( 
                         "-d"
                         , "--dryrun"
                         , action="store_true"
                         , dest="dryrun"
                         , help="Report only, no database changes"
                         , default=True
                     )
    parser.add_option( 
                         "-f"
                         , "--file-list"
                         , action="store"
                         , dest="commit_file"
                         , type="string"
                         , help="Input filename, or `-` for stdin"
                     )


def commit(argv):
    """
    'commit' sends local pdk database changes to the parent database.

    If the command succeeds, the parent directory will contain all
    changes make locally to the argument pdk descriptor file,
    and all relevant package files.

    This may include changes to descriptor files subordinate
    to the argument component descriptor(s)

    If the -d option is used, the command will just report what
    changes would be made to the parent database if the commit
    were actually executed.
    
    usage:
    commit comp:component message

    options:
    -d, --dryrun
    Do not make changes to the parent database.  Only report what
    changes would be made if the command were executed.
    
    -h, --help
    prints this message
    """
    print argv
    pass
####    evaluate the validity of the state of the database
####    build a list of "cache" files from the arg descriptor down
####    send the file list to the parent
####    build a list of descriptor files which:
####        have changed and
####        are in the hierarchy of the arg descriptor
####    svk ci the descriptor files

# vim:ai:et:sts=4:sw=4:tw=0:
