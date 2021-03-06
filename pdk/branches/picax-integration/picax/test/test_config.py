# test_config.py - test picax.config
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

"This module tests the picax.config module."

import os
import unittest
import picax.config

class ConfigBaseHarness(unittest.TestCase):
    "Base class with code for resetting picax.config."

    def tearDown(self):
        """Clear out the current configuration in picax.config, so
        a new one can be used."""

        picax.config.config = None

class ConfigFileBaseHarness(ConfigBaseHarness):
    """Shared base for tests requiring configuration files.  Set
    self.xml_text to the configuration file text to use for the tests."""

    xml_text = ""

    def setUp(self):
        "Set the module up with a configuration file."

        self.test_fn = "test.xml"
        self.test_out_fn = "test2.xml"
        self.args = [ "--read-config=%s" % (self.test_fn,),
                      "--write-config=%s" % (self.test_out_fn,), "foo" ]

        cf = open(self.test_fn, "w")
        cf.write(self.xml_text)
        cf.close()

    def tearDown(self):
        "Delete the config files generated from the tests."

        ConfigBaseHarness.tearDown(self)

        for fn in (self.test_fn, self.test_out_fn):
            if os.path.exists(fn):
                os.unlink(fn)

class TestCommandLine(ConfigBaseHarness):
    "Test command-line parsing and most options settings."

    def testExplicitOptions(self):
        "Test that the options passed on the command line are set."

        args = [ "--part-size=650000000", "--arch=i386", "--source=none",
                 "--debug", "foo", "bar", "baz" ]
        picax.config.handle_args(args)
        conf = picax.config.get_config()

        assert conf["arch"] == "i386"
        assert conf["source"] == "none"
        assert conf["debug"]

    def testDefaultOptions(self):
        "Test that defaults are being set correctly."

        args = [ "--part-size=650000000", "--arch=i386", "--source=none",
                 "foo", "bar", "baz" ]
        picax.config.handle_args(args)
        conf = picax.config.get_config()

        assert conf["num_parts"] == 0

    def testRepositories(self):
        "Test that repositories from the command line are being set."

        args = [ "--part-size=650000000", "foo", "bar", "baz" ]
        picax.config.handle_args(args)
        conf = picax.config.get_config()

        assert len(conf["repository_list"]) == 1
        assert conf["repository_list"][0] == ("bar", "baz")

    def testDebug(self):
        """Test that debugging is turned on when the PICAX_DEBUG
        environment variable is set, whether --debug is passed
        or not."""

        os.environ["PICAX_DEBUG"] = "yes"

        args = [ "--part-size=650000000", "--arch=i386", "--source=none",
                 "foo", "bar", "baz" ]
        picax.config.handle_args(args)
        conf = picax.config.get_config()

        assert conf["debug"]

    def testInstallerModule(self):
        "Test that installer module options can be set."

        args = [ "--installer=debian-installer",
                 "--inst-template-path=quux", "--part-size=650000000",
                 "foo", "bar", "baz" ]
        picax.config.handle_args(args)
        conf = picax.config.get_config()

        assert conf["installer_component"] == "debian-installer"
        assert conf["installer_options"]["template_path"] == "quux"

    def testMediaModule(self):
        "Test that media module options can be set."

        args = [ "--media=cd", "--media-image-size=700",
                 "--media-label=quux", "foo", "bar", "baz" ]
        picax.config.handle_args(args)
        conf = picax.config.get_config()

        assert conf["media_component"] == "cd"
        assert conf["media_options"]["image_size"] == 700
        assert conf["media_options"]["label"] == "quux"

    def testSanityChecking(self):
        "Test that sanity checking within picax.config is correct."

        args = [ "foo", "bar", "baz" ]
        args_to_add = [ "--source=none", "--num-parts=3" ]

        # First, try to configure with bad combinations of args.

        while len(args_to_add) > 0:
            failed = False
            try:
                picax.config.handle_args(args)
            except picax.config.ConfigError:
                failed = True

            assert failed

            args.insert(0, args_to_add.pop())

        # Now, the args should be sane together.  Make sure.

        picax.config.handle_args(args)

    def testPartMediaSanityChecking(self):
        "Test another part of sanity checking."

        args = [ "--media=cd", "--part-size=650000000",
                 "foo", "bar", "baz" ]

        failed = False
        try:
            picax.config.handle_args(args)
        except picax.config.ConfigError:
            failed = True

        assert failed

class TestConfigFile(ConfigFileBaseHarness):
    "Test configuration file handling."

    xml_text = """<?xml version='1.0'?>
<picaxconfig>
  <arch>i386</arch>
  <source>none</source>
  <part-size>650000000</part-size>
  <repository distribution='bar' component='baz'/>
</picaxconfig>
"""

    def testExplicitFileOptions(self):
        "Test that the options passed in the config file are set."

        picax.config.handle_args(self.args)
        conf = picax.config.get_config()

        assert conf["arch"] == "i386"
        assert conf["source"] == "none"

    def testDefaultFileOptions(self):
        "Test that defaults are being set correctly with config files."

        picax.config.handle_args(self.args)
        conf = picax.config.get_config()

        assert conf["num_parts"] == 0

    def testFileRepositories(self):
        "Test that repositories are being read properly from the file."

        picax.config.handle_args(self.args)
        conf = picax.config.get_config()

        assert len(conf["repository_list"]) == 1
        assert conf["repository_list"][0] == ("bar", "baz")

    def testFileAndCmdLineRepositories(self):
        """Test that repositories are being read properly from the file
        and being set from the command line properly."""

        args = self.args + ["quux", "frob"]

        picax.config.handle_args(args)
        conf = picax.config.get_config()

        assert len(conf["repository_list"]) == 2
        assert conf["repository_list"][0] == ("bar", "baz")
        assert conf["repository_list"][1] == ("quux", "frob")

    def testWriteConfigFile(self):
        "Test that the configuration file written is proper."

        # First, ensure that the configuration file is written.

        picax.config.handle_args(self.args)

        # Reset the configuration system.

        picax.config._init()

        # Now, read in the new configuration file.

        picax.config.handle_args(["--read-config=%s" % (self.test_out_fn,),
                                  "foo"])

        # Finally, check the file as if it were the regular file.

        self.testExplicitFileOptions()
        self.testDefaultFileOptions()

class TestBrokenConfigFile(ConfigFileBaseHarness):
    """Test that broken XML is not accepted for configuration.
    Also, act as a base class for other broken config file tests;
    can override xml_text and fail_msg to test different kinds of
    brokenness."""

    xml_text = """<?xml version='1.0'?>
<picaxconfig
  <arch>i386</arch>
  <part-size>650000000</part-size>
  <source>none</source>
</picaxconfig>
"""
    fail_msg = "Broken XML accepted."

    def testBrokenConfigFile(self):
        "Make sure configuration fails if the file is broken."

        succeeded = True
        try:
            picax.config.handle_args(self.args)
        except picax.config.ConfigError:
            succeeded = False

        self.failUnless(not succeeded, "(%s) %s" % (self.__class__.__name__,
                                                    self.fail_msg))

class TestRepoMissingInFile(TestBrokenConfigFile):
    "Test that configuration fails if no repository is specified."

    xml_text = """<?xml version='1.0'?>
<picaxconfig>
  <arch>i386</arch>
  <source>none</source>
</picaxconfig>
"""
    fail_msg = "No repositories defined."
