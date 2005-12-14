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

from operator import ge
from pdk.test.utest_util import Test, MockPackage
from pdk.package import deb
from pdk.meta import Entity

from pdk.rules import FieldMatchCondition, AndCondition, OrCondition, \
     RelationCondition, \
     OneMatchMetacondition, TrueCondition, Rule, RuleSystem, CompositeAction

class ShamAction(object):
    def __init__(self):
        self.calls = []

    def execute(self, entity, entities):
        self.calls.append((entity, entities))

class ConditionsAndRulesFixture(Test):
    def set_up(self):
        super(ConditionsAndRulesFixture, self).set_up()
        self.name_condition = FieldMatchCondition('pdk', 'name', 'a')
        self.version_condition = FieldMatchCondition('pdk', 'version', '1')
        self.and_condition = AndCondition([self.name_condition,
                                           self.version_condition])
        self.or_condition = OrCondition([self.name_condition,
                                         self.version_condition])

        self.a1 = MockPackage('a', '1', deb)
        self.a2 = MockPackage('a', '2', deb)
        self.b1 = MockPackage('b', '1', deb)
        self.b2 = MockPackage('b', '2', deb)

        self.all_packages = [ self.a1, self.a2, self.b1, self.b2 ]

    def test_version_relation(self):
        vrc = RelationCondition(ge, 'pdk', 'version', 3)
        assert vrc.evaluate({('pdk', 'version'): 4})
        assert vrc.evaluate({('pdk', 'version'): 3})
        assert not vrc.evaluate({('pdk', 'version'): 2})

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

    def test_or_match(self):
        assert self.or_condition.evaluate(self.a1)
        assert self.or_condition.evaluate(self.a2)
        assert self.or_condition.evaluate(self.b1)
        assert not self.or_condition.evaluate(self.b2)

    def test_basic_metaconditions(self):
        assert TrueCondition().evaluate(None)

        class MockRule(object):
            success_count = 0

        rule = MockRule()
        assert not OneMatchMetacondition().evaluate(rule)
        rule.success_count = 1
        assert OneMatchMetacondition().evaluate(rule)

    def test_composite_action(self):
        sham1 = ShamAction()
        sham2 = ShamAction()
        actions = CompositeAction([sham1, sham2])
        actions.execute('a', 'b')
        actions.execute('d', 'e')
        expected_calls = [ ('a', 'b'), ('d', 'e') ]
        self.assert_equals(expected_calls, sham1.calls)
        self.assert_equals(expected_calls, sham2.calls)

    def test_rule(self):
        rule = Rule(self.and_condition, None)
        assert not rule.evaluate_metacondition()
        rule.action = ShamAction()
        rule.fire(self.b2, 'b')
        expected = []
        self.assert_equal(expected, rule.action.calls)
        assert not rule.evaluate_metacondition()
        rule.action = ShamAction()
        rule.fire(self.a1, 'b')
        expected = [ (self.a1, 'b') ]
        self.assert_equal(expected, rule.action.calls)
        assert rule.evaluate_metacondition()

    def test_rule_system(self):
        rule_a = Rule(self.and_condition, None)
        rule_b = Rule(FieldMatchCondition('pdk', 'name', 'b'), None)

        composite = RuleSystem([rule_a, rule_b])
        assert not composite.evaluate_metacondition()

        expected_empty = []

        rule_a.action = ShamAction()
        rule_b.action = ShamAction()
        composite.fire(self.a1, 'b')
        expected_data = [ (self.a1, 'b') ]
        self.assert_equal(expected_data, rule_a.action.calls)
        self.assert_equal(expected_empty, rule_b.action.calls)
        assert not composite.evaluate_metacondition()

        rule_a.action = ShamAction()
        rule_b.action = ShamAction()
        composite.fire(self.b2, 'b')
        expected_data = [ (self.b2, 'b') ]
        self.assert_equal(expected_empty, rule_a.action.calls)
        self.assert_equal(expected_data, rule_b.action.calls)
        assert composite.evaluate_metacondition()
