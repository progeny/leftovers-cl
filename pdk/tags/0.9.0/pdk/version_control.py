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
from pdk.exceptions import SemanticError
from pdk.util import shell_command
from pdk.util import relative_path, pjoin

## version_control
## Author:  Glen Smith
## Date:    23 June 2005
## Version: 0.0.1


class VersionControl(object):
    """
    Library Interface to pdk version control
    """

    def __init__(self, work_path, git_path):
        self.work_dir = work_path
        self.vc_dir = git_path

    def popen2(self, command):
        """Forks off a pdk command.

        Returns handles to stdin and standard out.
        command is fed to /bin/sh, not exec'ed directly.

        Command is executed with cwd set to self.work_dir, and
        env variable GIT_DIR pointed at self.vc_dir.
        """
        child_in_read, child_in_write = os.pipe()
        parent_in_read, parent_in_write = os.pipe()
        pid = os.fork()
        if pid:
            # parent
            os.close(child_in_read)
            os.close(parent_in_write)

            def _wait():
                '''A closure. Calling it waits on the remote process.

                If the remote process has non-zero status, an exception
                will be raised.
                '''
                dummy, status = os.waitpid(pid, 0)
                if status:
                    raise SemanticError, 'command "%s" failed: %d' \
                          % (command, status)

            return os.fdopen(child_in_write, 'w'), \
                   os.fdopen(parent_in_read), \
                   _wait
        else:
            # child
            os.close(child_in_write)
            os.close(parent_in_read)
            os.dup2(child_in_read, 0)
            os.dup2(parent_in_write, 1)
            os.chdir(self.work_dir)
            shell_cmd = '{ %s ; } ' % command
            os.execve('/bin/sh', ['/bin/sh', '-c', shell_cmd],
                      {'GIT_DIR': self.vc_dir})

    def shell_to_string(self, command):
        """Execute self.popen2; capture stdout as a string.

        Uses self.popen2, so it inherits those characteristics.

        Closes the command's stdin.
        """
        remote_in, remote_out, wait = self.popen2(command)
        remote_in.close()
        value = remote_out.read()
        remote_out.close()
        wait()
        return value

    def create(self):
        """
        Populate self.vc_dir with a git skeleton.
        """
        self.shell_to_string('git-init-db')
        os.makedirs(pjoin(self.vc_dir, 'remotes'))

    def add(self, name):
        """
        Initialize version control
        """
        name = relative_path(self.work_dir, name)
        cmd = 'git-update-cache --add %s' % name
        return self.shell_to_string(cmd)

    def remove(self, name):
        """
        Initialize version control
        """
        name = relative_path(self.work_dir, name)
        self.shell_to_string('rm ' + name)
        cmd = 'git-update-cache --remove %s' % name
        return self.shell_to_string(cmd)

    def revert(self, name):
        """
        Initialize version control
        """
        name = relative_path(self.work_dir, name)
        self.shell_to_string('rm ' + name)
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
        files = self.shell_to_string('git-diff-files --name-only').split()
        files = [ relative_path(work_dir, item) for item in files ]
        self.shell_to_string('git-update-cache ' + ' '.join(files))

        sha1 = self.shell_to_string('git-write-tree').strip()

        commit_cmd = 'git-commit-tree ' + sha1
        if parent_id:
            commit_cmd += ' -p ' + str(parent_id)
        remote_in, remote_out, wait = self.popen2(commit_cmd)
        remote_in.write(remark)
        remote_in.close()
        commit_id = remote_out.read()
        remote_out.close()
        wait()

        the_file = file(head_file, 'w')
        the_file.write(str(commit_id))
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
        update the version control by pulling from remote sources.
        """
        if self.is_new():
            command_string = 'git fetch %(name)s :%(name)s' \
                % {'name' : upstream_name}
            self.shell_to_string(command_string)
            command_string = 'git checkout -b master -f %s' % upstream_name
            self.shell_to_string(command_string)
        else:
            command_string = 'git pull %s' % upstream_name
            self.shell_to_string(command_string)

    def cat(self, filename):
        '''Get the unchanged version of the given filename.'''
        command = 'git-diff-files ' + filename
        git_result = self.shell_to_string(command).strip()
        if git_result:
            parts = git_result.split()
            git_blob_id = parts[2]
            result = StringIO(self.shell_to_string('git-cat-file blob %s'
                                                     % git_blob_id))
        else:
            result = open(filename)
        return result

    def push(self, remote):
        '''Push local commits to a remote git.'''
        command_string = 'git ls-remote "%s"' % remote
        output = self.shell_to_string(command_string)
        push_command_string = 'git push "%s"' % remote
        if '\tHEAD\n' not in output:
            push_command_string += ' master'
        self.shell_to_string(push_command_string)

    def is_new(self):
        '''Is this a "new" (no commits) git repository?'''
        head_file = pjoin(self.vc_dir, 'HEAD')
        return not os.path.exists(head_file)

# vim:ai:et:sts=4:sw=4:tw=0:
