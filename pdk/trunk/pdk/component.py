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

"""
component.py

This module houses functionality related to using, creating, and
machine modifying components.

"""
import os
from pdk.util import write_pretty_xml, parse_xml
from cElementTree import ElementTree, Element, SubElement
from pdk.rules import Rule, CompositeRule, AndCondition, OrCondition, \
     FieldMatchCondition
from pdk.package import get_package_type, Package
from pdk.exceptions import PdkException, CommandLineError, InputError, \
     SemanticError
from xml.parsers.expat import ExpatError
from pdk.log import get_logger
from pdk.workspace import current_workspace



def dumpmeta(component_refs):
    """Print all component metadata to standard out."""
    cache = current_workspace().cache()
    for component_ref in component_refs:
        component = ComponentDescriptor(component_ref).load(cache)
        for item in component.meta:
            predicates = component.meta[item]
            for key, value in predicates.iteritems():
                if isinstance(item, Package):
                    ref = item.blob_id
                    name = item.name
                    type_string = item.type
                else:
                    ref = item.ref
                    name = ''
                    type_string = 'component'
                print '|'.join([ref, type_string, name, key, value])


def resolve(args):
    """resolve resolves abstract package references

    *This needs a detailed usage message*

    If the command succeeds, the component will be modified in place.
    Abstract references will be rewritten to concrete references, and
    missing constraint elements will be placed.

    The command takes a single component descriptor followed by zero
    or more channel names.

    If not channel names are given, resolve uses all channels to
    resolve references.

    A warning is given if any unresolved references remain.
    """
    if len(args) < 1:
        raise CommandLineError, 'component descriptor required'
    workspace = current_workspace()
    component_name = args[0]
    descriptor = ComponentDescriptor(component_name)
    channel_names = args[1:]
    channels = workspace.channels()
    package_list = channels.get_package_list(channel_names)
    descriptor.resolve(package_list)

    descriptor._assert_resolved()


def download(args):
    """
    download: Make local copies of the package files needed by the 
    descriptor FILE.  The needed package files will be located based 
    on the package index on configured channels.
    usage: download FILE

    Valid options:
    none
    """
    if len(args) != 1:
        raise CommandLineError, 'download takes a component descriptor'
    descriptor = ComponentDescriptor(args[0])
    descriptor.download()


def find_overlaps(packages):
    """Group packages by their names, 'newest' package first in a group."""
    overlaps = []
    def reverse_version_compare(a, b):
        """Reverse sense of version comparison"""
        return -cmp(a.version, b.version)
    for dummy, package_group in collate_packages(packages):
        if len(package_group) > 1:
            sorted = package_group[:]
            sorted.sort(reverse_version_compare)
            overlaps.append((sorted[0], sorted[1:]))
    return overlaps


def collate_packages(packages):
    """Group packages into a sorted list by package name,type."""
    collated = {}
    for package in packages:
        key = (package.name, package.type)
        collated.setdefault(key, []).append(package)
    keys = collated.keys()
    keys.sort()
    return [ (k, collated[k]) for k in keys ]


class ComponentDescriptor(object):
    """Represents a component descriptor object.

    This class is for looking at a convenient abstraction of the raw
    contents of a descriptor.

    Use the meta and contents properties to change the descriptor.

    Use load(cache) to instantiate trees of Component objects.
    """
    def __init__(self, filename, handle = None):
        self.filename = filename
        if handle:
            try:
                tree = parse_xml(handle)
            except ExpatError, message:
                raise InputError(message)

        else:
            if os.path.exists(filename):
                try:
                    tree = parse_xml(filename)
                except ExpatError, message:
                    raise InputError(filename, message)
            else:
                tree = ElementTree(element = Element('component'))

        self.id = ''
        self.name = ''
        self.description = ''
        self.requires = []
        self.provides = []

        self.meta = []
        self.contents = []

        self.build_component_descriptor(tree.getroot())

    def load(self, cache):
        """Instantiate a component object tree for this descriptor."""
        component = Component(self.filename)
        field_names = ('id', 'name', 'description', 'requires', 'provides')
        for field_name in field_names:
            value = getattr(self, field_name)
            setattr(component, field_name, value)

        group_message = ""
        local_rules = []
        for ref in self.contents:
            try:
                if isinstance(ref, PackageReference):
                    if ref.blob_id:
                        refs = [ref] + ref.children
                    else:
                        local_rules.append(ref.rule)
                        refs = ref.children
                    for concrete_ref in refs:
                        package = concrete_ref.load(cache)
                        component.packages.append(package)
                        component.direct_packages.append(package)
                        if not concrete_ref.verify(cache):
                            message = 'Concrete package does not ' \
                                      'meet expected constraints: %s' \
                                      % concrete_ref.blob_id, package.name
                            raise SemanticError(message)
                        local_rules.append(concrete_ref.rule)
                elif isinstance(ref, ComponentReference):
                    child_descriptor = ref.load()
                    child_component = child_descriptor.load(cache)
                    component.direct_components.append(child_component)
                    component.components.append(child_component)
                    component.components.extend(child_component.components)
                    component.packages.extend(child_component.packages)
                    component.rules.extend(child_component.rules)

            except PdkException, local_message:
                if group_message:
                    group_message = group_message + "\n"
                group_message = group_message + \
                    "Problems found in %s:\n%s" % (self.filename,
                                                   local_message)

        if group_message:
            raise SemanticError(group_message)

        component.rules.extend(local_rules)
        uber_rule = CompositeRule(component.rules)
        for package in component.packages:
            for package, key, value in uber_rule.fire(package):
                component.meta.update({package: {key: value}})
        for decendent_component in component.components:
            for found_component, key, value in \
                    uber_rule.fire(decendent_component):
                component.meta.update({found_component: {key: value}})
        component.meta.update({component: dict(self.meta)})

        return component


    def write(self):
        '''Write the potentially modified descriptor back to xml.

        The original filename is overwritten.
        '''
        tree = ElementTree(element = Element('component'))
        root = tree.getroot()

        # construct the simple fields first.
        simple_fields = [ ('id', self.id),
                          ('name', self.name),
                          ('description', self.description) ]
        for multifield_name in ('requires', 'provides'):
            values = getattr(self, multifield_name)
            for value in values:
                simple_fields.append((multifield_name, value))

        for name, value in simple_fields:
            if value:
                element = SubElement(root, name)
                element.text = value

        # create and populate meta element if we have metadata.
        if len(self.meta) > 0:
            meta_element = SubElement(root, 'meta')
            for predicate in self.meta:
                meta_child = SubElement(meta_element, predicate[0])
                meta_child.text = predicate[1]

        if self.contents:
            contents_element = SubElement(root, 'contents')

        # last, write the contents element
        for reference in self.contents:
            if isinstance(reference, PackageReference):
                self.write_package_reference(contents_element, reference)
            elif isinstance(reference, ComponentReference):
                component_element = SubElement(contents_element,
                                               'component')
                component_element.text = reference.filename
        dirname = os.path.dirname(self.filename) or "."
        if not os.path.exists(dirname):
            os.makedirs(dirname)
        write_pretty_xml(tree, self.filename)

    def write_package_reference(self, parent, reference):
        """Build elements for a single package reference."""
        attributes = {}
        if reference.blob_id:
            attributes['ref'] = reference.blob_id
        name = reference.package_type.type_string
        ref_element = SubElement(parent, name, attributes)

        assert hasattr(reference.rule.condition, 'conditions'), \
            'Package rules should always be flat AndConditions'
        for condition in reference.rule.condition.conditions:
            if condition.field_name in ('blob-id', 'type'):
                continue
            condition_element = SubElement(ref_element,
                                           condition.field_name)
            condition_element.text = condition.target

        for inner_ref in reference.children:
            self.write_package_reference(ref_element, inner_ref)

        predicates = reference.rule.predicates
        if predicates:
            meta_element = SubElement(ref_element, 'meta')
            for predicate, target in predicates:
                predicate_element = SubElement(meta_element,
                                               predicate)
                predicate_element.text = target


    def _assert_resolved(self):
        """
        Assert that the descriptor has no abstract references.
        """
        logger = get_logger()
        unresolved = [r for r in self.contents 
                       if isinstance(r,PackageReference) 
                         and r.is_abstract()
                      ]
        if unresolved:
            logger.warn(
                'Unresolved references remain in %s' \
                % self.filename
                )
            for reference in unresolved:
                pkgtype = reference.package_type.type_string
                condition = str(reference.rule)
                logger.warn(
                    "No %s %s" % (pkgtype, condition)
                )


    def resolve(self, package_list):
        """Resolve abstract references by searching the given package list.
        """
        refs = []
        child_conditions = []
        for index, ref in self.enumerate_package_refs():
            refs.append((ref, index))

        # first run the packages through base level package references.
        for ghost_package in package_list:
            for ref_index, ref_tuple in enumerate(refs):
                ref, contents_index = ref_tuple
                if ref.rule.condition.evaluate(ghost_package):
                    if ghost_package.role == 'source':
                        new_ref = \
                            PackageReference.from_package(ghost_package)
                        new_ref.rule.predicates = ref.rule.predicates
                        self.contents[contents_index] = new_ref
                        del refs[ref_index]
                        child_condition = get_child_condition(ghost_package)
                        child_conditions.append((child_condition, new_ref))
                        break
                    elif ghost_package.role == 'binary':
                        if ref in [ cs[1] for cs in child_conditions ]:
                            new_ref = ref
                        else:
                            get_abstract_ref = \
                                PackageReference.abstract_from_package
                            new_ref = get_abstract_ref(ghost_package)
                            new_ref.rule.predicates = ref.rule.predicates
                            self.contents[contents_index] = new_ref
                            del refs[ref_index]
                            child_condition = \
                                get_child_condition(ghost_package)
                            child_conditions.append((child_condition,
                                                     new_ref))
                        break

        # run through all the packages again, this time using the
        # child_conditions of new references.
        for ghost_package in package_list:
            for child_condition, ref in child_conditions:
                if child_condition.evaluate(ghost_package):
                    # watch out... this ref could be the same as the
                    # base level reference.
                    if ref.rule.condition.evaluate(ghost_package) and \
                           ghost_package.role == 'source':
                        continue
                    new_child_ref = \
                        PackageReference.from_package(ghost_package)
                    ref.children.append(new_child_ref)
                    break

        self.write()


    def download(self):
        """
        Acquire the packages for this descriptor from known channels
        """
        workspace = current_workspace()
        cache = workspace.cache()
        channels = workspace.channels()
        for ref in self.iter_full_package_refs():
            if ref.blob_id and ref.blob_id not in cache:
                try:
                    base_uri, filename = \
                        channels.find_by_blob_id(ref.blob_id)
                except KeyError:
                    raise SemanticError, \
                        "could not find %s in any channel" % (ref.blob_id,)
                cache.import_file(base_uri, filename, ref.blob_id)
                package = ref.load(cache)
                if hasattr(package, 'extra_file'):
                    for blob_id, filename in package.extra_file:
                        cache.import_file(base_uri, filename, blob_id)


    def iter_package_refs(self):
        '''Yield all base package references in order.'''
        for dummy, ref in self.enumerate_package_refs():
            yield ref


    def iter_full_package_refs(self):
        '''Yield all base and child package references.

        The search is pre-order depth first.
        '''
        for ref in self.iter_package_refs():
            yield ref
            for child_ref in ref.children:
                yield child_ref

    def enumerate_package_refs(self):
        '''Yield all index, package_reference pairs in self.contents.'''
        for index, ref in enumerate(self.contents):
            if isinstance(ref, PackageReference):
                yield index, ref


    # These functions are only used when reading a descriptor in from
    # an xml handle. They roughly represent a recursive descent parser
    # except they operate on a pre-existing xml tree.
    #
    # The entry point is build_component_descriptor

    def build_meta(self, meta_element):
        '''Return a list of tuples (predicate, object) for a "meta" tag.'''
        return [ (e.tag, e.text) for e in meta_element ]

    def is_package_ref(self, rule_element):
        '''Does this element represent a single package?

        Returns true for elements representing both concrete and abstract
        references.
        '''
        return rule_element.tag in ('deb', 'dsc', 'rpm', 'srpm')

    def build_package_ref(self, ref_element):
        '''Return a package_ref given an element.

        This function should only be applied to elements which pass the
        is_package_ref test.
        '''
        and_condition = AndCondition([])

        blob_id = None
        if 'ref' in ref_element.attrib:
            blob_id = ref_element.attrib['ref']
            blob_id_condition = FieldMatchCondition('blob-id', blob_id)
            and_condition.conditions.append(blob_id_condition)

        package_type = get_package_type(format = ref_element.tag)
        type_condition = FieldMatchCondition('type',
                                             package_type.type_string)

        predicates = []
        inner_refs = []
        if ref_element.text and ref_element.text.strip():
            target = ref_element.text.strip()
            name_condition = FieldMatchCondition('name', target)
            and_condition.conditions.append(name_condition)
        else:
            for element in ref_element:
                if element.tag == 'meta':
                    predicates.extend(self.build_meta(element))
                elif self.is_package_ref(element):
                    inner_ref = self.build_package_ref(element)
                    inner_refs.append(inner_ref)
                else:
                    target = element.text.strip()
                    inner_condition = FieldMatchCondition(element.tag,
                                                          target)
                    and_condition.conditions.append(inner_condition)
        and_condition.conditions.append(type_condition)
        rule = Rule(and_condition, predicates)
        ref = PackageReference(package_type, blob_id, rule)
        ref.children = inner_refs
        return ref

    def normalize_text(self, element, strip):
        '''Read a text string from an xml element.

        Null values are converted to the empty string.

        strip is a boolean indicating if whitespace should be stripped
        from the ends of the string.
        '''
        value = None
        if element is not None:
            value = element.text
            if strip:
                value = value.strip()
        if not value:
            value = ''
        return value

    def read_field(self, root, name, strip = True):
        '''Return the text of the first element with the given name.

        Search is limited to direct descendants of the root.

        See normalize_text for strip description.
        '''
        element = root.find(name)
        return self.normalize_text(element, strip)

    def read_multifield(self, root, name, strip = True):
        '''Return the text of all elements with given name in the root.

        Search is limited to direct descendants of the root.

        See normalize_text for strip description.
        '''
        elements = root.findall(name)
        value = []
        for element in elements:
            value.append(self.normalize_text(element, strip))
        return value

    def build_component_descriptor(self, component_element):
        '''Build up the state of this descriptor from the given element.'''
        contents_element = component_element.find('contents')
        if contents_element:
            for element in contents_element:
                if self.is_package_ref(element):
                    ref = self.build_package_ref(element)
                    self.contents.append(ref)
                elif element.tag == 'component':
                    ref = ComponentReference(element.text.strip())
                    self.contents.append(ref)

        meta_element = component_element.find('meta')
        if meta_element:
            self.meta.extend(self.build_meta(meta_element))

        self.id = self.read_field(component_element, 'id')
        self.name = self.read_field(component_element, 'name')
        self.description = self.read_field(component_element, 'description',
                                           False)
        self.requires = self.read_multifield(component_element, 'requires')
        self.provides = self.read_multifield(component_element, 'provides')


class Component(object):
    """Represents a logical PDK component.

    Do not mutate the fields of Component objects. They are meant to
    be used as hash 
    """
    __slots__ = ('ref', 'type',
                 'id', 'name', 'description', 'requires', 'provides',
                 'packages', 'direct_packages',
                 'components', 'direct_components', 'meta', 'rules')
    identity_fields = ('ref', 'type',
                       'id', 'name', 'description', 'requires', 'provides',
                       'direct_packages',
                       'direct_components', 'meta')

    def __init__(self, ref):
        self.ref = ref
        self.type = 'component'

        self.id = ''
        self.name = ''
        self.description = ''
        self.requires = []
        self.provides = []

        self.packages = []
        self.components = []
        self.direct_packages = []
        self.direct_components = []
        self.meta = ComponentMeta()
        self.rules = []

    def _get_values(self):
        '''Return an immutable value representing the full identity.'''
        values = ['component']
        for field in self.identity_fields:
            value = getattr(self, field)
            if isinstance(value, list):
                value = tuple(value)
        return tuple(values)

    def __cmp__(self, other):
        return cmp(self._get_values(), other._get_values())

    def __hash__(self):
        return hash(self._get_values())


class ComponentMeta(object):
    """Represents overridable component metadata.

    This object behaves like a dict of dicts of strings with limited
    write capabilities.

    Use the update method to add/override existing data. Using the update
    method to copy data directly from one object to another should result in
    a proper shallow copy, at least where the two first two levels of dicts
    are concerned.
    """
    def __init__(self):
        self.data = {}

    def update(self, new_items):
        """Copy/override new_items into current data"""
        for key in new_items:
            if key not in self.data:
                self.data[key] = {}
            self.data[key].update(new_items[key])

    def __getitem__(self, index):
        """Retrieve a data item."""
        return self.data[index]

    def __iter__(self):
        """Return an iterator. Imitates iter(dict)."""
        return iter(self.data)

    def __nonzero__(self):
        """Does this object contain any data? Imitates bool(dict)."""
        return bool(self.data)

    def __repr__(self):
        """Return a string represntation of the underlying dict."""
        return repr(self.data)


def get_deb_child_condition_data(package):
    """Get child condition data for a deb."""
    return [ ('name', package.sp_name),
             ('version', package.sp_version),
             ('type', 'dsc') ]

def get_dsc_child_condition_data(package):
    """Get child condition data for a dsc."""
    return [ ('sp_name', package.name),
             ('sp_version', package.version.full_version),
             ('type', 'deb') ]

def get_rpm_child_condition_data(package):
    """Get child condition data for an rpm."""
    return [ ('filename', package.source_rpm),
             ('type', 'srpm') ]

def get_srpm_child_condition_data(package):
    """Get child condition data for an srpm."""
    return [ ('sourcerpm', package.filename),
             ('type', 'rpm') ]

def get_general_condition_data(package):
    """Get condition data for any package."""
    condition_data = [ ('blob-id', package.blob_id),
                       ('name', package.name),
                       ('version', package.version.full_version) ]
    if package.role == 'binary':
        condition_data.append(('arch', package.arch))
    condition_data.append(('type', package.type))
    return condition_data

def get_abstract_condition_data(full_condition_data):
    """Remove conditions which are used only for concrete references."""
    return [ (k, v) for k, v in full_condition_data
             if k not in ('arch', 'blob-id') ]

def get_child_condition(package):
    """Get child condition data for any package."""
    condition_fn = get_child_condition_fn(package)
    child_part = build_and_condition(condition_fn(package))
    if package.role == 'source':
        return child_part
    else:
        parent_data = get_general_condition_data(package)
        parent_data = get_abstract_condition_data(parent_data)
        parent_part = build_and_condition(parent_data)
        return OrCondition([child_part, parent_part])

child_condition_fn_map = {
    'deb': get_deb_child_condition_data,
    'dsc': get_dsc_child_condition_data,
    'rpm': get_rpm_child_condition_data,
    'srpm': get_srpm_child_condition_data }
def get_child_condition_fn(package):
    """Determine which child condition function to use on a package."""
    return child_condition_fn_map[package.type]

def build_and_condition(condition_data):
    """Build an 'and' condition from a list of tuples."""
    and_condition = AndCondition([])
    conditions = and_condition.conditions
    for name, value in condition_data:
        conditions.append(FieldMatchCondition(name, value))
    return and_condition


class PackageReference(object):
    '''Represents a concrete package reference.'''
    def __init__(self, package_type, blob_id, rule):
        self.package_type = package_type
        self.blob_id = blob_id
        self.rule = rule
        self.children = []

    def abstract_from_package(package):
        '''Instantiate an abstract reference for the given package.'''
        concrete_condition_data = get_general_condition_data(package)
        abstract_condition_data = \
            get_abstract_condition_data(concrete_condition_data)
        abstract_condition = build_and_condition(abstract_condition_data)

        rule = Rule(abstract_condition, [])

        return PackageReference(package.package_type, None, rule)
    abstract_from_package = staticmethod(abstract_from_package)

    def from_package(package):
        '''Instantiate a reference for the given package.'''
        condition_data = get_general_condition_data(package)
        condition = build_and_condition(condition_data)
        rule = Rule(condition, [])

        return PackageReference(package.package_type, package.blob_id, rule)

    from_package = staticmethod(from_package)

    def verify(self, cache):
        '''Check if the referred to package meets the rule criteria.'''
        if self.blob_id:
            return self.rule.condition.evaluate(self.load(cache))
        else:
            return True

    def load(self, cache):
        '''Load the package associated with this ref.'''
        return cache.load_package(self.blob_id,
                                  self.package_type.type_string)

    def is_abstract(self):
        '''Return true if this package reference is abstact.'''
        return not (bool(self.blob_id) or bool(self.children))

class ComponentReference(object):
    '''Represents a component reference.

    Use self.load() as a shortcut to the component descriptor.
    '''
    def __init__(self, filename):
        self.filename = filename

    def load(self):
        '''Instantiate the ComponentDescriptor object for this reference.'''
        return ComponentDescriptor(self.filename)


# vim:ai:et:sts=4:sw=4:tw=0:
