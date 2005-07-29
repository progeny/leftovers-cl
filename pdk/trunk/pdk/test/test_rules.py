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

from pdk.test.utest_util import Test
from pdk.package import Package

from pdk.rules import FieldMatchCondition, AndCondition, \
     OneMatchMetacondition, TrueCondition, Rule, CompositeRule

class ConditionsAndRulesFixture(Test):
    def set_up(self):
        super(ConditionsAndRulesFixture, self).set_up()
        self.name_condition = FieldMatchCondition('name', 'a')
        self.version_condition = FieldMatchCondition('version', '1')
        self.and_condition = AndCondition([self.name_condition,
                                                 self.version_condition])

        self.a1 = Package({'name': 'a', 'version': '1'}, None)
        self.a2 = Package({'name': 'a', 'version': '2'}, None)
        self.b1 = Package({'name': 'b', 'version': '1'}, None)
        self.b2 = Package({'name': 'b', 'version': '2'}, None)

        self.all_packages = [ self.a1, self.a2, self.b1, self.b2 ]

    def test_field_match(self):
        assert self.name_condition.evaluate(self.a1)
        assert not self.name_condition.evaluate(self.b1)
        assert self.name_condition.evaluate(self.a2)
        assert not self.name_condition.evaluate(self.b2)
        assert self.version_condition.evaluate(self.a1)
        assert not self.version_condition.evaluate(self.a2)
        assert self.version_condition.evaluate(self.b1)
        assert not self.version_condition.evaluate(self.b2)

    def test_and_match(self):
        assert self.and_condition.evaluate(self.a1)
        assert not self.and_condition.evaluate(self.a2)
        assert not self.and_condition.evaluate(self.b1)
        assert not self.and_condition.evaluate(self.b2)

    def test_basic_metaconditions(self):
        assert TrueCondition().evaluate(None)

        class MockRule(object):
            success_count = 0

        rule = MockRule()
        assert not OneMatchMetacondition().evaluate(rule)
        rule.success_count = 1
        assert OneMatchMetacondition().evaluate(rule)

    def test_rule(self):
        predicates = [ ('is', 'blue'), ('has', 'joy') ]
        rule = Rule(self.and_condition, predicates)
        assert not rule.evaluate_metacondition()
        actual = list(rule.fire(self.b2))
        expected = []
        self.assert_equal(expected, actual)
        assert not rule.evaluate_metacondition()
        actual = list(rule.fire(self.a1))
        expected = [ (self.a1, 'is', 'blue'), (self.a1, 'has', 'joy') ]
        self.assert_equal(expected, actual)
        assert rule.evaluate_metacondition()

    def test_composite_statement_iterator(self):
        predicates_a = [ ('is', 'blue'), ('has', 'joy') ]
        rule_a = Rule(self.and_condition, predicates_a)
        predicates_b = [ ('is', 'red'), ('has', 'five') ]
        rule_b = Rule(FieldMatchCondition('name', 'b'), predicates_b)

        composite = CompositeRule([rule_a, rule_b])
        assert not composite.evaluate_metacondition()

        actual = list(composite.fire(self.a1))
        expected = [ (self.a1, 'is', 'blue'), (self.a1, 'has', 'joy') ]
        self.assert_equal(expected, actual)
        assert not composite.evaluate_metacondition()

        actual = list(composite.fire(self.b2))
        expected = [ (self.b2, 'is', 'red'), (self.b2, 'has', 'five') ]
        self.assert_equal(expected, actual)
        assert composite.evaluate_metacondition()
