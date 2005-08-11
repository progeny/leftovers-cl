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

import os
from pdk import version_control
from pdk import util
from pdk.cache import Cache
from pdk.exceptions import ConfigurationError, CommandLineError

def current_workspace():
    """
    Locate the current workspace and return the workspace object.


    This works on the assumption/presumption that you are in a
    workspace currently.  It merely looks upward in the directory
    tree until it finds its' marker files/dirs, and then instances
    the Workspace object with that directory as its base.
    """
    whole_path = util.find_base_dir()
    if not whole_path:
        raise ConfigurationError("Not currently in a workspace")
    return _Workspace(whole_path)

def info(ignore):
    """Report information about the local workspace"""
    ignore.pop() # stop pylint complaining about unused arg
    try:
        ws = current_workspace()
        print 'Base Path: %s' % ws.location 
        print 'Cache is: %s' % os.path.join(ws.location,'cache')
    except ConfigurationError, message:
        print message
    

def create_workspace(args):
    """
    Create a local pdk working directory.
    Usage:
    pdk workspace create [workspace name]
    """
    if not args:
        raise CommandLineError("requires an argument")
    name = args[0]
    path = os.path.join(os.getcwd(), name)
    #os.mkdir(path)

    #vc = version_control.VersionControl(None)
    #vc = vc.create(path)

    ws = _Workspace(path).create(path)
    return ws
    
# For external linkage
create = create_workspace


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

    ws = _Workspace(work_area)
    ws.clone(
        product_url
        , work_area
        , branch_name
        , local_head_name
        )


def pull(args):
    """ 
    Started from the shell script production_pull
    Does a pull from one git directory to another.
    """
    remote_vc_path = os.path.join(args[0], 'VC')
    local_vc_path = os.path.join(args[1], 'VC')
    if not os.path.isdir(remote_vc_path):
        raise CommandLineError(
            "Remote directory %s does not exist" % remote_vc_path
            )
    if not os.path.isdir(local_vc_path):
        raise CommandLineError(
            "Local directory %s does not exist" % local_vc_path
            )

    local_head_name = args[2]
    
    start_path = os.getcwd()
    try:
        os.environ['GIT_DIR'] = local_vc_path

        remote_file = file(remote_vc_path + '/HEAD', 'r')
        remote_commit_id = remote_file.read().strip()
        remote_file.close()

        version_control._shell_command('git-local-pull -a -l ' + \
                                        remote_commit_id + ' ' + \
                                        remote_vc_path)

        local_head = local_vc_path + '/refs/heads/' + local_head_name
        tmp_file = file(local_head, 'w')
        tmp_file.write(remote_commit_id)
        tmp_file.close()
    finally:
        os.chdir(start_path)


def add(args):
    """
    add a local working item under version control
    """
    name = args[0]
    ws = current_workspace()
    return ws.add(name)


def commit(args):
    """
    commit local changes
    """
    head_name = args[0]
    remark = args[1]
    ws = current_workspace()
    ws.commit(head_name, remark)


def update(args):
    """
    commit local changes
    """
    upstream_name = args[0]
    ws = current_workspace()
    ws.update(upstream_name)


class _Workspace(object):
    """
    Library interface to pdk workspace
    """
#    def __init__(self, product_URL, work_area, branch_name, \
#                 local_head_name, remote_head_name):
        # look at the os.getcwd():
        # If we are in an existing workspace,
        # we should populate attributes accordingly
    def __init__(self, directory):
        location = self.location = directory
        if os.path.isdir(directory):
            self.its_version_control = \
                version_control.VersionControl(location)
            self.its_cache = Cache(os.path.join(location,'cache'))
        else:
            self.its_version_control = None
            self.its_cache = None

    def cache(self):
        """Return the current workspace's cache component"""
        return self.its_cache

    def version_control(self):
        """Return the local workspace's version control component"""
        if not self.its_version_control:
            ctor = version_control.VersionControl
            self.its_version_control = ctor(self.location)
        return self.its_version_control

    def clone(self, product_URL, work_area, branch_name,
                 local_head_name):
        """
        Create a local instance of the workspace
        with a product from a remote URL
        """
        start_path = os.getcwd()
        try:
            self.create(work_area)
            os.chdir(work_area + '/work')
            self.version_control().clone(
                product_URL
                , branch_name
                , local_head_name
                )
        finally:
            os.chdir(start_path)

    def create(self, name):
        """
        Create an 'empty' local instance of the workspace
        """
        vc_constructor = version_control.VersionControl
        if os.path.exists(name):
            raise Exception, "directory already exists"

        start_path = os.getcwd()
        try:
            product_path = os.path.join(start_path, name)
            os.mkdir(product_path)
            os.mkdir(os.path.join(product_path,'cache'))
            symlink_dir = os.path.join(product_path, 'VC')

            # Darned two-stage creation
            vc = self.its_version_control = vc_constructor(product_path)
            vc.create()
            # Link to top VC dir, so workspace is a "source"
            vc_dir = os.path.abspath(vc.location)
            os.symlink(vc_dir, symlink_dir)
        finally:
            os.chdir(start_path)

    def add(self, name):
        """
        Create an 'empty' local instance of the database
        """
        return self.version_control().add(name)


    def commit(self, head_name, remark):
        """
        Commit changes to version control
        """
        self.version_control().commit(head_name, remark)


    def update(self, upstream_name):
        """
        Get latest changes from version control
        """
        self.version_control().update(upstream_name)


# vim:ai:et:sts=4:sw=4:tw=0:
