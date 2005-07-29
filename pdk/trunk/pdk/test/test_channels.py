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

from cStringIO import StringIO
from pdk.test.utest_util import Test

from pdk.channels import gen_apt_deb_control, ChannelData

class TestAptDebControl(Test):
    def test_gen_apt_deb_control(self):
        packages = 'a\n\nb\nc\r\n\n'
        actual = list(gen_apt_deb_control(StringIO(packages)))
        expected = ['a\n\n', 'b\nc\r\n\n']
        self.assert_equals_long(actual, expected)

class MockPackage(object):
    def __init__(self, blob_id):
        self.blob_id = blob_id

class TestChannelData(Test):
    def test_add(self):
        a = MockPackage('a')
        b = MockPackage('b')
        c = MockPackage('c')
        channel = [ (a, 'uri:a', 'a.deb'),
                    (b, 'uri:b', 'b.deb'),
                    (c, 'uri:c', 'c.deb') ]

        data = ChannelData()
        data.add('local', channel)

        self.assert_equals(('uri:b', 'b.deb'), data.find_by_blob_id('b'))
        self.assert_equals(('uri:a', 'a.deb'), data.find_by_blob_id('a'))
        self.assert_equals(('uri:c', 'c.deb'), data.find_by_blob_id('c'))

        self.assert_equals([channel], data.get_channels(['local']))
