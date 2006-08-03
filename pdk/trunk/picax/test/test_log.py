# test_log.py - test picax.log
#
# Copyright 2005 Progeny Linux Systems.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

"This module tests the picax.log module."

import unittest
import picax.log
import picax.config

class TestLog(unittest.TestCase):
    "Test picax.log."

    def setUp(self):
        "Since picax.log depends on picax.config being set up, set it up."
        picax.config.handle_args(["--part-size=650000000",
                                  "foo", "bar", "baz"])

    def testLogger(self):
        "Make sure that the logger object is a singleton."

        log1 = picax.log.get_logger()
        log2 = picax.log.get_logger()

        assert log1 is log2

# vim:set ai et sw=4 ts=4 tw=75:
