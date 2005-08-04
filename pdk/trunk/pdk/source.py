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
source

Library interface to pdk source
"""
__revision__ = '$Progeny$'

import os
#from pdk import cache
#from pdk import version_control
#from pdk import workspace
import sys


def publish(args):
    """
    Create the standard product source at the argument path,
    using the current workspace.
    Usage:
    pdk publish [source_path]
    """
    workspace_path = args[0]
    workspace_branch = args[1]
    source_path = args[2]
    source_branch = args[3]
    source = Source(source_path)
    source.publish(workspace_path, workspace_branch, source_branch)


class Source(object):
    """
    Library interface to pdk source
    """
    def __init__(self, source_path, source_name):
        """
        Initialize source
        """
        start_path = os.getcwd()
        self.replace = False
        if os.path.exists(source_path):
            if self.replace:
                os.removedirs(source_path)
            else:
                raise Exception, "directory already exists"

#1) find the head of the current workspace
        #ws = workspace.Workspace()
        #get it from the command param...for now.
        #workspace_path = ws.path
#2a) create the destination dir 
        os.mkdir(source_path)
        os.chdir(source_path)
        #make sure we define the path attribute in
        #absolute terms
        self.path = os.getcwd()
        self.name = source_name

        vc_path = self.path + '/VC'
        os.mkdir(vc_path)
#2b) ...with cache...
        cache_path = self.path + '/cache'
        os.mkdir(cache_path)
#2c) ...& vc dirs.
        os.chdir(start_path)


    def publish(self, workspace_path, workspace_branch, source_branch):
        """
        Create the standard product source at the argument path,
        using the current workspace.
        Usage:
        pdk publish [source_path]
        options:
        -r --replace: allows overwriting an existing source,
        destroying all content that currently exists
        """
        start_path = os.getcwd()
        print sys.stderr, workspace_branch, source_branch

#3) copy (cache-push?) the workspace/cache into the dest/cache dir.
#        chache.cache_push(workspace_cache_path, source_cache_path)
#4) Drop the destination's 'vc' directory.
#5) Recursive-copy the workspace/vc directory to destination/vc
        os.chdir(start_path)
        print sys.syserr, workspace_path




# vim:ai:et:sts=4:sw=4:tw=0:
