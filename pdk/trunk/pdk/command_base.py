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
#import sys
#import getopt
import pdk.log as log
logger = log.get_logger()
#from pdk.component import ComponentDescriptor
#from pdk.cache import Cache
#from pdk.yaxml import parse_yaxml_file

## command_base.py
## Author:  Glen Smith
## Date:    16 June 2005
## Version: 0.0.1

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
        return fn(*args, **kwargs)
    def getdoc(self):
        """Trick to get docstring from mapped fuction"""
        module = __import__(self.module, globals(), locals(), ["pdk"])
        fn = getattr(module, self.function)
        return fn.__doc__
    __doc__ = property(getdoc, None)
        
class PdkBase(cmd.Cmd):
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


    def _is_in_shell(self):
        """invoke to assure commands aren't being called from a script"""
        import traceback
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
            raise Exception, "hist command takes no arguments"
        if self._is_in_shell():
            print self._hist


    def do_exit(self, args):
        """Exits from the pdk command shell"""
        if args:
            raise Exception, "exit command takes no arguments"
        return -1


    ## Command definitions to support Cmd object functionality ##
    def do_eof(self, args):
        """Exit on system end of file character"""
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


for addin_file in [ x for x in ('~/.pdk_addins','.pdk_addins')
                    if os.path.exists(x) ]:
    for record in open(addin_file):
        path, function, localname  = record.split()
        ref = LazyModuleRef(path, function)
        setattr(PdkBase, localname, ref) 

# vim:ai:et:sts=4:sw=4:tw=0:
