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
workspace

Library interface to pdk workspace
"""
__revision__ = '$Progeny$'

from pdk.util import assert_python_version
assert_python_version()
import os
import sys
from pdk import version_control


def clone(args):
    """
    Create the standard product work area beneath pwd.
    Usage:
    pdk clone [source URL] [local name]
    """
    product_url = args[0]
    work_area = args[1]
    branch_name = args[2]
    local_head_name = args[3]
    remote_head_name = args[4]
    ws = Workspace()
    ws.clone(
        product_url, 
        work_area,
        branch_name, 
        local_head_name,
        remote_head_name
    )


def create(args):
    """
    Create a local pdk working directory.
    Usage:
    pdk workspace create [workspace name]
    """
    if not args:
        print sys.stderr, "requires an argument"
        print __doc__
    else:
        name = args[0]
        ws = Workspace()
        ws.create(name)


def add(args):
    """
    add a local working item under version control
    """
    name = args[0]
    ws = Workspace()
    return ws.add(name)


def commit(args):
    """
    commit local changes
    """
    head_name = args[0]
    remark = args[1]
    ws = Workspace()
    ws.commit(head_name, remark)


def update(args):
    """
    commit local changes
    """
    upstream_name = args[0]
    remote_head_name = args[1]
    ws = Workspace()
    ws.update(upstream_name, remote_head_name)


class Workspace(object):
    """
    Library interface to pdk workspace
    """
    def __init__(self):
#    def __init__(self, product_URL, work_area, branch_name, \
#                 local_head_name, remote_head_name):
        self.version_control = version_control.VersionControl()


    def clone(self, product_URL, work_area, branch_name, local_head_name,
             remote_head_name):
        """
        Create a local instance of the database
        with a product from a remote URL
        """
        
        start_path = os.getcwd()
        product_path = start_path + '/' + work_area
        os.mkdir(product_path)
        os.chdir(product_path)
        
        self.version_control.clone(
            product_URL,
            branch_name,
            local_head_name,
            remote_head_name
            )
        os.mkdir(product_path + '/cache')
        os.mkdir(product_path + '/work')
        os.chdir(start_path)


    def add(self, name):
        """
        Create an 'empty' local instance of the database
        """
        return self.version_control.add(name)


    def create(self, name):
        """
        Create an 'empty' local instance of the database
        """
        if os.path.exists(name):
            raise Exception, "directory already exists"
        start_path = os.getcwd()
        product_path = start_path + '/' + name
        os.mkdir(product_path)
        os.chdir(product_path)
        self.version_control.create()
        os.mkdir(product_path + '/cache')
        os.chdir(start_path)


    def commit(self, head_name, remark):
        """
        Commit changes to version control
        """
        self.version_control.commit(head_name, remark)


    def update(self, upstream_name, remote_head_name):
        """
        Get latest changes from version control
        """
        self.version_control.update(upstream_name, remote_head_name)


# vim:ai:et:sts=4:sw=4:tw=0:
