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
import os

__revision__ = "$Progeny$"

if os.environ.has_key("PDKVERBOSE"):
    verbose = os.environ["PDKVERBOSE"]


def get_logger():
    """
    Return the default python logging channel.
    """
    import sys
    logger = logging.getLogger('myapp')
    hdlr = logging.StreamHandler(sys.stderr)
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    hdlr.setFormatter(formatter)
    logger.addHandler(hdlr)
    if os.environ.has_key("PDKDEBUG"):
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.WARNING)
    return logger


def get_file_logger():
    """
    Return the default python logging channel.
    """
    logger = logging.getLogger('myapp')
    hdlr = logging.FileHandler('this_is_myapp.log')
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    hdlr.setFormatter(formatter)
    logger.addHandler(hdlr) 
    if os.environ.has_key("PDKDEBUG"):
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)
    return logger


##We can use this logger object now to write entries to the log file:
def test_log():
    """
    Provide example usage
    """
    logger = get_logger()
    logger.error('We have a problem')
    logger.info('While this is just chatty')


# vim:ai:et:sts=4:sw=4:tw=0:
