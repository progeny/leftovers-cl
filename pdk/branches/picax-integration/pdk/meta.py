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

'''Contains utility classes for managing metadata.

The metadata class is ComponentMeta.

Metadata in pdk is essentially "layered" allowing for more information
about a given item to override previous information, regarless of the
source of the information.

Basically this allows components to override information in packages, etc.
'''

class ComponentMeta(object):
    """Represents overridable component metadata.

    Use the add method to add/override existing data.

    Domains are associated with predicates, but do not serve as
    namespace delimiters.

    meta[item] always returns a _ComponentMetaGroup.
    """
    def __init__(self):
        self.data = {}

    def set(self, item, domain, predicate, target):
        """Set a new or override an existing metadata item."""
        self.set_group(item, ((domain, predicate, target),))

    def set_group(self, item, predicates):
        """Set a new or override a number of existing metadata items."""
        group = self.get_group(item)
        group.set_group(predicates)

    def get_group(self, item):
        """Get the group the group associated with the item.

        Create the group if necessary."""
        return self.data.setdefault(item, _ComponentMetaGroup({}))

    def get(self, item, predicate):
        """Get thet data associated with a single item, predicate pair."""
        return self.data[item][predicate]

    def get_domain_predicates(self, item, domain):
        """Get all the predicates associated with the item and domain."""
        return self[item].get_domain_predicates(domain)

    def __getitem__(self, item):
        """Retrieve the whole metadata group for item."""
        return self.data[item]

    def __iter__(self):
        """Return an iterator. Imitates iter(dict)."""
        return iter(self.data)

    def __nonzero__(self):
        """Does this object contain any data? Imitates bool(dict)."""
        return bool(self.data)

    def __repr__(self):
        return repr(self.data)

    def has_predicate(self, item, predicate):
        """Is the item/predicate in this metadata?"""
        return item in self.data and predicate in self.data[item]

class _ComponentMetaGroup(dict):
    """Holds metadata specific to a particular object.

    Use the set and update methods to set/override fields.
    """
#    domains = None
    __slots__ = ('domains',)

    def __new__(cls, item_dict):
        self = dict.__new__(cls, item_dict)
        self.domains = {}
        return self

    def set(self, domain, predicate, target):
        """Set a new or override an existing metadata item."""
        self.set_group(((domain, predicate, target),))

    def set_group(self, predicates):
        """Set a new or override a number of existing metadata items."""
        for domain, predicate, target in predicates:
            self[predicate] = target
            self.domains[predicate] = domain

    def get_domain_predicates(self, domain):
        """Get all the predicates which declare the given domain."""
        for predicate, predicate_domain in self.domains.iteritems():
            if predicate_domain == domain:
                yield predicate

    def as_dict(self):
        """Return a dict representing this whole group.

        Predicates are the keys, and meta item values are the values.

        Domains are ignored.
        """
        return dict(self)
