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

'''rules.py

Handle rule and condition processing.

Structure:

Rule:
    condition object
        has an evaluate method that returns a boolean indicating whether
        the provided object matches the encapsulated condition.
    meta_condition object
        accepts the rule itself and evalutes a condition usually related
        to state of the rule itself.
    predicates
        A list of 2-tuples.

    fire(object):
        see Rule class

    evaluate_meta_condition
        see Rule class
'''

from pdk.util import string_domain

def make_comparable(cls):
    '''Make a condition class comparable using its get_identity function'''
    def __cmp__(self, other):
        return cmp(self.__class__, other.__class__) or \
               cmp(self.get_identity(), other.get_identity())

    def __hash__(self):
        return hash(self.get_identity())

    cls.__cmp__ = __cmp__
    cls.__hash__ = __hash__

class FieldMatchCondition(object):
    '''Check that the provided object has a particular attribute and value.
    '''
    def __init__(self, domain, predicate, target):
        self.domain = domain
        self.predicate = predicate
        self.target = target

    def evaluate(self, candidate):
        key = (self.domain, self.predicate)

        # Unfortunately components are special cases.
        #
        # At some point in the future they may inherit from the Entity
        # class. Then we can rid ourselves of this oddball and
        # unfortunate exception handler.
        try:
            if key in candidate:
                return candidate[key] == self.target
        except TypeError, e:
            if 'iterable' in str(e):
                pass
            else:
                raise

        # The pdk domain is special, we can evalute it against raw
        # entity attributes.
        #
        # Maybe someday we can rid ourselves of this special case.
        if self.domain == 'pdk':
            return hasattr(candidate, self.predicate) and \
                   getattr(candidate, self.predicate) == self.target

    def __str__(self):
        tag = string_domain(self.domain, self.predicate)
        return "[%s] is '%s'" % (tag, self.target)

    __repr__ = __str__

    def get_identity(self):
        '''Return the comparable identity for this object.'''
        return (self.domain, self.predicate, self.target)

make_comparable(FieldMatchCondition)

class RelationCondition(object):
    '''A condition designed to compare versions.

    condition - A function taking to parameters and returning a boolean.
    domain, predicate - The domain and predicate to be matched.
    target    - The second value passed to the condition function.

    When evaluating, the candidate field will be passed as the first
    argument to the condition function.
    '''
    def __init__(self, condition, domain, predicate, target):
        self.condition = condition
        self.domain = domain
        self.predicate = predicate
        self.target = target

    def evaluate(self, candidate):
        field = (self.domain, self.predicate)
        if field in candidate:
            return self.condition(candidate[field], self.target)
        else:
            return False

    def __str__(self):
        tag = string_domain(self.domain, self.predicate)
        return "[%s] is %s '%s'" % (tag, self.condition.__name__,
                                    self.target)

    __repr__ = __str__

    def get_identity(self):
        '''Return the comparable identity for this object.'''
        return (self.condition, self.domain, self.predicate, self.target)

make_comparable(RelationCondition)

class AndCondition(object):
    '''Check that the provided object meets all the provided conditions.'''
    def __init__(self, conditions):
        self.conditions = conditions

    def evaluate(self, candidate):
        for condition in self.conditions:
            if not condition.evaluate(candidate):
                return False
        return True

    def __str__(self):
        child_strings = [str(x) for x in self.conditions]
        return '( %s )' % ' AND '.join(child_strings)

    __repr__ = __str__

    def get_identity(self):
        '''Return the comparable identity for this object.'''
        return tuple(self.conditions)

make_comparable(AndCondition)

class OrCondition(object):
    '''Check that the provided object meets one of the conditions.'''
    def __init__(self, conditions):
        self.conditions = conditions

    def evaluate(self, candidate):
        for condition in self.conditions:
            if condition.evaluate(candidate):
                return True
        return False

    def __str__(self):
        child_strings = [str(x) for x in self.conditions]
        return '( %s )' % ' OR '.join(child_strings)

    __repr__ = __str__

    def get_identity(self):
        '''Return the comparable identity for this object.'''
        return tuple(self.conditions)

make_comparable(OrCondition)

class NotCondition(object):
    '''Invert the value of evaluating the contained condition.'''
    def __init__(self, condition):
        self.condition = condition

    def evaluate(self, candidate):
        return not self.condition.evaluate(candidate)

    def __str__(self):
        return '*not*( %s )' % self.condition

    __repr__ = __str__

    def get_identity(self):
        '''Return the comparable identity for this object.'''
        return self.condition

make_comparable(NotCondition)

class StarCondition(object):
    '''Make the contained condition evaluate against the complement.

    The contained condition will be run against the candidate complement if
    it is present.

    If the candidate has no complement attibute, the condition
    automatically fails.

    Rule actions are applied to the candidate itself, not the complement.
    '''
    def __init__(self, condition):
        self.condition = condition

    def evaluate(self, candidate):
        if not hasattr(candidate, 'complement'):
            return False
        for comp in candidate.complement:
            if self.condition.evaluate(comp):
                return True
        return False

    def __str__(self):
        return '*star*( %s )' % self.condition

    __repr__ = __str__

    def get_identity(self):
        '''Return the comparable identity for this object.'''
        return self.condition

make_comparable(StarCondition)

class OneMatchMetacondition(object):
    '''Check that the success_count attribute is 1.'''
    def evaluate(self, rule):
        return rule.success_count == 1

class TrueCondition(object):
    '''Always evaluate to true.'''
    def evaluate(self, dummy):
        return True

    def __str__(self):
        return 'cond true!'

class Rule(object):
    '''A rule which can be applied to entities or other objects.

    See module docstring.
    '''
    def __init__(self, condition, action,
                 metacondition = OneMatchMetacondition()):
        self.condition = condition
        self.action = action
        self.metacondition = metacondition
        self.success_count = 0

    def evaluate_metacondition(self):
        '''Evalute the metacondition with self.'''
        return self.metacondition.evaluate(self)

    def fire(self, entity):
        '''If the condition matches, yield a sequence of 3-tuples.
        The first element of the tuple will be the provided
        object. The second and third correspond to the fields of the
        2-tuple.
        '''
        if self.condition.evaluate(entity):
            self.success_count += 1
            self.action.execute(entity)

    def __str__(self):
        text = "where " + str(self.condition)
        text += " action: " + str(self.action)
        return text


class RuleSystem(object):
    '''Composite a number of rule objects.'''
    def __init__(self, rules):
        self.rules = rules

    def evaluate_metacondition(self):
        '''Evaluate all meta conditions. Stop on the first failure.'''
        for rule in self.rules:
            if not rule.evaluate_metacondition():
                return False
        return True

    def fire(self, entity):
        '''Fire all rules, passing the given object to each.
        Chains all the yielded statements into a single iterator.
        '''
        for rule in self.rules:
            rule.fire(entity)

    def __str__(self):
        return " AND ".join( [ str(r) for r in self.rules ])

class CompositeAction(object):
    '''Composite a series of actions.'''
    def __init__(self, actions):
        self.actions = actions

    def execute(self, entity):
        '''Execute all the actions in sequence.'''
        for action in self.actions:
            action.execute(entity)

    def __str__(self):
        return str(self.actions)

# some abbreviations.

fmc = FieldMatchCondition
rc = RelationCondition
ac = AndCondition
oc = OrCondition
tc = TrueCondition
starc = StarCondition
notc = NotCondition
