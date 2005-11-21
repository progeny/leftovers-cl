#!/usr/bin/python
# 
# utest.py - run tests
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

import sys
import os
import imp
import unittest

import picax.test

# This file must be run in the root of the source directory.

if not os.path.isdir("picax/test"):
    raise RuntimeError, "could not find tests"

# Import the tests.  This is not a function for namespace reasons.

top_suite = unittest.TestSuite()

for module_fn in os.listdir("picax/test"):
    if not os.path.isfile("picax/test/" + module_fn):
        continue
    if module_fn[-3:] != ".py" or module_fn[:5] != "test_":
        continue

    module_name = module_fn[:-3]

    (mod_file, mod_fn, mod_desc) = imp.find_module(module_name,
                                                   picax.test.__path__)
    try:
        mod = imp.load_module(module_name, mod_file, mod_fn, mod_desc)
    finally:
        if mod_file is not None:
            mod_file.close()

    for identifier in mod.__dict__.keys():
        try:
            if issubclass(mod.__dict__[identifier], unittest.TestCase):
                top_suite.addTest(
                    unittest.makeSuite(mod.__dict__[identifier],
                                       "test"))
        except:
            pass

# Run the tests

if __name__ == "__main__":
    result = unittest.TextTestRunner().run(top_suite)
    sys.exit(not result.wasSuccessful())
