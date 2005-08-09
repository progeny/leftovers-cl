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
from sets import Set
from cStringIO import StringIO as stringio
from pdk.test.utest_util import Test, TempDirTest, ShamCache, MockPackage
from pdk.package import Package, Deb, Dsc, Rpm, SRpm, RPMVersion
from pdk.cache import Cache
from pdk.rules import FieldMatchCondition, Rule

from pdk.component import find_overlaps, collate_packages, \
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

class TestFindRemovalCandidates(Test):
    def test_no_dups(self):
        a = MockPackage('a', '0:1-2', Deb())
        b = MockPackage('b', '0:1-2', Deb())

        self.assert_equal([], find_overlaps(Set([a, b])))

    def test_one_dup(self):
        a1 = MockPackage('a', '0:1-1', Deb())
        a2 = MockPackage('a', '0:1-2', Deb())

        self.assert_equals_long([(a2, [a1])], find_overlaps(Set([a1, a2])))

    def test_many_dups(self):
        a1 = MockPackage('a', '0:1-1', Deb())
        a2 = MockPackage('a', '0:1-2', Deb())
        a3 = MockPackage('a', '0:1-3', Deb())
        b1 = MockPackage('b', '0:1-1', Deb())
        b2 = MockPackage('b', '0:1-2', Deb())

        packages = Set([a1, a2, a3, b1, b2])

        self.assert_equals_long([(a3, [a2, a1]), (b2, [b1])],
                                find_overlaps(packages))

    def test_source(self):
        a1b = MockPackage('a', '0:1-1', Deb())
        a1s = MockPackage('a', '0:1-1', Dsc())

        self.assert_equals_long([], find_overlaps(Set([a1b, a1s])))


class TestCollatePackages(Test):
    def set_up(self):
        self.cp = collate_packages

    def test_none(self):
        self.assert_equal([], self.cp([]))

    def test_one(self):
        a = MockPackage('a', '0:1-2', Deb())
        self.assert_equal([(('a', 'deb'), [a])], self.cp([a]))

    def test_two(self):
        a1 = MockPackage('a', '0:1-1', Deb())
        a2 = MockPackage('a', '0:1-2', Deb())
        self.assert_equal([(('a', 'deb'), [a1, a2])], self.cp([a1, a2]))

    def test_different(self):
        a = MockPackage('a', '0:1-2', Deb())
        b = MockPackage('b', '0:1-2', Deb())
        self.assert_equals_long([(('a', 'deb'), [a]),
                                 (('b', 'deb'), [b])],
                                self.cp([a, b]))

    def test_source(self):
        a1b = MockPackage('a', '0:1-1', Deb())
        a1s = MockPackage('a', '0:1-1', Dsc())
        b = MockPackage('b', '0:1-2', Deb())
        self.assert_equals_long([(('a', 'deb'), [a1b]),
                                 (('a', 'dsc'), [a1s]),
                                 (('b', 'deb'), [b])],
                                self.cp([a1b, a1s, b]))

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
        descriptor = desc.load(None)
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
        cache.add(Package({'version': '1', 'blob-id': 'sha-1:aaa'}, Deb()))
        component = desc.load(cache)
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
        cache.add(Package({'version': '1', 'blob-id': 'sha-1:aaa'}, Deb()))
        component = desc.load(cache)
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
        component = desc.load(None)
        self.assert_equals(component.meta[component]['necessity'],
                           'optional')

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
        component = desc.load(None)
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

        apache = Package({'name': 'apache', 'version': '1',
                          'blob-id': 'sha-1:aaa'}, Deb())
        libc = Package({'name': 'libc6', 'version': '1',
                        'blob-id': 'sha-1:bbb'}, Deb())
        cache = ShamCache()
        cache.add(apache)
        cache.add(libc)

        desc_b = ComponentDescriptor('b.xml')
        component_b = desc_b.load(cache)
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
                          component_b.meta[libc]['necessity'])
        self.assert_equal('optional',
                          component_b.meta[apache]['necessity'])

        desc_a = ComponentDescriptor('a.xml')
        component_a = desc_a.load(cache)
        assert isinstance(component_a, Component)
        self.assert_equal(2, len(component_a.packages))
        self.assert_equal(['sha-1:aaa', 'sha-1:bbb'],
                          [ p.blob_id for p in component_a.packages ])
        self.assert_equal(0, len(component_a.direct_packages))
        self.assert_equal(1, len(component_a.direct_components))
        self.assert_equal(2, len(component_a.components))
        self.assert_equal('mandatory',
                          component_a.meta[libc]['necessity'])
        self.assert_equal('default',
                          component_a.meta[apache]['necessity'])
        self.assert_equal('42',
                          component_a.meta[libc]['some-random-key'])

        component_b_from_a = list(component_a.direct_components)[0]
        component_c = list(component_b_from_a.direct_components)[0]
        self.assert_equal('mandatory',
                          component_c.meta[libc]['necessity'])
        self.assert_equal('42',
                          component_c.meta[libc]['some-random-key'])
        assert apache not in component_c.meta

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
        cache.add(Package({'version': '1', 'blob-id': 'sha-1:aaa'}, Deb()))
        desc.load(cache)
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
        package = Package({'version': '1', 'blob-id': 'sha-1:aaa'}, Deb())
        cache.add(package)
        desc = ComponentDescriptor('test1.xml')
        comp = desc.load(cache)
        assert package in comp.meta
        self.assert_equal("mandatory", comp.meta[package]["necessity"])

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
        comp = desc.load(Cache())
        assert comp in comp.meta
        self.assert_equal('mandatory', comp.meta[comp]['necessity'])

class TestComponentMeta(Test):
    def test_component_meta(self):
        meta_deep = ComponentMeta()
        assert not meta_deep
        meta_deep.update({'a': {'b': 'c', 'd': 'e'}, 'b': {'f': 'g'}})
        assert meta_deep
        self.assert_equal({'b': 'c', 'd': 'e'}, meta_deep['a'])
        meta_shallow = ComponentMeta()
        meta_shallow.update(meta_deep)
        meta_shallow.update({'a': {'b': 'h'}})
        self.assert_equal({'b': 'h', 'd': 'e'}, meta_shallow['a'])

class TestPackageRef(Test):
    def test_verify(self):
        apache = Package({'name': 'apache', 'version': '1',
                          'blob-id': 'sha-1:aaa'}, Deb())
        libc = Package({'name': 'libc6', 'version': '1',
                        'blob-id': 'sha-1:aaa'}, Deb())

        condition = FieldMatchCondition('name', 'apache')
        rule = Rule(condition, [])
        ref = PackageReference(Deb(), 'sha-1:aaa', rule, [], None)
        good_cache = ShamCache()
        good_cache.add(apache)
        assert ref.verify(good_cache)

        bad_cache = ShamCache()
        bad_cache.add(libc)

        assert not ref.verify(bad_cache)

    def test_is_abstract(self):
        concrete_ref = PackageReference(Deb(), 'sha-1:aaa', None, [], None)
        assert not concrete_ref.is_abstract()

        abstract_ref = PackageReference(Deb(), None, None, [], None)
        assert abstract_ref.is_abstract()

    def test_get_child_condition_fn(self):
        apache_deb = Package({'name': 'apache', 'version': '1',
                              'blob-id': 'sha-1:aaa'}, Deb())
        apache_rpm = Package({'name': 'apache', 'version': '1',
                              'blob-id': 'sha-1:aaa'}, Rpm())
        apache_dsc = Package({'name': 'apache', 'version': '1',
                              'blob-id': 'sha-1:aaa'}, Dsc())
        apache_srpm = Package({'name': 'apache', 'version': '1',
                               'blob-id': 'sha-1:aaa'}, SRpm())

        self.assert_equals(get_deb_child_condition_data,
                           get_child_condition_fn(apache_deb))
        self.assert_equals(get_dsc_child_condition_data,
                           get_child_condition_fn(apache_dsc))
        self.assert_equals(get_rpm_child_condition_data,
                           get_child_condition_fn(apache_rpm))
        self.assert_equals(get_srpm_child_condition_data,
                           get_child_condition_fn(apache_srpm))

    def test_get_deb_child_condition_data(self):
        apache_deb = Package({'name': 'apache', 'version': '1',
                              'blob-id': 'sha-1:aaa',
                              'sp_name': 'one', 'sp_version': 'two'}, Deb())

        expected = [ ('name', 'one'),
                     ('version', 'two'),
                     ('type', 'dsc') ]

        self.assert_equals(expected,
                           get_deb_child_condition_data(apache_deb))

    def test_get_dsc_child_condition_data(self):
        apache_dsc = Package({'name': 'apache', 'version': '1',
                              'blob-id': 'sha-1:aaa'}, Dsc())

        expected = [ ('sp_name', 'apache'),
                     ('sp_version', '1'),
                     ('type', 'deb') ]

        self.assert_equals(expected,
                           get_dsc_child_condition_data(apache_dsc))


    def test_get_rpm_child_conditoin_data(self):
        apache_rpm = Package({'name': 'apache', 'version': '1',
                              'blob-id': 'sha-1:aaa',
                              'source-rpm': 'apache-1.src.rpm'}, Rpm())
        expected = [ ('filename', 'apache-1.src.rpm'),
                     ('type', 'srpm') ]

        self.assert_equals(expected,
                           get_rpm_child_condition_data(apache_rpm))

    def test_get_srpm_child_conditoin_data(self):
        version = RPMVersion(version_tuple = (None, '1', '2'))
        apache_srpm = Package({'name': 'apache',
                               'version': version,
                               'blob-id': 'sha-1:aaa'}, SRpm())
        expected = [ ('sourcerpm', 'apache-1-2.src.rpm'),
                     ('type', 'rpm') ]

        self.assert_equals(expected,
                           get_srpm_child_condition_data(apache_srpm))

