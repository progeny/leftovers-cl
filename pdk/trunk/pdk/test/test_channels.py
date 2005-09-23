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

from pdk.channels import OutsideWorld, FileLocator, \
     DirectorySection, AptDebBinaryStrategy, AptDebSourceStrategy, \
     AptDebSection, OutsideWorldFactory, WorldData, quote

class TestAptDebControl(Test):
    def test_iter_apt_deb_control(self):
        packages = 'a\n\nb\nc\r\n\n'
        iter_apt_deb_control = AptDebSection.iter_apt_deb_control
        actual = list(iter_apt_deb_control(StringIO(packages)))
        expected = ['a\n\n', 'b\nc\r\n\n']
        self.assert_equals_long(actual, expected)

class MockPackage(object):
    def __init__(self, blob_id):
        self.blob_id = blob_id
        self.contents = {}

class TestOutsideWorld(Test):
    def test_update_blob_id_locator(self):
        a = MockPackage('a')
        b = MockPackage('b')
        c = MockPackage('c')
        fl = FileLocator
        section_data  = [ (a, 'a', fl('uri:a', 'a.deb', None)),
                          (b, 'b', fl('uri:b', 'b.deb', None)),
                          (c, 'c', fl('uri:c', 'c.deb', None)) ]
        class MockSection(object):
            def iter_package_info(self):
                return section_data

        sections = { 'local': [MockSection()] }

        data = OutsideWorld(sections)
        data.update_blob_id_locator()

        self.assert_equals(fl('uri:b', 'b.deb', None),
                           data.find_by_blob_id('b'))
        self.assert_equals(fl('uri:a', 'a.deb', None),
                           data.find_by_blob_id('a'))
        self.assert_equals(fl('uri:c', 'c.deb', None),
                           data.find_by_blob_id('c'))

        self.assert_equals_long([ i[0] for i in section_data ],
                                list(data.iter_packages(['local'])))

class TestChannelFilenames(Test):
    def test_iter_sections(self):
        world_dict = {
            'channels': { 'local': { 'type': 'dir',
                                     'path': 'directory' },
                          'remote': { 'type': 'apt-deb',
                                      'path': 'http://localhost/',
                                      'dist': 'stable',
                                      'components': 'main contrib',
                                      'archs': 'source i386' }
                          },
            'sources': {}
            }
        world_data = WorldData(world_dict)
        world = OutsideWorldFactory(world_data, 'zzz/zzz').create()
        base_path = 'http://localhost/'
        hpath = base_path + 'dists/stable/%s/%s/%s'
        expected = [
            DirectorySection('directory'),
            AptDebSection(
                hpath % ('main', 'source', 'Sources.gz'),
                None,
                AptDebSourceStrategy(base_path)),
            AptDebSection(
                hpath % ('main', 'binary-i386', 'Packages.gz'),
                None,
                AptDebBinaryStrategy(base_path)),
            AptDebSection(
                hpath % ('contrib', 'source', 'Sources.gz'),
                None,
                AptDebSourceStrategy(base_path)),
            AptDebSection(
                hpath % ('contrib', 'binary-i386', 'Packages.gz'),
                None,
                AptDebBinaryStrategy(base_path))
            ]

        actual = list(world.iter_sections())
        self.assert_equals_long(expected, actual)

    def test_quote(self):
        path = 'http://localhost/dists/stable/Z.gz'
        quoted_path = 'http_localhost_dists_stable_Z.gz'

        self.assert_equals_long(quoted_path, quote(path))
