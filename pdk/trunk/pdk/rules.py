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

class FieldMatchCondition(object):
    '''Check that the provided object has a particular attribute and value.
    '''
    def __init__(self, domain, field_name, target):
        self.domain = domain
        self.field_name = field_name
        self.target = target

    def evaluate(self, candidate):
        key = (self.domain, self.field_name)

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
            return hasattr(candidate, self.field_name) and \
                   getattr(candidate, self.field_name) == self.target

    def __repr__(self):
        return 'cond fm (%s, %s, %s)' % (self.domain, self.field_name,
                                         self.target)

    def __str__(self):
        tag = string_domain(self.domain, self.field_name)
        return "[%s] is '%s'" % (tag, self.target)

class AndCondition(object):
    '''Check that the provided object meets all the provided conditions.'''
    def __init__(self, conditions):
        self.conditions = conditions

    def evaluate(self, candidate):
        for condition in self.conditions:
            if not condition.evaluate(candidate):
                return False
        return True

    def __repr__(self):
        return 'cond and %s' % self.conditions

    def __str__(self):
        child_strings = [str(x) for x in self.conditions]
        return ' AND '.join(child_strings)


class OrCondition(object):
    '''Check that the provided object meets one of the conditions.'''
    def __init__(self, conditions):
        self.conditions = conditions

    def evaluate(self, candidate):
        for condition in self.conditions:
            if condition.evaluate(candidate):
                return True
        return False

    def __repr__(self):
        return 'cond or %s' % self.conditions

    def __str__(self):
        child_strings = [str(x) for x in self.conditions]
        return ' OR '.join(child_strings)


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

    def fire(self, entity, entities):
        '''If the condition matches, yield a sequence of 3-tuples.
        The first element of the tuple will be the provided
        object. The second and third correspond to the fields of the
        2-tuple.
        '''
        if self.condition.evaluate(entity):
            self.success_count += 1
            self.action.execute(entity, entities)

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

    def fire(self, entity, entities):
        '''Fire all rules, passing the given object to each.
        Chains all the yielded statements into a single iterator.
        '''
        for rule in self.rules:
            rule.fire(entity, entities)

    def __str__(self):
        return " AND ".join( [ str(r) for r in self.rules ])

class CompositeAction(object):
    '''Composite a series of actions.'''
    def __init__(self, actions):
        self.actions = actions

    def execute(self, entity, entities):
        '''Execute all the actions in sequence.'''
        for action in self.actions:
            action.execute(entity, entities)

    def __str__(self):
        return str(self.actions)
