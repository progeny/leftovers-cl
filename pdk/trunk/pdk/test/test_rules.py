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

from pdk import rules

class ShamAction(object):
    def __init__(self):
        self.calls = []

    def execute(self, entity):
        self.calls.append(entity)

class TestRuleIdentities(Test):
    def test_field_match_condition(self):
        first = rules.fmc('a', 'b', 'c')
        same_as_first = rules.fmc('a', 'b', 'c')
        second = rules.fmc('d', 'e', 'f')

        assert first == same_as_first
        assert second != first
        assert hash(first) == hash(same_as_first)

    def test_relation_condition(self):
        first = rules.rc(ge, 'a', 'b', 'c')
        same_as_first = rules.rc(ge, 'a', 'b', 'c')
        second = rules.rc(ge, 'd', 'e', 'f')

        assert first == same_as_first
        assert second != first
        assert hash(first) == hash(same_as_first)

    def test_and_or_condition(self):
        first = rules.ac([1, 2, 3])
        same_as_first = rules.ac([1, 2, 3])
        second = rules.oc([1, 2, 3])

        assert first == same_as_first
        assert second != first
        assert hash(first) == hash(same_as_first)

class ConditionsAndRulesFixture(Test):
    def set_up(self):
        super(ConditionsAndRulesFixture, self).set_up()
        self.name_condition = rules.fmc('pdk', 'name', 'a')
        self.version_condition = rules.fmc('pdk', 'version', '1')
        self.and_condition = rules.ac([self.name_condition,
                                           self.version_condition])
        self.or_condition = rules.oc([self.name_condition,
                                         self.version_condition])

        self.a1 = MockPackage('a', '1', deb)
        self.a2 = MockPackage('a', '2', deb)
        self.b1 = MockPackage('b', '1', deb)
        self.b2 = MockPackage('b', '2', deb)

        self.all_packages = [ self.a1, self.a2, self.b1, self.b2 ]

    def test_version_relation(self):
        vrc = rules.rc(ge, 'pdk', 'version', 3)
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
        assert rules.tc().evaluate(None)

        class MockRule(object):
            success_count = 0

        rule = MockRule()
        assert not rules.OneMatchMetacondition().evaluate(rule)
        rule.success_count = 1
        assert rules.OneMatchMetacondition().evaluate(rule)

    def test_composite_action(self):
        sham1 = ShamAction()
        sham2 = ShamAction()
        actions = rules.CompositeAction([sham1, sham2])
        actions.execute('a')
        actions.execute('b')
        expected_calls = [ 'a', 'b' ]
        self.assert_equals(expected_calls, sham1.calls)
        self.assert_equals(expected_calls, sham2.calls)

    def test_rule(self):
        rule = rules.Rule(self.and_condition, None)
        assert not rule.evaluate_metacondition()
        rule.action = ShamAction()
        rule.fire(self.b2)
        expected = []
        self.assert_equal(expected, rule.action.calls)
        assert not rule.evaluate_metacondition()
        rule.action = ShamAction()
        rule.fire(self.a1)
        expected = [ self.a1 ]
        self.assert_equal(expected, rule.action.calls)
        assert rule.evaluate_metacondition()

    def test_rule_system(self):
        rule_a = rules.Rule(self.and_condition, None)
        rule_b = rules.Rule(rules.fmc('pdk', 'name', 'b'), None)

        composite = rules.RuleSystem([rule_a, rule_b])
        assert not composite.evaluate_metacondition()

        expected_empty = []

        rule_a.action = ShamAction()
        rule_b.action = ShamAction()
        composite.fire(self.a1)
        expected_data = [ self.a1 ]
        self.assert_equal(expected_data, rule_a.action.calls)
        self.assert_equal(expected_empty, rule_b.action.calls)
        assert not composite.evaluate_metacondition()

        rule_a.action = ShamAction()
        rule_b.action = ShamAction()
        composite.fire(self.b2)
        expected_data = [ self.b2 ]
        self.assert_equal(expected_empty, rule_a.action.calls)
        self.assert_equal(expected_data, rule_b.action.calls)
        assert composite.evaluate_metacondition()
