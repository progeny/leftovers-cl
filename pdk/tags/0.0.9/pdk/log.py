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

"""This module enables logging.

"""

import logging
import threading
import os

__revision__ = "$Progeny$"


lock = threading.Lock()
def get_logger():
    """
    Return the default python logging channel.
    """
    lock.acquire()
    try:
        if not get_logger.logger:
            import sys
            logger = get_logger.logger = logging.getLogger('pdk')
            hdlr = logging.StreamHandler(sys.stderr)
            formatter = logging.Formatter(
                '%(asctime)s %(levelname)s %(message)s'
                )
            hdlr.setFormatter(formatter)
            logger.addHandler(hdlr)
            if os.environ.has_key("PDKDEBUG"):
                logger.setLevel(logging.DEBUG)
            else:
                logger.setLevel(logging.WARNING)
    finally:
        lock.release()
    return get_logger.logger
get_logger.logger = None

# vim:ai:et:sts=4:sw=4:tw=0:
