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
This module contains functionality supporting the command line handling
framework.
"""

__revision__ = '$Progeny$'

import os
import sys
import optparse
import traceback
import pdk.log as log
from pdk.exceptions import CommandLineError, InputError, \
                    SemanticError, ConfigurationError, \
                    IntegrityFault
logger = log.get_logger()

def load_function(module_name, function_name):
    '''Import the module and locate the function within it.

    Returns the function.
    '''
    module = __import__(module_name, globals(), locals(), ["pdk"])
    function = getattr(module, function_name)
    return function

def apply_and_exit(function, args):
    '''Execute function with args in an exception handler.

    The handler will automatically take care of displaying any error messages
    and exiting if necessary.
    '''
    failure_type = 0
    try:
        return function(args)
    except IntegrityFault, message:
        logger.error("Integrity Fault Noted: %s" % message)
        failure_type = 1
    except CommandLineError, message:
        logger.error("Syntax Error: %s" % message)
        print function.__doc__
        failure_type = 2
    except InputError, message:
        logger.error("Invalid input: %s" % message)
        failure_type = 3
    except SemanticError, message:
        logger.error("Operation cannot be performed: %s" % message)
        failure_type = 4
    except ConfigurationError, message:
        logger.error("Configuration/setup error: %s" % message)
        failure_type = 5
    except SystemExit, status:
        failure_type = status
    except:
        traceback.print_exc(sys.stderr)
        logger.error("Unknown error")
        failure_type = 6
    sys.exit(failure_type)

class Command(object):
    '''Represents a user command as a module/function pair.

    Provides methods for obtaining a help string and invoking the command.
    '''
    def __init__(self, module_name, function_name):
        self.module_name = module_name
        self.function_name = function_name

    def load_function(self):
        '''Return the function which implements this user command.'''
        return load_function(self.module_name, self.function_name)

    def get_help(self):
        '''Return the usage message for this command.'''
        return self.load_function().__doc__

    def __cmp__(self, other):
        return cmp(self.__class__, other.__class__) or \
            cmp(self.module_name, other.module_name) or \
            cmp(self.function_name, other.function_name)

    def __str__(self):
        return 'Command <%r %r>' \
            % (self.module_name, self.function_name)
    __repr__ = __str__

class DirectCommand(object):
    '''Represents a user command as a direct reference to a function.

    Like Command, provides methods for obtaining a help string and invoking
    the command.
    '''
    def __init__(self, function):
        self.function = function

    def load_function(self):
        '''Return the underlying function.'''
        return self.function

    def get_help(self):
        '''Return the usage message for this command.'''
        return self.function.__doc__

    def __cmp__(self, other):
        return cmp(self.__class__, other.__class__) or \
            cmp(self.function, other.function)

    def __str__(self):
        return 'DirectCommand <%r>' % (self.function)
    __repr__ = __str__

class RunnableCommand(object):
    '''Stores a Command object (or similar) with args for invoking later.

    This is essentially a closure we can use to defer loadking and invoking
    a user command.
    '''
    def __init__(self, command, args):
        self.command = command
        self.args = args

    def load_function(self):
        '''Return the function underlying the command.'''
        return self.command.load_function()

    def run(self):
        '''Actually invoke the command and exit.

        This method should never return.
        '''
        function = self.command.load_function()
        apply_and_exit(function, self.args)

    def __cmp__(self, other):
        return cmp(self.__class__, other.__class__) or \
            cmp(self.command, other.command) or \
            cmp(self.args, other.args)

    def __str__(self):
        return 'Runnable <%r %r>' \
            % (self.command, self.args)
    __repr__ = __str__

class HelpCommands(object):
    '''Like the HelpCommand class but shows help for multiple commands.
    '''
    def __init__(self, command_name, commands_obj, exit_value):
        self.command_name = command_name
        self.commands = commands_obj
        self.exit_value = exit_value

    def run(self):
        '''Display help instead of trying to invoke a command.'''
        print self.commands.get_help()
        sys.exit(0)

    def __cmp__(self, other):
        return cmp(self.__class__, other.__class__) or \
            cmp(self.command_name, other.command_name) or \
            cmp(self.commands, other.commands) or \
            cmp(self.exit_value, other.exit_value)

    def __str__(self):
        return 'HelpCommands <%r %r %r>' \
            % (self.command_name, self.commands, self.exit_value)
    __repr__ = __str__

class HelpCommand(object):
    '''Like the RunnableCommand class but shows help instead of invoking.
    '''
    def __init__(self, command):
        self.command = command

    def run(self):
        '''Show help instead of trying to invoke a command.'''
        print self.command.get_help()
        sys.exit(0)

    def __cmp__(self, other):
        return cmp(self.__class__, other.__class__) or \
            cmp(self.command, other.command)

    def __str__(self):
        return 'HelpCommand <%r>' % (self.command)
    __repr__ = __str__

class Commands(object):
    '''Hold references to multiple command objects.

    Takes care of parsing command line data to locate and invoke a user
    command. When necessary uses Help variants of Command classes.
    '''
    def __init__(self, command_name):
        self.command_name = command_name
        self.commands = {}
        self.magic_help = 'help'

    def __cmp__(self, other):
        return cmp(self.__class__, other.__class__) or \
            cmp(self.command_name, other.command_name) or \
            cmp(self.commands, other.commands)

    def __str__(self):
        return 'Commands <%r %r>' \
            % (self.command_name, self.commands)
    __repr__ = __str__

    def easy_map(self, command_name, module, function):
        '''Map a single word command to a module and function name.'''
        self.map((command_name,), Command(module, function))

    def map_direct(self, segments, function):
        '''Map a multi word command directly to a function reference.'''
        self.map(segments, DirectCommand(function))

    def map(self, segments, command):
        '''Map a multi word command to a Command object.'''
        key, tail = segments[0], segments[1:]
        if len(tail) > 0:
            sub_command = self.commands.setdefault(key, Commands(key))
            sub_command.map(tail, command)
        else:
            self.commands[key] = command

    def find_help(self, args, previous = None):
        '''Find a help command for the given args.

        This is invoked when help appears before or within command args.
        --help is handled by optparse directly.
        '''
        if previous is None:
            previous = []
        current = previous + [self.command_name]

        if len(args) < 1:
            return HelpCommands(current, self, 0)

        key, tail = args[0], args[1:]
        if key not in self.commands:
            return HelpCommands(current, self, 0)

        value = self.commands[key]
        if isinstance(value, Commands):
            return value.find_help(tail, current)
        else:
            return HelpCommand(value)

    def find(self, args, previous = None):
        '''Find the appropriate command object for the given args.'''
        if previous is None:
            previous = []
        current = previous + [self.command_name]

        if len(args) < 1:
            return HelpCommands(current, self, 1)
        key, tail = args[0], args[1:]

        if key == self.magic_help:
            return self.find_help(tail, previous)

        if key not in self.commands:
            raise InputError, 'No command found for given arguments'

        value = self.commands[key]
        if isinstance(value, Commands):
            return value.find(tail, current)
        else:
            return RunnableCommand(value, tail)

    def get_help(self):
        '''Return a help message listing my sub commands.'''
        message = ''
        message += 'Command containing subcommands:\n'
        sub_commands = self.commands.keys()
        sub_commands.sort()
        for sub_command in sub_commands:
            message += '    %s\n' % sub_command
        return message

    def run(self, raw_args):
        '''Invoke the proper user function or help for the given args.'''
        runnable_command = self.find(raw_args)
        runnable_command.run()

class CommandArgs(object):
    '''Represents common operations on results from optparse.'''
    def __init__(self, opts, args):
        self.opts = opts
        self.args = args

    def get_new_directory(self):
        '''Get a new directory.

        The directory must not already exist.
        '''
        new_dir = self.pop_arg('new directory')
        if os.path.exists(new_dir):
            raise SemanticError('Already exists: "%s"' % new_dir)
        return new_dir

    def get_one_reoriented_file(self, workspace):
        '''Get exactly one filename, reoriented to the workspace. '''
        if len(self.args) != 1:
            raise CommandLineError('requires a single filename')
        return workspace.reorient_filename(self.pop_arg('filename'))

    def get_reoriented_files(self, workspace, minimum = 1):
        '''Get a minimum number of filenames, reoriented to the workspace.
        '''
        if len(self.args) < minimum:
            message = 'Must provide at least %d filename.' % minimum
            raise CommandLineError(message)
        return [ workspace.reorient_filename(f) for f in self.args ]

    def pop_arg(self, description):
        '''Remove an argument from self.args.

        description is used to form more friendly error messages.
        '''
        if len(self.args) == 0:
            raise CommandLineError('required argument: %s', description)
        return self.args.pop(0)

    def assert_no_args(self):
        '''Assert that no arguments have been given.'''
        if len(self.args) != 0:
            raise CommandLineError('command takes no arguments')

class CommandArgsSpec(object):
    '''Factory for creating CommandArgs objects.

    The spec is a series of strings. For details of which strings are
    available read the source code to the create function.
    '''
    def __init__(self, usage, *spec):
        self.usage = usage
        self.spec = spec

        self.parser = optparse.OptionParser(usage = self.usage)
        op = self.parser.add_option
        for item in self.spec:
            if item == 'commit-msg':
                op('-f', '--commit-msg-file',
                   dest = 'commit_msg_file',
                   help = 'File containing a prewritten commit message.',
                   metavar = 'FILE')

                op("-m", "--commit-msg",
                   dest = "commit_msg",
                   help = "Commit message to use",
                   metavar = 'MESSAGE')

            elif item == 'channels':
                op("-c", "--channel",
                   action = "append",
                   dest = "channels",
                   type = "string",
                   help = "A channel name.")

            elif item == 'machine-readable':
                op("-m", "--machine-readable",
                   action = "store_true",
                   dest = "machine_readable",
                   default = False,
                   help = "Make the output machine readable.")

            elif item == 'no-report':
                op("-R", "--no-report",
                   action = "store_false",
                   dest = "show_report",
                   default = True,
                   help = "Don't bother showing the report.")

            elif item == 'dry-run':
                op("-n", "--dry-run",
                   action = "store_false",
                   dest = "save_component_changes",
                   default = True,
                   help = "Don't save changes after processing.")

            elif item == 'output-dest':
                op('-o', '--out-file', '--out-dest',
                   dest = 'output_dest',
                   help = "Destination for output.",
                   metavar = "DEST")

            elif item == 'show-unchanged':
                op('--show-unchanged',
                   action = "store_true",
                   dest = 'show_unchanged',
                   default = False,
                   help = "Show unchanged items in report.")

            elif item == 'force':
                op('-f', '--force',
                   action = "store_true",
                   dest = 'force',
                   default = False,
                   help = "Force the operation.")


            elif item == 'revision':
                op('-r', '--rev', '--revision',
                   dest = 'revision',
                   metavar = 'REV')
            else:
                assert False, "Unknown command line specification. '%s'" \
                       % item

    def create(self, raw_args):
        '''Create a new CommandArgs object, processing raw_args.'''

        opts, args = self.parser.parse_args(args = raw_args)
        return CommandArgs(opts, args)

    def format_help(self):
        '''Format a complete help message.'''
        return self.parser.format_help()

def make_invokable(fn, *spec):
    '''Make the given function an "invokable".

    Spec strings are optional and may directly follow the function argument.

    Invokables are special because their --help options work properly
    based on the command spec and function doc string.
    '''
    doc_string = fn.__doc__.strip()
    spec = CommandArgsSpec(doc_string, *spec)
    def _invoke(raw_args):
        '''Actually invoke the function.'''
        args = spec.create(raw_args)
        fn(args)

    _invoke.__doc__ = spec.format_help()
    return _invoke

# vim:ai:et:sts=4:sw=4:tw=0:
