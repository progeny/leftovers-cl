#!/usr/bin/python
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
from pdk.meta import ComponentMeta
from sets import Set

class TestMeta(Test):
    def test_set(self):
        meta = ComponentMeta()
        meta.set(1, 'a', 'b', 'c')
        self.assert_equal('c', meta.get(1, 'b'))
        try:
            meta.get(1, 2)
            self.fail()
        except KeyError, key:
            self.assert_equal('2', str(key))

        try:
            meta.get(2, None)
        except KeyError, key:
            self.assert_equal('2', str(key))

        assert meta.has_predicate(1, 'b')
        assert not meta.has_predicate(2, 'b')
        assert not meta.has_predicate(1, 'a')

    def test_domains(self):
        meta = ComponentMeta()
        meta.set(1, 'd', 'a', 'b')
        meta.set(1, 'd', 'c', 'd')
        meta.set(1, '', 'e', 'f')
        meta.set(2, 'd', 'g', 'h')
        meta.set(2, 'd', 'i', 'k')
        meta.set(2, '', 'k', 'l')

        self.assert_equal(Set(['a', 'c']),
                          Set(meta.get_domain_predicates(1, 'd')))
        self.assert_equal(Set(['g', 'i']),
                          Set(meta.get_domain_predicates(2, 'd')))

    def test_placeholder(self):
        meta = ComponentMeta()
        meta.set(1, 'd', 'a', 'b')
        meta.set(1, '', 'e', 'f')
        meta.set(2, 'd', 'g', 'h')
        meta.set(2, '', 'k', 'l')

        placeholder = meta[1]
        placeholder.set('d', 'c', 'd')
        self.assert_equal('b', placeholder['a'])
        self.assert_equal('d', placeholder['c'])
        self.assert_equal('f', placeholder['e'])

        self.assert_equal(Set(['a', 'c']),
                          Set(placeholder.get_domain_predicates('d')))

        try:
            placeholder['g']
            self.fail()
        except KeyError, key:
            self.assert_equal("'g'", str(key))

        placeholder = meta[2]
        placeholder.set('d', 'i', 'k')
        self.assert_equal('h', placeholder['g'])
        self.assert_equal('k', placeholder['i'])
        self.assert_equal('l', placeholder['k'])

        self.assert_equal(Set(['g', 'i']),
                          Set(placeholder.get_domain_predicates('d')))

        try:
            placeholder['a']
            self.fail()
        except KeyError, key:
            self.assert_equal("'a'", str(key))

        try:
            meta[3]
            self.fail()
        except KeyError, key:
            self.assert_equal('3', str(key))
