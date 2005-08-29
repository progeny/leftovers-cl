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
import sys
from pdk import version_control
from pdk import util
from pdk.cache import Cache
from pdk.channels import ChannelData
from pdk.exceptions import ConfigurationError, IntegrityFault, \
          SemanticError, CommandLineError

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

def currently_in_a_workspace():
    """Determine if pwd is in a workspace """
    result = False
    if util.find_base_dir():
        result = True
    return result

def info(ignore):
    """Report information about the local workspace"""
    ignore.pop() # stop pylint complaining about unused arg
    try:
        ws = current_workspace()
        print 'Base Path: %s' % ws.location 
        print 'Cache is: %s' % os.path.join(ws.location,'cache')
    except ConfigurationError, message:
        print message
    

def create_workspace(workspace_root):
    """
    Create a local pdk working directory.
    Usage:
        pdk workspace create [workspace name]
    """
    # Friends don't let friends nest workspaces.
    if currently_in_a_workspace():
        raise SemanticError(
            "%s is Already in a workspace"
            % os.getcwd()
            )

    # localize some functions
    pjoin = os.path.join 
    absolute = os.path.abspath

    # Plan the layout 
    work_root = absolute(pjoin(os.getcwd(), workspace_root))
    work_path = pjoin(work_root, 'work')
    cache_path = pjoin(work_root, 'cache')
    vc_link_path = pjoin(work_root, 'VC')

    # Create empty workspace
    print "Creating: %s, %s" % (work_path, cache_path)
    os.makedirs(work_path)
    os.makedirs(cache_path)
    vc = version_control.create(work_path)
    os.symlink(absolute(vc.vc_dir), absolute(vc_link_path))

    # Return an object that wraps the workspace
    return _Workspace(work_root)
    
# For external linkage
def create(args):
    """
    cmd front-end for the workspace create function

    args = [target_path]
    """
    # Friends don't let friends nest workspaces.
    if currently_in_a_workspace():
        raise SemanticError(
            "%s is Already in a workspace"
            % os.getcwd()
            )

    if not args:
        raise CommandLineError("requires an argument")
    create_workspace(args[0])

def clone(args):
    """
    Create the standard product work area beneath pwd.
    Usage:
    pdk clone [remote_url] [local_dir] [src_branch] [local_head]
    """
    # Friends don't let friends nest workspaces.
    if currently_in_a_workspace():
        raise SemanticError(
            "%s is Already in a workspace"
            % os.getcwd()
            )
    remote_product_url = args[0]
    local_work_area = args[1]
    branch_name = args[2]
    local_head_name = args[3]

    # We want the work area to NOT already exist
    if os.path.isdir(local_work_area):
        raise SemanticError(
            "%s is already a work area" % local_work_area
            )

    # Make the work directory
    ws = create_workspace(local_work_area)
    if not os.path.isdir(local_work_area):
        raise IntegrityFault(
            "%s does not exist after create" 
            %  local_work_area
            )

    # Start cloning
    start_path = os.getcwd()
    try:
        version_control.clone(
            remote_product_url
            , branch_name
            , local_head_name
            , ws.workdir
            )
    finally:
        os.chdir(start_path)
    return ws


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

        util.shell_command('git-local-pull -a -l ' + \
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
    add: Put the file under version control, scheduling it
    for addition to repository.  It will be added in next commit.
    usage: add filename

    Valid options:
    none
    """
    name = args[0]
    ws = current_workspace()
    return ws.add(name)

def remove(args):
    """
    remove: Remove  a file from version control.
    usage: remove FILE

    The item specified by FILE is scheduled for deletion upon
    the next commit.  A files that has not been committed is 
    immediately removed from the working copy.

    Valid options:
    none
    """
    name = args[0]
    ws = current_workspace()
    return ws.remove(name)

def cat(args):
    """
    cat: Output the content of specified file from the
    version control repository.
    usage: cat FILE

    Valid options:
    none
    """
    name = args[0]
    ws = current_workspace()
    result = ws.cat(name).read().strip()
    print >> sys.stdout, result
    return result

def revert(args):
    """
    revert: Restore pristine working copy file (undo most local edits).
    usage: revert FILE

    Valid options:
    none
    """
    name = args[0]
    ws = current_workspace()
    return ws.revert(name)

def commit(args):
    """
    commit: Send changes from your working copy to the repository.
    usage: commit FILE MESSAGE

    A log message must be provided.

    Valid options:
    none
    """
    remark = args[0]
    ws = current_workspace()
    ws.commit(remark)

def update(ignore):
    """
    update: Bring changes from the repository into the working copy.
    usage: update

    Synchronize working copy to HEAD in repository.

    Valid options:
    none
    """
    ws = current_workspace()
    ws.update()
    return ignore

def update_from_remote(args):
    """
    update_from_remote: Bring changes from REMOTE into the working copy.
    usage: update [REMOTE]

      Bring working copy up-to-date with HEAD rev.

    Valid options:
    none
    """
    remote_name = args[0]
    ws = current_workspace()
    ws.update_from_remote(remote_name)


class _Workspace(object):
    """
    Library interface to pdk workspace
    """
    def __init__(self, directory):
        location = self.location = directory
        if not os.path.isdir(directory):
            raise IntegrityFault(
                "%s is not a workspace directory" 
                % directory
                )
        self.workdir = workdir = os.path.join(location,'work')
        self.its_version_control = \
            version_control._VersionControl(workdir)
        self.its_cache = Cache(os.path.join(location,'cache'))

    def cache(self):
        """Return the current workspace's cache component"""
        return self.its_cache

    def version_control(self):
        """Return the local workspace's version control component"""
        if not self.its_version_control:
            ctor = version_control.VersionControl
            self.its_version_control = ctor(self.location)
        return self.its_version_control

    def channels(self):
        """Return the current channel index

        The data returned is a ChannelData instance.
        """
        return ChannelData.load_cached()

    def add(self, name):
        """
        Add an item to local version control
        """
        return self.version_control().add(name)

    def remove(self, name):
        """
        Remove an item from local version control
        """
        return self.version_control().remove(name)

    def cat(self, name):
        """
        Remove an item from local version control
        """
        return self.version_control().cat(name)

    def revert(self, name):
        """
        Remove an item from local version control
        """
        return self.version_control().revert(name)

    def commit(self, remark):
        """
        Commit changes to version control
        """
        self.version_control().commit(remark)

    def update(self):
        """
        Get latest changes from version control
        """
        self.version_control().update()

    def update_from_remote(self, upstream_name):
        """
        Get latest changes from version control
        """
        self.version_control().update_from_remote(upstream_name)


# vim:ai:et:sts=4:sw=4:tw=0:
