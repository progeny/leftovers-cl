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
apply: a pdk command
Resolve a marked-up component descriptor by applying the
actions suggested by the 'svk mark' process
"""

__revision__ = '$Progeny$'

import optparse
from pdk.component import ComponentDescriptor
import pdk.log as log

logger = log.get_logger()


def do_apply(argv):
    """
    apply
    Find multiple instances of packages within a component, and apply
    the older version as a candidate for deletion
    """
    my_parser = optparse.OptionParser()
    opts, args = my_parser.parse_args(args=argv)
    logger.info("pdk apply argv, opts: " + " ".join(argv), str(opts))
    for component_uri in args:
        descriptor = ComponentDescriptor(component_uri)
        descriptor.apply()


# vim:ai:et:sts=4:sw=4:tw=0:
