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
import optparse
from sets import Set
from itertools import chain
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
from pdk.semdiff import print_report, print_bar_separated, print_man, \
     iter_diffs, iter_diffs_meta

def dumpmeta(component_refs):
    """Print all component metadata to standard out."""
    cache = current_workspace().cache
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


def run_resolve(raw_args, assert_resolved, abstract_constraint):
    '''Take care of details of running descriptor.resolve.

    raw_args - passed from command handlers
    do_assert - warn if any references are not resolved
    show_report - show a human readable report of what was done
    dry_run - do not save the component after we are finished
    '''
    parser = optparse.OptionParser()
    parser.add_option(
                         "-R"
                         , "--no-report"
                         , action="store_false"
                         , dest="show_report"
                         , default=True
                         , help="Don't bother showing the report."
                     )
    parser.add_option(
                         "-n"
                         , "--dry-run"
                         , action="store_false"
                         , dest="save_component_changes"
                         , default=True
                         , help="Don't save changes after processing."
                     )
    parser.add_option(
                         "-m"
                         , "--machine-readable"
                         , action="store_true"
                         , dest="machine_readable"
                         , default=False
                         , help="Make the output machine readable."
                     )
    opts, args = parser.parse_args(args = raw_args)

    if len(args) < 1:
        raise CommandLineError, 'component descriptor required'
    workspace = current_workspace()
    component_name = workspace.reorient_filename(args[0])
    os.chdir(workspace.location)
    descriptor = ComponentDescriptor(component_name)
    channel_names = args[1:]
    package_list = list(workspace.world.iter_packages(channel_names))
    descriptor.resolve(package_list, abstract_constraint)
    descriptor.setify_child_references()

    if assert_resolved:
        descriptor._assert_resolved()

    if opts.show_report:
        if opts.machine_readable:
            printer = print_bar_separated
        else:
            printer = print_man

        descriptor.diff_self(workspace, printer)

    if opts.save_component_changes:
        descriptor.write()

def resolve(args):
    """resolve resolves abstract package references

    *This needs a detailed usage message*

    If the command succeeds, the component will be modified in place.
    Abstract references will be populated with concrete references.

    The command takes a single component descriptor followed by zero
    or more channel names.

    If no channel names are given, resolve uses all channels to
    resolve references.

    A warning is given if any unresolved references remain.
    """
    run_resolve(args, True, True)

def upgrade(args):
    """upgrade upgrades concrete package references by package version

    *This needs a detailed usage message*

    If the command succeeds, the component will be modified in place.

    The command takes a single component descriptor followed by zero
    or more channel names.

    If no channel names are given, resolve uses all channels to
    resolve references.
    """
    run_resolve(args, False, False)

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

def semdiff(argv):
    """Return bar separated lines representing meaningful component changes.

    Diff works against version control, two arbitrary components, or a
    component and a set of channels.

    Usage: pdk semdiff [-m] [-c channel]* component [component]

    Note: When comparing against version control, only the named
    component is retrieved from version control. Sub components are
    found in the work area.

    -c can be specified multiple times to compare against a set of
     channels.

    -m makes the output machine readable.
    """
    workspace = current_workspace()
    cat = workspace.vc.cat
    cache = workspace.cache
    parser = optparse.OptionParser()
    parser.add_option(
                         "-c"
                         , "--channel"
                         , action="append"
                         , dest="channels"
                         , type="string"
                         , help="A channel name."
                     )

    parser.add_option(
                         "-m"
                         , "--machine-readable"
                         , action="store_true"
                         , dest="machine_readable"
                         , default=False
                         , help="Make the output machine readable."
                     )

    opts, args = parser.parse_args(args=argv)

    if opts.machine_readable:
        printer = print_bar_separated
    else:
        printer = print_man

    if opts.channels:
        ref = args[0]
        desc = ComponentDescriptor(args[0])
        component = desc.load(cache)
        old_package_list = component.direct_packages
        world = workspace.world
        new_package_list = list(world.iter_packages(opts.channels))
        old_meta = {}
        new_meta = {}
    elif len(args) == 1:
        ref = args[0]
        # Get old
        old_desc = ComponentDescriptor(ref, cat(ref))
        old_component = old_desc.load(cache)
        old_package_list = old_component.direct_packages
        old_meta = old_component.meta
        # Get new
        new_desc = ComponentDescriptor(ref)
        new_component = new_desc.load(cache)
        new_package_list = new_component.direct_packages
        new_meta = new_component.meta
    elif len(args) == 2:
        ref = args[1]
        # get old
        old_desc = ComponentDescriptor(args[0])
        old_component = old_desc.load(cache)
        old_package_list = old_component.direct_packages
        old_meta = old_component.meta
        # Get new
        new_desc = ComponentDescriptor(args[1])
        new_component = new_desc.load(cache)
        new_package_list = new_component.direct_packages
        new_meta = new_component.meta
    else:
        raise CommandLineError("Argument list is invalid")

    diffs = iter_diffs(old_package_list, new_package_list)
    diffs_meta = iter_diffs_meta(old_meta, new_meta)
    data = chain(diffs, diffs_meta)
    printer(ref, data)

class ComponentDescriptor(object):
    """Represents a component descriptor object.

    This class is for looking at a convenient abstraction of the raw
    contents of a descriptor.

    Use the meta and contents properties to change the descriptor.

    Use load(cache) to instantiate trees of Component objects.
    """
    def __init__(self, filename, handle = None):
        self.filename = filename
        if filename is None:
            tree = ElementTree(element = Element('component'))
        elif handle:
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
                message = 'Component descriptor "%s" does not exist.' \
                          % filename
                raise InputError(message)

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
                                      % concrete_ref.blob_id, package
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

        for name, value in reference.fields:
            condition_element = SubElement(ref_element, name)
            condition_element.text = value

        predicates = reference.predicates
        if predicates:
            meta_element = SubElement(ref_element, 'meta')
            for predicate, target in predicates:
                predicate_element = SubElement(meta_element,
                                               predicate)
                predicate_element.text = target

        for inner_ref in reference.children:
            self.write_package_reference(ref_element, inner_ref)


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


    def setify_child_references(self):
        """Remove duplicate and sort child references from the component.

        The same child ocurring three times under three different
        parents is not considered a duplicate.
        """

        for parent_ref in self.iter_package_refs():
            child_set = Set(parent_ref.children)
            new_child_list = list(child_set)
            new_child_list.sort()
            parent_ref.children = new_child_list

    def _get_parent_matches(self, package_list, abstract_constraint):
        '''Creates "match tuples" associating packages with matched refs.

        tuple looks like: (package, ref)
        '''
        match_information = []

        # first run the packages through base level package references.
        for ghost_package in package_list:
            for ref in self.iter_package_refs(abstract_constraint):
                if ref.rule.condition.evaluate(ghost_package):
                    match_information.append((ghost_package, ref))
        return match_information

    def _resolve_conflicting_matches(self, parent_matches):
        '''Apply policy when the same ref matches more than one package.

        Current policy is roughly the same as debian. Use the "newest"
        package.
        '''
        def _cmp_matches(a, b):
            '''Compare two match tuples.'''
            return -cmp(a[0].version, b[0].version)

        parent_matches.sort(_cmp_matches)
        last_ref = None
        child_conditions = []
        for this_match in parent_matches:
            ghost_package, ref = this_match
            if last_ref is not None and ref == last_ref:
                # skip this record as a newer one has already been found.
                continue
            child_condition = get_child_condition(ghost_package, ref)
            child_conditions.append((child_condition, this_match[1]))
            last_ref = ref
        return child_conditions

    def resolve(self, package_list, abstract_constraint):
        """Resolve abstract references by searching the given package list.

        abstract_constraint is passed to self.iter_package_refs().
        """
        parent_matches = self._get_parent_matches(package_list,
                                                  abstract_constraint)
        child_conditions = self._resolve_conflicting_matches(parent_matches)

        # run through the new list of matched refs and clear the child
        # lists.
        for dummy, ref in child_conditions:
            ref.children = []

        # run through all the packages again, this time using the
        # child_conditions of new references.
        for ghost_package in package_list:
            for child_condition, ref in child_conditions:
                if child_condition.evaluate(ghost_package):
                    new_child_ref = \
                        PackageReference.from_package(ghost_package)
                    expected_filename = ghost_package.filename
                    found_filename = ghost_package.found_filename
                    if expected_filename != found_filename:
                        predicate = ('filename', found_filename)
                        new_child_ref.predicates.append(predicate)
                    ref.children.append(new_child_ref)

    def download(self):
        """
        Acquire the packages for this descriptor from known channels
        """
        workspace = current_workspace()
        cache = workspace.cache
        blob_ids = [ r.blob_id for r in self.iter_full_package_refs()
                     if r.blob_id and r.blob_id not in cache ]
        workspace.acquire(blob_ids)

        # now that we have all downloads done, pass through again looking
        # for extra files
        extra_blob_ids = []
        for ref in self.iter_full_package_refs():
            if not ref.blob_id:
                continue
            package = ref.load(cache)
            if hasattr(package, 'extra_file'):
                for extra_blob_id, dummy in package.extra_file:
                    extra_blob_ids.append(extra_blob_id)
        workspace.acquire(extra_blob_ids)
        return

    def iter_package_refs(self, abstract_constraint = None):
        '''Yield all base package references in order.

        If abstract_constraint is provided (and not None) then that
        value will be a constraint on the is_abstract() method of the
        refs. If a reference does no match the constraint, it is skipped.
        '''
        for dummy, ref in self.enumerate_package_refs():
            if abstract_constraint is not None:
                if bool(abstract_constraint) != bool(ref.is_abstract()):
                    continue
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
        return rule_element.tag in ('deb', 'udeb', 'dsc', 'rpm', 'srpm')

    def build_package_ref(self, ref_element):
        '''Return a package_ref given an element.

        This function should only be applied to elements which pass the
        is_package_ref test.
        '''
        fields = []

        blob_id = None
        if 'ref' in ref_element.attrib:
            blob_id = ref_element.attrib['ref']

        package_type = get_package_type(format = ref_element.tag)

        predicates = []
        inner_refs = []
        if ref_element.text and ref_element.text.strip():
            target = ref_element.text.strip()
            fields.append(('name', target))
        else:
            for element in ref_element:
                if element.tag == 'meta':
                    predicates.extend(self.build_meta(element))
                elif self.is_package_ref(element):
                    inner_ref = self.build_package_ref(element)
                    inner_refs.append(inner_ref)
                else:
                    target = element.text.strip()
                    fields.append((element.tag, target))
        ref = PackageReference(package_type, blob_id, fields, predicates)
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

    def diff_self(self, workspace, printer):
        '''Run semdiff between self and its previously written state.'''
        orig_descriptor = ComponentDescriptor(self.filename)
        c_cache = workspace.world.get_backed_cache(workspace.cache)
        print_report(orig_descriptor.load(c_cache), self.load(c_cache),
                     printer)


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
             [ 'or',
               ('type', 'deb'),
               ('type', 'udeb') ] ]

def get_rpm_child_condition_data(package):
    """Get child condition data for an rpm."""
    return [ ('filename', package.source_rpm),
             ('type', 'srpm') ]

def get_srpm_child_condition_data(package):
    """Get child condition data for an srpm."""
    return [ ('source-rpm', package.filename),
             ('type', 'rpm') ]

def get_general_fields(package):
    """Get condition data for any package."""
    fields = [ ('name', package.name),
               ('version', package.version.full_version) ]
    if package.role == 'binary':
        fields.append(('arch', package.arch))
    return fields

def get_child_condition(package, ref):
    """Get child condition data for any package."""
    condition_fn = get_child_condition_fn(package)
    child_condition = build_condition(condition_fn(package))
    # Always pin the the child's parent to a single version.
    # Someday we may need a more sophisticated mechanism for RPM.
    # I'm just not sure. -dt
    parent_version = package.version.full_version
    parent_condition = build_condition(ref.fields +
                                       [('version', parent_version)])
    return OrCondition([child_condition, parent_condition])

child_condition_fn_map = {
    'deb': get_deb_child_condition_data,
    'udeb': get_deb_child_condition_data,
    'dsc': get_dsc_child_condition_data,
    'rpm': get_rpm_child_condition_data,
    'srpm': get_srpm_child_condition_data }
def get_child_condition_fn(package):
    """Determine which child condition function to use on a package."""
    return child_condition_fn_map[package.type]

condition_type_map = {
    'and': AndCondition,
    'or': OrCondition
    }
def build_condition(raw_condition_data):
    """Build an 'and' condition from a list of tuples."""
    if isinstance(raw_condition_data[0], basestring):
        condition_type = raw_condition_data[0]
        condition_data = raw_condition_data[1:]
    else:
        condition_type = 'and'
        condition_data = raw_condition_data
    condition = condition_type_map[condition_type]([])
    for item in condition_data:
        if isinstance(item, tuple):
            name, value = item
            condition.conditions.append(FieldMatchCondition(name, value))
        else:
            condition.conditions.append(build_condition(item))
    return condition


class PackageReference(object):
    '''Represents a concrete package reference.'''
    def __init__(self, package_type, blob_id, fields, predicates):
        self.package_type = package_type
        self.blob_id = blob_id
        self.fields = fields
        self.predicates = predicates
        self.children = []

    def from_package(package):
        '''Instantiate a reference for the given package.'''
        fields = get_general_fields(package)
        return PackageReference(package.package_type, package.blob_id,
                                fields, [])
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

    def __contains__(self, field):
        return field in [ t[0] for t in self.fields ]

    def __getitem__(self, field):
        fields_dict = dict(self.fields)
        return fields_dict[field]

    def get_name(self):
        '''Get the expected name of the referenced package(s).

        Returns a blank string if no name was given.
        '''
        return ('name' in self and self['name']) or ''
    name = property(get_name)

    def get_version(self):
        '''Get the exected version of the referenced package(s).

        Returns a blank string if no version was given.
        '''
        return ('version' in self and self['version']) or ''
    version = property(get_version)

    def get_arch(self):
        '''Get the exected arch of the referenced package(s).

        Returns a blank string if no arch was given.
        '''
        return ('arch' in self and self['arch']) or ''
    arch = property(get_arch)

    def get_rule(self):
        '''Construct a rule object for this reference.'''
        all_fields = ['and']
        if self.blob_id:
            all_fields.append(('blob-id', self.blob_id))

        all_fields.extend(self.fields)
        all_fields.append(('type', self.package_type.type_string))
        return Rule(build_condition(all_fields), self.predicates)
    rule = property(get_rule)

    def __identity_tuple(self):
        '''Return a tuple to help cmp and hash handle this object.'''
        return self.package_type.format_string, \
               self.package_type.role_string, \
               self.package_type.type_string, \
               self.name, self.version, self.arch, self.blob_id, \
               tuple(self.fields), tuple(self.predicates), \
               tuple(self.children)

    def __cmp__(self, other):
        return cmp(self.__identity_tuple(), other.__identity_tuple())

    def __hash__(self):
        return hash(self.__identity_tuple())

class ComponentReference(object):
    '''Represents a component reference.

    Use self.load() as a shortcut to the component descriptor.
    '''
    def __init__(self, filename):
        self.filename = filename

    def load(self):
        '''Instantiate the ComponentDescriptor object for this reference.'''
        return ComponentDescriptor(self.filename)

class Metafilter(object):
    '''Delegates attribute and item lookups through metadata.

    Wraps other objects and provides __getattr__ and __getitem__.

    If the provided metadata has data for the given key or attribute, the
    metadata value is provided. Otherwise, the provided object handles
    the key or attribute normally.
    '''
    def __init__(self, meta, filteree):
        self.__meta = meta
        self.__filteree = filteree

    def __getattr__(self, name):
        return self.__try_meta(name) or getattr(self.__filteree, name)

    def __getitem__(self, name):
        return self.__try_meta(name) or self.__filteree[name]

    def __try_meta(self, name):
        '''Try to find the named attribute/item in metadata.

        Returns the found value on success, None on failure.
        '''
        if self.__filteree in self.__meta:
            meta_dict = self.__meta[self.__filteree]
            if name in meta_dict:
                return meta_dict[name]
        return None

    def __repr__(self):
        return '<Metafilter (%s)>' % self.__filteree

# vim:ai:et:sts=4:sw=4:tw=0:
