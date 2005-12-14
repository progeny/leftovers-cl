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
from pdk.meta import Entity, Entities
from pdk.cache import Cache
from pdk.rules import AndCondition, OrCondition, FieldMatchCondition, \
     RelationCondition
from operator import lt, le, gt, ge

from pdk.component import \
     ComponentDescriptor, Component, PackageReference, \
     get_child_condition_fn, \
     get_deb_child_condition_data, \
     get_dsc_child_condition_data, \
     get_rpm_child_condition_data, \
     get_srpm_child_condition_data, \
     ActionLinkEntities, \
     ActionUnlinkEntities, \
     ActionMetaSet, \
     build_condition


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

class TestActions(Test):
    def test_link_ent_str(self):
        action = ActionLinkEntities('a', 'b')
        self.assert_equals("link ('a', 'b')", str(action))

    def test_link_exe(self):
        ent = Entity('c', 'd')
        action = ActionLinkEntities('a', 'b')
        entities = Entities()

        action.execute(ent, entities)
        self.assert_equal({('c', 'd'): [('a', 'b')]}, entities.links)

    def test_unlink_ent_str(self):
        action = ActionUnlinkEntities('a', 'b')
        self.assert_equals("unlink ('a', 'b')", str(action))

    def test_unlink_exe(self):
        ent = Entity('c', 'd')
        action = ActionUnlinkEntities('a', 'b')
        entities = Entities()
        entities.links = {('c', 'd'): [('a', 'b')]}
        action.execute(ent, entities)
        self.assert_equal({('c', 'd'): []}, entities.links)

    def test_action_meta_set(self):
        action = ActionMetaSet('a', 'b', 'c')
        actual = {}
        action.execute(actual, None)
        self.assert_equals({('a', 'b'): 'c'}, actual)

class TestCompDesc(TempDirTest):
    def test_read_relation_condition(self):
        os.system('''
cat >a.xml <<EOF
<component>
  <contents>
    <deb>
      <version>2.0.53</version>
      <version-lt>2.0.53</version-lt>
      <version-lt-eq>2.0.53</version-lt-eq>
      <version-gt>2.0.53</version-gt>
      <version-gt-eq>2.0.53</version-gt-eq>
    </deb>
    <dsc>
      <version>2.0.53</version>
      <version-lt>2.0.53</version-lt>
    </dsc>
    <rpm>
      <version>2.0.53</version>
      <version-lt>2.0.53</version-lt>
    </rpm>
    <srpm>
      <version>2.0.53</version>
      <version-lt>2.0.53</version-lt>
    </srpm>
  </contents>
</component>
''')
        desc = ComponentDescriptor('a.xml')
        deb_ref = desc.contents[0]
        dv = DebianVersion
        self.assert_equal(('pdk', 'version', dv('2.0.53')),
                          deb_ref.fields[0])
        self.assert_equal((lt, 'pdk', 'version', dv('2.0.53')),
                          deb_ref.fields[1])
        self.assert_equal((le, 'pdk', 'version', dv('2.0.53')),
                          deb_ref.fields[2])
        self.assert_equal((gt, 'pdk', 'version', dv('2.0.53')),
                          deb_ref.fields[3])
        self.assert_equal((ge, 'pdk', 'version', dv('2.0.53')),
                          deb_ref.fields[4])

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
        cache.add(MockPackage('a', '1', deb, 'sha-1:aaa'))
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
        cache.add(MockPackage('a', '1', deb, 'sha-1:aaa'))
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
        self.assert_equals(component.meta['pdk', 'necessity'], 'optional')

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

        apache = MockPackage('apache', '1', deb,'sha-1:aaa')
        libc = MockPackage('libc6', '1', deb, 'sha-1:bbb')
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
                          libc['pdk', 'necessity'])
        self.assert_equal('optional',
                          apache['pdk', 'necessity'])

        apache = MockPackage('apache', '1', deb,'sha-1:aaa')
        libc = MockPackage('libc6', '1', deb, 'sha-1:bbb')
        cache = ShamCache()
        cache.add(apache)
        cache.add(libc)

        desc_a = ComponentDescriptor('a.xml')
        component_a = desc_a.load(cache)
        assert isinstance(component_a, Component)
        self.assert_equal(2, len(component_a.packages))
        self.assert_equal(['sha-1:aaa', 'sha-1:bbb'],
                          [ p.blob_id for p in component_a.packages ])
        self.assert_equal(0, len(component_a.direct_packages))
        self.assert_equal(1, len(component_a.direct_components))
        self.assert_equal(2, len(component_a.components))
        self.assert_equal('mandatory', libc['pdk', 'necessity'])
        self.assert_equal('default', apache['pdk', 'necessity'])
        self.assert_equal('42', libc['pdk', 'some-random-key'])

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
        package = MockPackage('a', '1', deb, 'sha-1:aaa')
        cache.add(package)
        desc = ComponentDescriptor('test1.xml')
        comp = desc.load(cache)
        assert package in comp.packages
        self.assert_equal("mandatory", package[('pdk', 'necessity')])

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
        comp = desc.load(Cache(os.path.join(self.work_dir, 'cache')))
        self.assert_equal('mandatory', comp.meta[('pdk', 'necessity')])

    def test_iter_package_refs(self):
        class MockRef(PackageReference):
            def __init__(self, label):
                PackageReference.__init__(self, deb, None,
                                          [('pdk', 'name', 'apache')], [])
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

    def test_parse_entity(self):
        '''Check that we can parse entities at all.'''
        open('test.xml', 'w').write('''<?xml version="1.0"?>
<component>
  <entities>
    <some-ent id="can-do">
      <a.name>hello</a.name>
      <b.description>whodo whodo whodo</b.description>
    </some-ent>
  </entities>
</component>
''')

        desc = ComponentDescriptor('test.xml')
        entity1 = desc.entities[('some-ent', 'can-do')]
        self.assert_equal('hello', entity1[('a', 'name')])
        self.assert_equal('whodo whodo whodo',
                          entity1[('b', 'description')])
        cache = ShamCache()
        comp = desc.load(cache)
        entity2 = comp.entities[('some-ent', 'can-do')]
        self.assert_equal('hello', entity2[('a', 'name')])
        self.assert_equal('whodo whodo whodo',
                          entity2[('b', 'description')])

    def test_parse_link(self):
        '''Check that we can parse entities at all.'''
        open('test.xml', 'w').write('''<?xml version="1.0"?>
<component>
  <contents>
    <deb ref="sha-1:aaa">
      <meta>
        <pdk.link>
          <some-meta>can-do</some-meta>
        </pdk.link>
      </meta>
    </deb>
  </contents>
</component>
''')

        desc = ComponentDescriptor('test.xml')
        self.assert_equal([('some-meta', 'can-do')], desc.contents[0].links)
        cache = ShamCache()
        package = MockPackage('a', '1', deb, 'sha-1:aaa')
        cache.add(package)
        comp = desc.load(cache)
        self.assert_equals([('some-meta', 'can-do')],
                           comp.entities.links['deb', 'sha-1:aaa'])

class TestPackageRef(Test):
    def test_build_condition(self):
        fields = \
               [ ('pdk', 'name', 'a'),
                 ('deb', 'arch', 'c'),
                 [ 'or',
                   ('deb', 'hello', 'e'),
                   ('deb', 'hello', 'f') ],
                 (ge, 'pdk', 'version', 4) ]
        condition = build_condition(fields)
        assert isinstance(condition, AndCondition)
        and_conds = condition.conditions
        self.assert_equals(4, len(and_conds))

        assert isinstance(and_conds[0], FieldMatchCondition)
        self.assert_equals('pdk', and_conds[0].domain)
        self.assert_equals('name', and_conds[0].field_name)
        self.assert_equals('a', and_conds[0].target)

        assert isinstance(and_conds[1], FieldMatchCondition)
        self.assert_equals('deb', and_conds[1].domain)
        self.assert_equals('arch', and_conds[1].field_name)
        self.assert_equals('c', and_conds[1].target)

        assert isinstance(and_conds[2], OrCondition)
        or_conds = and_conds[2].conditions
        self.assert_equals(2, len(or_conds))

        assert isinstance(or_conds[0], FieldMatchCondition)
        self.assert_equals('deb', or_conds[0].domain)
        self.assert_equals('hello', or_conds[0].field_name)
        self.assert_equals('e', or_conds[0].target)

        assert isinstance(or_conds[1], FieldMatchCondition)
        self.assert_equals('deb', or_conds[1].domain)
        self.assert_equals('hello', or_conds[1].field_name)
        self.assert_equals('f', or_conds[1].target)

        assert isinstance(and_conds[3], RelationCondition)
        self.assert_equals(ge, and_conds[3].condition)
        self.assert_equals('pdk', and_conds[3].domain)
        self.assert_equals('version', and_conds[3].predicate)
        self.assert_equals(4, and_conds[3].value)

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
        ref = PackageReference(deb, 'sha-1:aaa',
                               [('pdk', 'name', 'apache')], [])

        assert ('pdk', 'name') in ref
        assert ('pdk', 'version') not in ref
        self.assert_equal('apache', ref[('pdk', 'name')])
        self.assert_equal('apache', ref.name)
        self.assert_equal('', ref.version)
        self.assert_equal('', ref.arch)

    def test_comparable(self):
        fields = [('pdk', 'name', 'apache')]
        refa1 = PackageReference(deb, 'sha-1:aaa', fields, [])
        refa2 = PackageReference(deb, 'sha-1:aaa', fields, [])
        refb = PackageReference(deb, 'sha-1:aaa',
                                [('pdk', 'name', 'xsok')], [])

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
        extra = {('pdk', 'sp-name'): 'one',
                 ('pdk', 'sp-version'): sp_version}
        apache_deb = MockPackage('apache', '1', deb, 'sha-1:aaa', extra)

        expected = [ ('pdk', 'name', 'one'),
                     ('pdk', 'version', '1-2'),
                     ('pdk', 'type', 'dsc') ]

        self.assert_equals(expected,
                           get_deb_child_condition_data(apache_deb))

    def test_get_dsc_child_condition_data(self):
        version = DebianVersion('1-2')
        apache_dsc = MockPackage('apache', version, dsc, 'sha-1:aaa')

        expected = [ ('pdk', 'sp-name', 'apache'),
                     ('pdk', 'sp-version', '1-2'),
                     [ 'or',
                       ('pdk', 'type', 'deb'),
                       ('pdk', 'type', 'udeb') ] ]

        self.assert_equals(expected,
                           get_dsc_child_condition_data(apache_dsc))


    def test_get_rpm_child_condition_data(self):
        version = RPMVersion(version_string = '1-2')
        extras = {('pdk', 'source-rpm'): 'apache.src.rpm'}
        apache_rpm = MockPackage('apache', version, rpm, 'sha-1:aaa',
                                 extras = extras)

        expected = [ ('pdk', 'filename', 'apache.src.rpm'),
                     ('pdk', 'type', 'srpm') ]

        self.assert_equals(expected,
                           get_rpm_child_condition_data(apache_rpm))

    def test_get_srpm_child_condition_data(self):
        version = RPMVersion(version_string = '1-2')
        apache_srpm = MockPackage('apache', version, srpm, 'sha-1:aaa')
        expected = [ ('pdk', 'source-rpm', 'apache-1-2.src.rpm'),
                     ('pdk', 'type', 'rpm') ]

        self.assert_equals(expected,
                           get_srpm_child_condition_data(apache_srpm))

