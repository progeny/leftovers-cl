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

"""Unit test for component operations"""
import os
from cStringIO import StringIO as stringio
from pdk.test.utest_util import Test, TempDirTest, ShamCache, MockPackage
from pdk.package import udeb, deb, dsc, rpm, srpm, RPMVersion, \
     DebianVersion
from pdk.cache import Cache

from pdk.component import \
     ComponentDescriptor, Component, ComponentMeta, PackageReference, \
     get_child_condition_fn, \
     get_deb_child_condition_data, \
     get_dsc_child_condition_data, \
     get_rpm_child_condition_data, \
     get_srpm_child_condition_data

__revision__ = "$Progeny$"

class MockUriHelper(dict):
    def __getattr__(self, name):
        return self[name]

class MockCache(object):
    def __init__(self):
        self.packages = []

    def load_package(self, blob_id, format):
        ref = (blob_id, format)
        if ref not in self.packages:
            self.packages.append(ref)
        return ref

class TestParseDomain(Test):
    def test_parse_domain(self):
        pd = ComponentDescriptor.parse_domain
        self.assert_equal(('', 'zz'), pd('zz'))
        self.assert_equal(('deb', 'name'), pd('deb.name'))
        self.assert_equal(('deb', 'deb.name'), pd('deb.deb.name'))

