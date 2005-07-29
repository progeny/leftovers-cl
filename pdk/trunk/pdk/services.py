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
services

Library interface to pdk services
"""
__revision__ = '$Progeny$'

from pdk.util import assert_python_version
assert_python_version()
import sys


def init(args):
    """
    Initialize subscription services to a source provider.
    Usage:
    pdk init [source URL]
    """
    source_url = args[0]
    print sys.stderr, source_url

    """
    Initializes the PDK environment. Should be run on the development
    team's depot server after initial installation of CL/PDK. Prompts
    for username and password, adding that authentication to the
    local .netrc, which allows the server to communicate with a 
    source provider over an authenticated API. 

    After pdk init, developers with accounts can connect to the depot
    server, which is potentially located on a different machine.
    """



# vim:ai:et:sts=4:sw=4:tw=0:
