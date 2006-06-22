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

from pdk.exceptions import InputError
from pdk.command_base import Commands, Command, RunnableCommand, \
     HelpCommand, HelpCommands, DirectCommand

__revision__ = "$Progeny$"

def dummy_function():
    '''test doc'''
    pass

class TestCommands(Test):
    def test_find(self):
        com = Commands('aaa')
        com.easy_map('a', 'b', 'c')
        com.map_direct(['d'], dummy_function)
        com.map(['g', 'h'], Command('i', 'j'))

        def rc(module, function, args):
            return RunnableCommand(Command(module, function), args)
        def rcd(function, args):
            return RunnableCommand(DirectCommand(function), args)
        def hc(module, function):
            return HelpCommand(Command(module, function))
        hcs = HelpCommands

        self.assert_equal(rc('b', 'c', ['1', '2', '3']),
                          com.find(['a', '1', '2', '3']))
        self.assert_equal(rc('i', 'j', ['1', '2', '3']),
                          com.find(['g', 'h', '1', '2', '3']))
        self.assert_equal(hc('b', 'c'),
                          com.find(['help', 'a', '1', '2', '3']))
        self.assert_equal(hc('i', 'j'),
                          com.find(['g', 'help', 'h', '1', '2', '3']))
        self.assert_equal(hcs(['aaa', 'g'], com.commands['g'], 0),
                          com.find(['help', 'g', '1', '2', '3']))
        self.assert_equal(hcs(['aaa', 'g'], com.commands['g'], 1),
                          com.find(['g']))
        self.assert_equal(rcd(dummy_function, ['1', '2', '3']),
                          com.find(['d', '1', '2', '3']))

        try:
            com.find(['zzzzzz'])
        except InputError:
            pass
        else:
            self.fail('Should have thrown InputException!')

    def test_runnable_command(self):
        def rc(args):
            return RunnableCommand(Command('pdk.test.test_commands',
                                           'dummy_function'), args)
        com = rc([])
        self.assert_equal(dummy_function, com.load_function())


    def test_command(self):
        com = Command('pdk.test.test_commands', 'dummy_function')
        self.assert_equal('test doc', com.get_help())