class TestCompDesc(TempDirTest):
    def test_load_empty(self):
        """compdesc.load returns an empty component"""
        os.system('''
cat >a.xml <<EOF
<?xml version="1.0" encoding="utf-8"?>
<component/>
EOF
''')
        desc = ComponentDescriptor('a.xml')
        meta = ComponentMeta()
        descriptor = desc.load(meta, None)
        assert isinstance(descriptor, Component)

    def test_load(self):
        """compdesc.load returns a component with packages"""
        os.system('''
cat >a.xml <<EOF
<?xml version="1.0" encoding="utf-8"?>
<component>
  <contents>
    <deb ref="sha-1:aaa"/>
  </contents>
</component>
EOF
''')
        desc = ComponentDescriptor('a.xml')
        cache = ShamCache()
        cache.add(MockPackage('a', '1', deb, 'sha-1:aaa'))
        meta = ComponentMeta()
        component = desc.load(meta, cache)
        assert isinstance(component, Component)
        self.assert_equal(1, len(component.packages))
        self.assert_equal(1, len(component.direct_packages))
        self.assert_equal(['sha-1:aaa'],
                          [ p.blob_id for p in component.packages ])
        self.assert_equal(0, len(component.direct_components))
        self.assert_equal(0, len(component.components))

    def test_load_file_object(self):
        """compdesc.load returns a component with packages"""
        handle = stringio('''<?xml version="1.0" encoding="utf-8"?>
<component>
  <contents>
    <deb ref="sha-1:aaa"/>
  </contents>
</component>
''')
        desc = ComponentDescriptor('a.xml', handle)
        cache = ShamCache()
        cache.add(MockPackage('a', '1', deb, 'sha-1:aaa'))
        meta = ComponentMeta()
        component = desc.load(meta, cache)
        assert isinstance(component, Component)
        self.assert_equal('a.xml', desc.filename)
        self.assert_equal(1, len(component.packages))
        self.assert_equal(1, len(component.direct_packages))
        self.assert_equal(['sha-1:aaa'],
                          [ p.blob_id for p in component.packages ])
        self.assert_equal(0, len(component.direct_components))
        self.assert_equal(0, len(component.components))

    def test_load_component_meta(self):
        """compdesc.load finds component metadata"""
        os.system('''
cat >a.xml <<EOF
<?xml version="1.0" encoding="utf-8"?>
<component>
  <meta>
    <necessity>optional</necessity>
  </meta>
</component>
EOF
''')
        desc = ComponentDescriptor('a.xml')
        meta = ComponentMeta()
        component = desc.load(meta, None)
        self.assert_equals(meta[component]['necessity'], 'optional')

    def test_load_fields(self):
        """compdesc.load populates id, name, etc. fields"""
        os.system('''
cat >a.xml <<EOF
<?xml version="1.0"?>
<component>
  <id>resolveme</id>
  <name>Resolve Me</name>
  <description>
    I need to be resolved
  </description>
  <requires>a</requires>
  <requires>b</requires>
  <provides>c</provides>
  <provides>d</provides>
</component>
EOF
''')
        desc = ComponentDescriptor('a.xml')
        meta = ComponentMeta()
        component = desc.load(meta, None)
        self.assert_equals('resolveme', component.id)
        self.assert_equals('Resolve Me', component.name)
        self.assert_equals('\n    I need to be resolved\n  ',
                           component.description)
        self.assert_equals(['a', 'b'], component.requires)
        self.assert_equals(['c', 'd'], component.provides)

    def test_load_multilevel(self):
        """test loading a component that refers to another"""
        os.system('''
cat >a.xml <<EOF
<?xml version="1.0" encoding="utf-8"?>
<component>
  <contents>
    <deb>
      <name>libc6</name>
      <meta>
        <necessity>mandatory</necessity>
      </meta>
    </deb>
    <deb>
      <name>apache</name>
      <meta>
        <necessity>default</necessity>
      </meta>
    </deb>
    <component>b.xml</component>
  </contents>
</component>
EOF
''')
        os.system('''
cat >b.xml <<EOF
<?xml version="1.0" encoding="utf-8"?>
<component>
  <contents>
    <deb>
      <name>libc6</name>
      <meta>
        <necessity>optional</necessity>
      </meta>
    </deb>
    <deb ref="sha-1:aaa">
      <name>apache</name>
      <meta>
        <necessity>optional</necessity>
      </meta>
    </deb>
    <component>c.xml</component>
  </contents>
</component>
EOF
''')
        os.system('''
cat >c.xml <<EOF
<?xml version="1.0" encoding="utf-8"?>
<component>
  <contents>
    <deb ref="sha-1:bbb">
      <name>libc6</name>
      <meta>
        <necessity>mandatory</necessity>
        <some-random-key>42</some-random-key>
      </meta>
    </deb>
  </contents>
</component>
EOF
''')

        apache = MockPackage('apache', '1', deb,'sha-1:aaa')
        libc = MockPackage('libc6', '1', deb, 'sha-1:bbb')
        cache = ShamCache()
        cache.add(apache)
        cache.add(libc)

        meta = ComponentMeta()
        desc_b = ComponentDescriptor('b.xml')
        component_b = desc_b.load(meta, cache)
        assert isinstance(component_b, Component)
        self.assert_equal('b.xml', desc_b.filename)
        self.assert_equal('b.xml', component_b.ref)
        self.assert_equal(2, len(component_b.packages))
        self.assert_equal(['sha-1:aaa', 'sha-1:bbb'],
                          [ p.blob_id for p in component_b.packages ])
        self.assert_equal(1, len(component_b.direct_packages))
        self.assert_equal(1, len(component_b.direct_components))
        self.assert_equal(1, len(component_b.components))
        self.assert_equal('optional',
                          meta[libc]['necessity'])
        self.assert_equal('optional',
                          meta[apache]['necessity'])

        meta = ComponentMeta()
        desc_a = ComponentDescriptor('a.xml')
        component_a = desc_a.load(meta, cache)
        assert isinstance(component_a, Component)
        self.assert_equal(2, len(component_a.packages))
        self.assert_equal(['sha-1:aaa', 'sha-1:bbb'],
                          [ p.blob_id for p in component_a.packages ])
        self.assert_equal(0, len(component_a.direct_packages))
        self.assert_equal(1, len(component_a.direct_components))
        self.assert_equal(2, len(component_a.components))
        self.assert_equal('mandatory', meta[libc]['necessity'])
        self.assert_equal('default', meta[apache]['necessity'])
        self.assert_equal('42', meta[libc]['some-random-key'])

    def test_empty_meta_element(self):
        open('test.xml', 'w').write('''<?xml version="1.0"?>
<component>
  <meta/>
</component>
''')
        desc = ComponentDescriptor('test.xml')
        desc.write()
        expected = '''<?xml version="1.0" encoding="utf-8"?>
<component>
</component>
'''
        self.assert_equals_long(expected, open('test.xml').read())

    def test_occupied_meta_element(self):
        open('test.xml', 'w').write('''<?xml version="1.0"?>
<component>
  <meta>
    <key>value</key>
  </meta>
  <contents>
    <deb ref="sha-1:aaa">
      <meta>
        <other-key>other-value</other-key>
      </meta>
    </deb>
  </contents>
</component>
''')
        desc = ComponentDescriptor('test.xml')
        desc.write()
        expected = '''<?xml version="1.0" encoding="utf-8"?>
<component>
  <meta>
    <key>value</key>
  </meta>
  <contents>
    <deb ref="sha-1:aaa">
      <meta>
        <other-key>other-value</other-key>
      </meta>
    </deb>
  </contents>
</component>
'''
        self.assert_equals_long(expected, open('test.xml').read())

    def test_dont_mutate_meta(self):
        """Make sure the load method does not mutate the meta info
        in the descriptor.
        """
        open('test.xml', 'w').write('''<?xml version="1.0"?>
<component>
  <meta>
    <predicate>object</predicate>
  </meta>
  <contents>
    <dsc>
      <name>a</name>
      <meta>
        <c>d</c>
      </meta>
    </dsc>
    <deb ref="sha-1:aaa">
      <meta>
        <necessity>mandatory</necessity>
      </meta>
    </deb>
  </contents>
</component>
''')
        desc = ComponentDescriptor('test.xml')
        cache = ShamCache()
        cache.add(MockPackage('a', '1', deb, 'sha-1:aaa'))
        meta = ComponentMeta()
        desc.load(meta, cache)
        desc.write()
        expected = '''<?xml version="1.0" encoding="utf-8"?>
<component>
  <meta>
    <predicate>object</predicate>
  </meta>
  <contents>
    <dsc>
      <name>a</name>
      <meta>
        <c>d</c>
      </meta>
    </dsc>
    <deb ref="sha-1:aaa">
      <meta>
        <necessity>mandatory</necessity>
      </meta>
    </deb>
  </contents>
</component>
'''
        self.assert_equals_long(expected, open('test.xml').read())

    def test_load_sub_component_meta(self):
        """Be sure metadata gets loaded from subcomponents even if
        the toplevel component has none.
        """
        open('test1.xml', 'w').write('''<?xml version="1.0"?>
<component>
  <contents>
    <component>test2.xml</component>
  </contents>
</component>
''')
        open('test2.xml', 'w').write('''<?xml version="1.0"?>
<component>
  <contents>
    <deb ref="sha-1:aaa">
      <meta>
        <necessity>mandatory</necessity>
      </meta>
    </deb>
  </contents>
</component>
''')
        cache = ShamCache()
        package = MockPackage('a', '1', deb, 'sha-1:aaa')
        cache.add(package)
        meta = ComponentMeta()
        desc = ComponentDescriptor('test1.xml')
        desc.load(meta, cache)
        assert package in meta
        self.assert_equal("mandatory", meta[package]["necessity"])

    def test_meta_implicit_ref(self):
        """Check that implicit references in metadata are supported and
        correctly resolve to references to self.
        """
        open('test.xml', 'w').write('''<?xml version="1.0"?>
<component>
  <meta>
    <necessity>mandatory</necessity>
  </meta>
</component>
''')
        desc = ComponentDescriptor('test.xml')
        meta = ComponentMeta()
        comp = desc.load(meta, Cache(os.path.join(self.work_dir, 'cache')))
        assert comp in meta
        self.assert_equal('mandatory', meta[comp]['necessity'])

    def test_iter_package_refs(self):
        class MockRef(PackageReference):
            def __init__(self, label):
                PackageReference.__init__(self, deb, None,
                                          [('name', 'apache')], [])
                self.label = label
                self.children = []

            def __repr__(self):
                return str(self.label)

        desc = ComponentDescriptor(None)
        a = MockRef('a')
        b = MockRef('b')
        c = MockRef('c')
        a.children = [b]
        desc.contents = [ a, c ]

        self.assert_equal([a, c], list(desc.iter_package_refs()))
        self.assert_equal([a, b, c], list(desc.iter_full_package_refs()))

class TestPackageRef(Test):
    def test_is_abstract(self):
        concrete_ref_a = \
            PackageReference(deb, 'sha-1:aaa', None, None)
        assert not concrete_ref_a.is_abstract()

        concrete_ref_b = PackageReference(deb, None, None, None)
        concrete_ref_b.children.append(concrete_ref_a)
        assert not concrete_ref_b.is_abstract()

        abstract_ref = PackageReference(deb, None, None, None)
        assert abstract_ref.is_abstract()

    def test_field_lookups(self):
        ref = PackageReference(deb, 'sha-1:aaa', [('name', 'apache')], [])

        assert 'name' in ref
        assert 'version' not in ref
        self.assert_equal('apache', ref['name'])
        self.assert_equal('apache', ref.name)
        self.assert_equal('', ref.version)
        self.assert_equal('', ref.arch)

    def test_comparable(self):
        fields = [('name', 'apache')]
        refa1 = PackageReference(deb, 'sha-1:aaa', fields, [])
        refa2 = PackageReference(deb, 'sha-1:aaa', fields, [])
        refb = PackageReference(deb, 'sha-1:aaa', [('name', 'xsok')], [])

        assert refa1 == refa2
        assert refa1 < refb

    def test_get_child_condition_fn(self):
        apache_deb = MockPackage('apache', '1', deb, 'sha-1:aaa')
        apache_udeb = MockPackage('apache', '1', udeb, 'sha-1:aaa')
        apache_rpm = MockPackage('apache', '1', rpm, 'sha-1:aaa')
        apache_dsc = MockPackage('apache', '1', dsc, 'sha-1:aaa')
        apache_srpm = MockPackage('apache', '1', srpm, 'sha-1:aaa')

        self.assert_equals(get_deb_child_condition_data,
                           get_child_condition_fn(apache_deb))
        self.assert_equals(get_deb_child_condition_data,
                           get_child_condition_fn(apache_udeb))
        self.assert_equals(get_dsc_child_condition_data,
                           get_child_condition_fn(apache_dsc))
        self.assert_equals(get_rpm_child_condition_data,
                           get_child_condition_fn(apache_rpm))
        self.assert_equals(get_srpm_child_condition_data,
                           get_child_condition_fn(apache_srpm))

    def test_get_deb_child_condition_data(self):
        sp_version = DebianVersion('1-2')
        extra = {'sp-name': 'one', 'sp-version': sp_version}
        apache_deb = MockPackage('apache', '1', deb, 'sha-1:aaa', **extra)

        expected = [ ('name', 'one'),
                     ('version', '1-2'),
                     ('type', 'dsc') ]

        self.assert_equals(expected,
                           get_deb_child_condition_data(apache_deb))

    def test_get_dsc_child_condition_data(self):
        version = DebianVersion('1-2')
        apache_dsc = MockPackage('apache', version, dsc, 'sha-1:aaa')

        expected = [ ('sp-name', 'apache'),
                     ('sp-version', '1-2'),
                     [ 'or',
                       ('type', 'deb'),
                       ('type', 'udeb') ] ]

        self.assert_equals(expected,
                           get_dsc_child_condition_data(apache_dsc))


    def test_get_rpm_child_condition_data(self):
        version = RPMVersion(version_tuple = (None, '1', '2'))
        extra = {'source-rpm': 'apache.src.rpm'}
        apache_rpm = MockPackage('apache', version, rpm, 'sha-1:aaa',
                                 **extra)

        expected = [ ('filename', 'apache.src.rpm'),
                     ('type', 'srpm') ]

        self.assert_equals(expected,
                           get_rpm_child_condition_data(apache_rpm))

    def test_get_srpm_child_condition_data(self):
        version = RPMVersion(version_tuple = (None, '1', '2'))
        apache_srpm = MockPackage('apache', version, srpm, 'sha-1:aaa')
        expected = [ ('source-rpm', 'apache-1-2.src.rpm'),
                     ('type', 'rpm') ]

        self.assert_equals(expected,
                           get_srpm_child_condition_data(apache_srpm))

