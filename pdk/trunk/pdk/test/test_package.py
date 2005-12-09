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

from sets import Set
from pdk.test.utest_util import Test, MockPackage

from pdk.package import \
     get_package_type, udeb, deb, dsc, srpm, rpm, \
     sanitize_deb_header, \
     UnknownPackageTypeError, synthesize_version_string, DebianVersion

__revision__ = "$Progeny$"

class TestPackageClass(Test):
    def test_emulation_behaviors(self):
        p = MockPackage('name', '2', deb, extras = {('pdk', 'a'): 1})
        self.assert_equal(1, p.pdk.a)
        self.assert_equal('name', p.pdk.name)
        self.assert_equal(DebianVersion('2'), p.pdk.version)

        self.assert_equal(3, len(p))

        try:
            p.z
            self.fail('should have thrown exception')
        except AttributeError:
            pass

        try:
            p['z']
            self.fail('should have thrown exception')
        except KeyError:
            pass

    def test_package_is_hashable(self):
        p = MockPackage('a', '1', deb)
        Set([p])

    def test_get_file(self):
        class MockType(object):
            format_string = 'deb'
            type_string = 'dsc'
            def get_filename(self, dummy):
                return 'asdfjkl'

        package_type = MockType()
        p = MockPackage('a', '2.3-1.1', package_type, arch ='i386')
        self.assert_equal('asdfjkl', p.filename)
        p[('pdk', 'filename')] = 'superduper'
        self.assert_equal('superduper', p.filename)

class TestDeb(Test):
    def test_parse(self):
        header = """Package: name
Depends: z
Version: 0:2-3
Architecture: i386
Replaces: y
Description: abc
 def
  ghi
 jkl mno

"""
        package = deb.parse(header, 'zzz')
        self.assert_equal(deb, package.package_type)
        self.assert_equal('zzz', package.blob_id)
        self.assertEquals('name', package.name)
        self.assertEquals('0', package.version.epoch)
        self.assertEquals('2', package.version.version)
        self.assertEquals('3', package.version.release)
        self.assertEquals('i386', package.arch)
        self.assertEquals('name', package.pdk.sp_name)
        self.assertEquals('0', package.pdk.sp_version.epoch)
        self.assertEquals('2', package.pdk.sp_version.version)
        self.assertEquals('3', package.pdk.sp_version.release)
        self.assert_equals('y', package['deb', 'Replaces'])

    def test_has_source(self):
        header = """Package: name
Depends: z
Version: 1
Architecture: i386
Source: a
Description: asdf
 One fine day
 there was some stuff.
 .
 Then more stuff.

"""
        package = deb.parse(header, 'zzz')
        self.assertEquals('a', package[('pdk', 'sp-name')])

    def test_has_source_version(self):
        header = """Package: name
Depends: z
Version: 1
Architecture: i386
Source: a (0.24-3.2)
Description: asdf
 One fine day
 there was some stuff.
 .
 Then more stuff.

"""
        package = deb.parse(header, 'zzz')
        self.assertEquals('a', package[('pdk', 'sp-name')])
        self.assertEquals(None, package.pdk.sp_version.epoch)
        self.assertEquals('0.24', package.pdk.sp_version.version)
        self.assertEquals('3.2', package.pdk.sp_version.release)

class TestDsc(Test):
    def test_parse(self):
        header = """Format: 1.0
Source: zippy
Section: contrib/net
Version: 0.6.6.1-2
Architecture: all
Files:
 300039c03ecb76239b2d74ade0868311 2676 zippy.diff.gz
 aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa 111 zippy.orig.tar.gz

"""
        package = dsc.parse(header, 'zzz')
        self.assert_equal(dsc, package.package_type)
        self.assert_equal('zzz', package.blob_id)
        self.assertEquals('zippy', package.name)
        self.assertEquals(None, package.version.epoch)
        self.assertEquals('0.6.6.1', package.version.version)
        self.assertEquals('2', package.version.release)
        self.assertEquals('all', package.arch)
        expected_files = (('md5:300039c03ecb76239b2d74ade0868311',
                           '2676',
                           'zippy.diff.gz'),
                          ('md5:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
                           '111',
                           'zippy.orig.tar.gz') )
        actual_files = package.extra_files
        self.assert_equals_long(expected_files, actual_files)
        assert ('pdk', 'raw-filename') not in package

    def test_parse_with_raw_filename(self):
        header = """Format: 1.0
Package: zippy
Section: contrib/net
Version: 0.6.6.1-2
Architecture: all
Files:
 bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb 267 zippy.dsc
 300039c03ecb76239b2d74ade0868311 2676 zippy.diff.gz
 aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa 111 zippy.orig.tar.gz

"""
        package = dsc.parse(header, 'zzz')
        self.assert_equal(dsc, package.package_type)
        self.assert_equals('zippy.dsc', package.pdk.raw_filename)
        self.assert_equals(267, package.size)

class TestGetPackageType(Test):
    def test_get_package_type(self):
        self.assert_equal(deb, get_package_type(filename = 'a.deb'))
        self.assert_equals(udeb, get_package_type(filename = 'a.udeb'))
        self.assert_equal(dsc, get_package_type(filename = 'a.dsc'))
        self.assert_equals(srpm, get_package_type(filename = 'a.src.rpm'))
        self.assert_equals(rpm, get_package_type(filename = 'a.rpm'))

        self.assert_equals(deb, get_package_type(format = 'deb'))
        self.assert_equals(udeb, get_package_type(format = 'udeb'))
        self.assert_equals(dsc, get_package_type(format = 'dsc'))
        self.assert_equals(srpm, get_package_type(format = 'srpm'))
        self.assert_equals(rpm, get_package_type(format = 'rpm'))

        try:
            get_package_type(filename = 'a')
        except UnknownPackageTypeError:
            pass
        else:
            self.fail('"a" is an invalid filetype')

        try:
            get_package_type(format = 'a')
        except UnknownPackageTypeError:
            pass
        else:
            self.fail('"a" is an invalid package format')

class TestSanitizeDebHeader(Test):
    def test_sanitize_deb_header(self):
        sdh = sanitize_deb_header
        self.assert_equal('a\nb\n', sdh('a\nb\n'))
        self.assert_equal('a\nb\n', sdh('\n\na\nb\n\n'))
        self.assert_equal('a\nb\n', sdh('a\nb'))

class TestGetFile(Test):
    def test_get_file(self):
        p = MockPackage('a', DebianVersion('2.3-1'), deb, arch = 'i386')
        self.assert_equal('a_2.3-1_i386.deb', deb.get_filename(p))
        self.assert_equal('a_2.3-1.dsc', dsc.get_filename(p))
        p = MockPackage('a', DebianVersion('1:2.3'), deb, arch = 'i386')
        self.assert_equal('a_2.3_i386.deb', deb.get_filename(p))
        self.assert_equal('a_2.3.dsc', dsc.get_filename(p))

class TestSynthesizeVersionString(Test):
    def set_up(self):
        self.svs = synthesize_version_string

    def test_nothing(self):
        self.assert_equal('', self.svs(None, None, None))

    def test_no_epoch(self):
        self.assert_equal('1.2-3.4', self.svs(None, '1.2', '3.4'))

    def test_all(self):
        self.assert_equal('3:4-5', self.svs('3', '4', '5'))

class TestPackageVersionCmp(Test):
    def test_deb(self):
        new = DebianVersion('2:0.4-4')
        old = DebianVersion('1.2-3')
        same_as_old = DebianVersion('1.2-3')

        assert old < new
        assert old == same_as_old

        self.assert_equal(-1, cmp(old, new))
        self.assert_equal(0, cmp(old, same_as_old))
        self.assert_equal(0, cmp(old, old))
        self.assert_equal(0, cmp(new, new))
        self.assert_equal(1, cmp(new, old))

        self.assert_equal('2', new.epoch)
        self.assert_equal('0.4', new.version)
        self.assert_equal('4', new.release)

        self.assert_equal(None, old.epoch)
        self.assert_equal('1.2', old.version)
        self.assert_equal('3', old.release)

class TestSortPackages(Test):
    def test_sort(self):
        def make_package(name, version, arch, package_type):
            return MockPackage(name, version, package_type, arch = arch)

        deb_a1 = make_package('a', '1', 'i386', deb)
        deb_a2 = make_package('a', '2', 'i386', deb)
        deb_a2_arm = make_package('a', '2', 'arm', deb)
        dsc_a1 = make_package('a', '1', 'i386', dsc)
        dsc_a2 = make_package('a', '2', 'i386', dsc)

        package_list = [ dsc_a2, deb_a2, deb_a1, deb_a2_arm, dsc_a1 ]
        package_list.sort()
        expected = [ deb_a1, deb_a2_arm, deb_a2, dsc_a1, dsc_a2 ]
        self.assert_equals_long(expected, package_list)
