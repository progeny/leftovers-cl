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
from pdk.util import path, write_pretty_xml, parse_xml
import pdk.cache 
from pdk.channels import ChannelData
from cElementTree import ElementTree, Element, SubElement
from pdk.rules import Rule, CompositeRule, AndCondition, FieldMatchCondition
from pdk.package import UnknownPackageTypeError, get_package_type
from pdk.exceptions import CommandLineError, InputError, SemanticError
from xml.parsers.expat import ExpatError
from pdk.log import get_logger


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
    component_name = args[0]
    descriptor = ComponentDescriptor(component_name)
    channel_names = args[1:]
    channels = ChannelData.load_cached()
    for channel in channels.get_channels(channel_names):
        descriptor.resolve(channel)

    logger = get_logger()
    for reference in descriptor.contents:
        if isinstance(reference, PackageReference):
            if reference.is_abstract():
                message = 'unresolved references remain in %s' \
                          % component_name
                logger.warn(message)
                break


def download(args):
    """
    Command line entry point to downloading missing packages.
    *This needs a detailed usage message*
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

        local_rules = []
        for ref in self.contents:
            rule = None
            if isinstance(ref, PackageReference):
                if ref.blob_id:
                    package = ref.load(cache)
                    component.packages.append(package)
                    component.direct_packages.append(package)
                    if not ref.verify(cache):
                        message = 'Concrete package does not meet ' \
                                  'expected constraints: %s' \
                                  % ref.blob_id, package.name
                        raise SemanticError(message)
                rule = ref.rule
            elif isinstance(ref, ComponentReference):
                child_descriptor = ref.load()
                child_component = child_descriptor.load(cache)
                component.direct_components.append(child_component)
                component.components.append(child_component)
                component.components.extend(child_component.components)
                component.packages.extend(child_component.packages)
                component.rules.extend(child_component.rules)

            if rule:
                local_rules.append(rule)

        component.rules.extend(local_rules)
        uber_rule = CompositeRule(component.rules)
        for package in component.packages:
            for package, key, value in uber_rule.fire(package):
                component.meta.update({(package.blob_id, package.type):
                                       {key: value}})
        for decendent_component in component.components:
            for found_component, key, value in \
                    uber_rule.fire(decendent_component):
                component.meta.update({(found_component.ref, 'component'):
                                       {key: value}})
        component.meta.update({(self.filename, 'component'):
                               dict(self.meta)})

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
                attributes = {}
                if reference.blob_id:
                    attributes['ref'] = reference.blob_id
                name = reference.package_type.type_string
                ref_element = SubElement(contents_element, name, attributes)

                assert hasattr(reference.rule.condition, 'conditions'), \
                    'Package rules should always be flat AndConditions'
                for condition in reference.rule.condition.conditions:
                    if condition.field_name in ('blob-id', 'type'):
                        continue
                    condition_element = SubElement(ref_element,
                                                   condition.field_name)
                    condition_element.text = condition.target

                predicates = reference.rule.predicates
                if predicates:
                    meta_element = SubElement(ref_element, 'meta')
                    for predicate, target in predicates:
                        predicate_element = SubElement(meta_element,
                                                       predicate)
                        predicate_element.text = target

            elif isinstance(reference, ComponentReference):
                component_element = SubElement(contents_element,
                                               'component')
                component_element.text = reference.filename
        dirname = path(self.filename)['..']()
        if not os.path.exists(dirname):
            os.makedirs(dirname)
        write_pretty_xml(tree, self.filename)


    def resolve(self, channel):
        """Resolve abstract references by searching the given channel."""
        refs = []
        for index, ref in self.enumerate_package_refs():
            refs.append((ref, index))

        for channel_item in channel:
            ghost_package = channel_item[0]
            for ref_index, ref_tuple in enumerate(refs):
                ref, contents_index = ref_tuple
                if ref.rule.condition.evaluate(ghost_package):
                    new_ref = PackageReference.from_package(ghost_package)
                    new_ref.rule.predicates = ref.rule.predicates
                    self.contents[contents_index] = new_ref
                    del refs[ref_index]
                    break
        self.write()


    def download(self):
        """
        Acquire the packages for this descriptor from known channels
        """
        cache = pdk.cache.Cache()
        channels = ChannelData.load_cached()
        for ref in self.iter_package_refs():
            if ref.blob_id and ref.blob_id not in cache:
                base_uri, filename = channels.find_by_blob_id(ref.blob_id)
                cache.import_file(base_uri, filename, ref.blob_id)
                package = ref.load(cache)
                if hasattr(package, 'extra_file'):
                    for blob_id, filename in package.extra_file:
                        cache.import_file(base_uri, filename, blob_id)


    def iter_package_refs(self):
        '''Yield all package references in order.'''
        for dummy, ref in self.enumerate_package_refs():
            yield ref


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
        if ref_element.text and ref_element.text.strip():
            target = ref_element.text.strip()
            name_condition = FieldMatchCondition('name', target)
            and_condition.conditions.append(name_condition)
        else:
            for element in ref_element:
                if element.tag == 'meta':
                    predicates.extend(self.build_meta(element))
                else:
                    target = element.text.strip()
                    inner_condition = FieldMatchCondition(element.tag,
                                                          target)
                    and_condition.conditions.append(inner_condition)
        and_condition.conditions.append(type_condition)
        rule = Rule(and_condition, predicates)
        return PackageReference(package_type, blob_id, rule)

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
    """Represents a logical PDK component."""
    __slots__ = ('ref', 'type',
                 'id', 'name', 'description', 'requires', 'provides',
                 'packages', 'direct_packages',
                 'components', 'direct_components', 'meta', 'rules')

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

class PackageReference(object):
    '''Represents a package reference.'''
    def __init__(self, package_type, blob_id, rule):
        self.package_type = package_type
        self.blob_id = blob_id
        self.rule = rule

    def from_package(package):
        '''Instantiate a reference for the given package.'''
        and_condition = AndCondition([])
        condition_data = [ ('blob-id', package.blob_id),
                           ('name', package.name),
                           ('version', package.version.full_version) ]
        if package.role == 'binary':
            condition_data.append(('arch', package.arch))
        condition_data.append(('type', package.type))
        conditions = and_condition.conditions
        for name, value in condition_data:
            conditions.append(FieldMatchCondition(name, value))
        rule = Rule(and_condition, [])
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
        return not bool(self.blob_id)

class ComponentReference(object):
    '''Represents a component reference.

    Use self.load() as a shortcut to the component descriptor.
    '''
    def __init__(self, filename):
        self.filename = filename

    def load(self):
        '''Instantiate the ComponentDescriptor object for this reference.'''
        return ComponentDescriptor(self.filename)

def do_dumpmeta(component_refs):
    """Print all component metadata to standard out."""
    cache = pdk.cache.Cache()
    for component_ref in component_refs:
        component = ComponentDescriptor(component_ref).load(cache)
        for ref in component.meta:
            meta_dict = component.meta[ref]
            for key, value in meta_dict.items():
                try:
                    name = cache.load_package(*ref).name
                except UnknownPackageTypeError:
                    name = ''
                print '|'.join([ref[0], ref[1], name, key, value])

def do_cachepull(args):
    """Pull needed cache entities from remote sources."""
    from pdk.yaxml import parse_yaxml_file
    component_refs = args
    cache = pdk.cache.Cache()
    sources = parse_yaxml_file('cache-sources.conf.xml')
    for comp_ref in component_refs:
        desc = ComponentDescriptor(comp_ref)
        for ref in desc.iter_package_refs():
            rel_filename  = cache.make_relative_filename(ref.blob_id)
            cache.import_file_from_sources(sources, rel_filename,
                                           ref.blob_id)
            package = ref.load(cache)
            if hasattr(package, 'extra_file'):
                for extra_blob_id, dummy in package.extra_file:
                    rel_extra = cache.make_relative_filename(extra_blob_id)
                    cache.import_file_from_sources(sources, rel_extra,
                                                   extra_blob_id)

# vim:ai:et:sts=4:sw=4:tw=0:
