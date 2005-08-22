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
command_base

This is the command line controller for all pdk.
"""

__revision__ = '$Progeny$'

import cmd
import os
import sys
import traceback
import types
import pdk.log as log
from pdk.exceptions import CommandLineError, InputError, \
                    SemanticError, ConfigurationError, \
                    IntegrityFault
logger = log.get_logger()

## command_base.py
## Author:  Glen Smith
## Date:    16 June 2005
## Version: 0.0.1


def _get_args_as_list(args):
    """
    If a command is invoked from the command line,
    the args will be one string.
    If the command is invoked from the pdk
    command environment, the args will be a list.
    This utility function returns a list for either
    so you don't have to care
    """
    if isinstance(args, types.StringTypes):
        return args.split()
    elif type(args) == type([]):
        return args
    else:
        raise Exception("unexpected args:" + str(type(args)) + str(args) )


def load_addins(base, *config_files):
    """
    Load the configuration files and load
    the command plugins that they define.
    """
    addin_list = []
    for config_file in config_files:
        for line in open(config_file):
            # Strip comments
            x = line.find('#')
            if x >= 0:
                line = line[:x]
            # See if there's anything left
            line.strip()
            if not line:
                continue
            # We only do cmd.add_external_plugins now
            try:
                modpath, modfunc, local = line.split()
                addin_list.append( (modpath, modfunc, local) )
            except ValueError:
                raise InputError("wrong number of fields: %s" % line)

    base.add_external_plugins(addin_list)

class LazyModuleRef(object):
    """Callable object that defers importing a package until it is 
    actually needed by a function call.

    This prevents us having to import all modules we want to reference, 
    whether we need them or not, and without the workaround of writing 
    a local function to import each module on demand.
    """
    def __init__(self, module, func_param):
        self.module = module
        self.function = func_param
    def __call__(self, *args, **kwargs):
        # Note: if modules NOT in 'pdk' are needed, then add the add'l
        #       modules to the fromlist (final argument to __import__)
        module = __import__(self.module, globals(), locals(), ["pdk"])
        fn = getattr(module, self.function)
        real_args = _get_args_as_list(*args)
        return fn(real_args, **kwargs)
    def getdoc(self):
        """Trick to get docstring from mapped fuction"""
        module = __import__(self.module, globals(), locals(), ["pdk"])
        fn = getattr(module, self.function)
        return fn.__doc__
    __doc__ = property(getdoc, None)

def add_wrapper(function):
    """
    Provide the means to wrap any of our functions in the same
    exception handling call.
    """
    def _with_exception_wrapper_(self, *args, **kwargs):
        "exception-ignoring decorator"
        failure_type = 0
        try:
            return function(self, *args, **kwargs)
        except IntegrityFault, message:
            logger.error("Integrity Fault Noted: %s" % message)
            failure_type = 1
        except CommandLineError, message:
            logger.error("Syntax Error: %s" % message)
            self.do_help(args[0])
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
        except:
            traceback.print_exc(sys.stderr)
            logger.error("Unknown error")
            failure_type = 6
        if self._is_in_shell():
            pass
        else:
            sys.exit(failure_type)
    return _with_exception_wrapper_

class CmdBase(cmd.Cmd):
    """This is the main command object"""

    def __init__(self):
        """
        Set up the command dictionary for pdk
        """
        cmd.Cmd.__init__(self)
        self.prompt = "pdk=>> "
        self.intro  = "Welcome to pdk!"  ## defaults to None
        self._hist    = []      ## No history yet
        self._locals  = {}      ## Initialize execution namespace for user
        self._globals = {}

    cmd.Cmd.onecmd = add_wrapper(cmd.Cmd.onecmd)

    def _is_in_shell(self):
        """invoke to assure commands aren't being called from a script"""
        ret_val = False
        stack = traceback.extract_stack()
        for entry in stack:
            if "cmdloop" in entry:
                ret_val = True
                break
        return ret_val


    ## Command definitions ##
    def do_hist(self, args):
        """Print a list of commands that have been entered"""
        if args:
            raise CommandLineError, "hist command takes no arguments"
        if self._is_in_shell():
            print self._hist


    def do_exit(self, args):
        """Exits from the pdk command shell"""
        if args:
            raise CommandLineError, "exit command takes no arguments"
        return -1


    def do_quit(self, args):
        """Exits from the pdk command shell"""
        if args:
            raise CommandLineError, "quit command takes no arguments"
        return -1

    ## Command definitions to support Cmd object functionality ##
    def do_EOF(self, args):
        """Exit on system end of file character"""
        print ""
        return self.do_exit(args)


    def do_shell(self, args):
        """Pass command to a system shell when line begins with '!'"""
        os.system(args)


    def do_help(self, args):
        """Get help on commands
           'help' or '?' with no arguments prints a list of commands for which help is available
           'help <command>' or '? <command>' gives help on <command>
        """
        ## Help text in the doc string
        cmd.Cmd.do_help(self, args)


    ## Override methods in Cmd object ##
    def preloop(self):
        """Initialization before prompting user for commands.
           Despite the claims in the Cmd documentaion, Cmd.preloop() is not a stub.
        """
        cmd.Cmd.preloop(self)   ## sets up command completion


    def postloop(self):
        """Take care of any unfinished business.
           Despite the claims in the Cmd documentaion, Cmd.postloop() is not a stub.
        """
        cmd.Cmd.postloop(self)   ## Clean up command completion


    def precmd(self, line):
        """ This method is called after the line has been input but before
            it has been interpreted. If you want to modifdy the input line
            before execution (for example, variable substitution) do it here.
        """
        self._hist += [ line.strip() ]
        return line


    def postcmd(self, stop, line):
        """If you want to stop the pdk,
           return something that evaluates to true.
           If you want to do some post command processing, 
           do it here.
        """
        logger.log(stop, line)
        return stop


    def emptyline(self):    
        """Do nothing on empty input line"""
        pass

    def run_one_command(self, fn_name, args):
        """Run one command, reporting errors in the standard way

        Intended for use in command-line (one-shot) invocation of 
        commands in the command base.
        """
        func = getattr(self, fn_name)
        fn_args = args[2:]
        func(fn_args)
    run_one_command = add_wrapper(run_one_command)

    def add_plugins(self, plugins):
        """Add additional functions to this commandbase

        'Plugins' is a list of (localname, function) tuples,
        or equivalents.
        """
        for localname, function in plugins:
            setattr(self, "do_%" % localname, function)

    def add_external_plugins(self, plugins):
        """Add plugins which are located in external modules

        "plugins" is a list of three-tuples consisting of:
              module_path - (dir.something for 'something' in 'dir')
              module_function - name of the function in the module
              localname - do_xxxxx where xxxxx is the command name
        example:
              doghouse.doggy bark4me  bark
        """
        for module_path, module_function, localname in plugins:
            ref = LazyModuleRef(module_path, module_function)
            setattr(self, "do_%s" % localname, ref)

# vim:ai:et:sts=4:sw=4:tw=0:
