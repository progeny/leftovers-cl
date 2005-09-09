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
version_control

Version Control Library
Part of the PDK suite
"""
__revision__ = '$Progeny$'

import os
from cStringIO import StringIO
from pdk.exceptions import IntegrityFault
from pdk.util import shell_command
from pdk.util import relative_path, pjoin

## version_control
## Author:  Glen Smith
## Date:    23 June 2005
## Version: 0.0.1


## Command definitions ##

class VersionControlError(StandardError):
    '''Raised when there are version control problems.'''
    pass


def _cd_shell_command(path, command_string, stdin=None, debug=False):
    """Wrapper for shell_command which includes the necessary dir
    path hijinks for version control (must execute from .git parent)

    All command parameters which are files must have already been 
    modified to be relative to the ./work directory of the project.
    """
    original_dir = os.getcwd()
    os.chdir(path)
    try:
        result = shell_command(command_string, stdin, debug)
    finally:
        os.chdir(original_dir)
    return result


def create(working_path):
    """Create a version control repo in the given work dir """
    # Since we're porcelain, we have to set the stage for command-line
    # tools -- saving the dir is "bread crumbs"
    starting_path = os.getcwd() 
    try:
        # If we're not there already, go to our working path
        if not starting_path.endswith(working_path):
            os.chdir(working_path)
        shell_command('git-init-db')
    finally:
        # Follow the bread crumbs home
        os.chdir(starting_path)
    return _VersionControl(working_path)


class _VersionControl(object):
    """
    Library Interface to pdk version control
    """

    def __init__(self, work_path):
        if not os.path.isdir(work_path):
            raise IntegrityFault(
                "%s is not a directory" % work_path
                )
        self.work_dir = work_path

        self.vc_dir = os.path.join(work_path, '.git')
        if not os.path.isdir(self.vc_dir):
            raise IntegrityFault(
                "%s is not a directory" % self.vc_dir
                )
        self.remotes_dir = pjoin(self.vc_dir ,'remotes')
        if not os.path.exists(self.remotes_dir):
            os.mkdir(self.remotes_dir)

    def add(self, name):
        """
        Initialize version control
        """
        name = relative_path(self.work_dir, name)
        cmd = 'git-update-cache --add %s' % name
        return _cd_shell_command(self.work_dir, cmd)

    def remove(self, name):
        """
        Initialize version control
        """
        name = relative_path(self.work_dir, name)
        shell_command('rm ' + name)
        cmd = 'git-update-cache --remove %s' % name
        return _cd_shell_command(self.work_dir, cmd)

    def revert(self, name):
        """
        Initialize version control
        """
        name = relative_path(self.work_dir, name)
        shell_command('rm ' + name)
        self.update()

    def commit(self, remark):
        """
        call git commands to commit local work
        """
        head_file = pjoin(self.vc_dir, 'HEAD')

        parent_id = None

        if os.path.exists(head_file):
            the_file = file(head_file, 'r')
            parent_id = the_file.read().strip()
            the_file.close()

        work_dir = self.work_dir
        files = _cd_shell_command(work_dir, \
                                 'git-diff-files --name-only').split()
        files = [ relative_path(work_dir, item) 
                  for item in files ]
        _cd_shell_command(work_dir, 'git-update-cache ' + \
                          ' '.join(files))

        sha1 = _cd_shell_command(work_dir, 'git-write-tree').strip()

        commit_cmd = 'git-commit-tree ' + str(sha1)
        if parent_id:
            commit_cmd += ' -p ' + str(parent_id)
        output = shell_command(commit_cmd, StringIO(remark))

        filename = pjoin(work_dir, head_file)
        the_file = file(filename, 'w')
        the_file.write(str(output))
        the_file.close()


    def update(self):
        """
        update the version control
        """
        start_dir = os.getcwd()
        try:
            shell_command('git-read-tree HEAD')
            shell_command('git-checkout-cache -a')
        finally:
            os.chdir(start_dir)

    def update_from_remote(self, upstream_name):
        """
        update the version control
        """
        if self.is_new():
            command_string = 'git fetch %(name)s :%(name)s' \
                % {'name' : upstream_name}
            _cd_shell_command(self.work_dir, command_string)
            command_string = 'git checkout -b master -f %s' % upstream_name
            _cd_shell_command(self.work_dir, command_string)
        else:
            command_string = 'git pull %s' % upstream_name
            _cd_shell_command(self.work_dir, command_string)

    def cat(self, filename):
        '''Get the unchanged version of the given filename.'''
        git_result = shell_command('git-diff-files ' + filename).strip()
        result = ''
        if git_result:
            parts = git_result.split()
            git_blob_id = parts[2]
            result = StringIO(shell_command('git-cat-file blob %s'
                                             % git_blob_id))
        else:
            result = open(filename)
        return result

    def push(self, remote):
        '''Push local commits to a remote git.'''
        command_string = 'git ls-remote "%s"' % remote
        output = _cd_shell_command(self.work_dir, command_string)
        push_command_string = 'git push "%s"' % remote
        if '\tHEAD\n' not in output:
            push_command_string += ' master'
        _cd_shell_command(self.work_dir, push_command_string)

    def is_new(self):
        '''Is this a "new" (no commits) git repository?'''
        head_file = pjoin(self.vc_dir, 'HEAD')
        return not os.path.exists(head_file)

def patch(args):
    """Perform a version control patch command"""
    file_name = args[0]
    command_string = 'git-apply ' + file_name
    shell_command(command_string)
##    git-update-cache progeny.com/apache.xml
##    pdk commit master "Required commit remark"

# vim:ai:et:sts=4:sw=4:tw=0:
