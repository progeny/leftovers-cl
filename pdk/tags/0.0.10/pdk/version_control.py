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
from sets import Set
from cStringIO import StringIO
from pdk.exceptions import SemanticError
from pdk.util import relative_path, pjoin, shell_command

## version_control
## Author:  Glen Smith
## Date:    23 June 2005
## Version: 0.0.1

class CommitNotFound(SemanticError):
    '''Raised when a caller attempts to operate on a non-existent commit.'''
    pass

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
        def set_up_child():
            '''Child process should chdir [work]; and set GIT_DIR.'''
            os.chdir(self.work_dir)
            os.environ.update({'GIT_DIR': self.vc_dir})
        return shell_command(command, set_up_child)

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
            self.shell_to_string('git-read-tree HEAD')
            self.shell_to_string('git-checkout-cache -a')
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

    def get_all_refs(self):
        '''List all raw commit_ids found under the git refs directory.'''
        command_string = 'git-rev-parse --all'
        output = self.shell_to_string(command_string)
        commit_ids = [ i.strip() for i in output.split() ]
        return commit_ids

    def is_valid_new_head(self, new_head):
        '''Does this new head_id include the old head_id in its history.'''
        if self.is_new():
            return True
        new_revs = self.get_rev_list([new_head])
        old_head = self.get_commit_id('HEAD')
        return old_head in new_revs

    def filter_refs(self, raw_refs):
        '''Return a list of refs that are given and present.

        Applies only to commit ids.
        '''
        refs = Set(raw_refs)
        head_ids = self.get_all_refs()
        refs_here = self.get_rev_list(head_ids)
        return refs_here & refs

    def get_rev_list(self, head_ids):
        '''Invoke git-rev-list on the given commit_ids.'''
        command = 'git-rev-list ' + ' '.join(head_ids)
        output = self.shell_to_string(command)
        refs_here = Set([ i.strip() for i in output.split() ])
        return refs_here

    def get_pack_handle(self, refs_wanted, raw_refs_not_needed):
        '''Return a file handle + waiter streaming a git pack.'''

        refs_not_needed = self.filter_refs(raw_refs_not_needed)
        command_string = 'git-rev-list --objects '
        for ref in refs_wanted:
            command_string += '%s ' % ref
        for ref in refs_not_needed:
            command_string += '^%s ' % ref
        command_string += '| git-pack-objects --stdout'
        self.shell_to_string(command_string)
        remote_in, remote_out, wait = self.popen2(command_string)
        remote_in.close()
        return remote_out, wait

    def get_unpack_handle(self):
        '''Return a file handle + waiter for receiving a git pack.'''
        command_string = 'git-unpack-objects'
        remote_in, remote_out, wait = self.popen2(command_string)
        remote_out.close()
        return remote_in, wait

    def send_pack_via_framer(self, framer, target_ids, unneeded_ids):
        '''Send a pack via the given framer.'''
        handle, waiter = self.get_pack_handle(target_ids, unneeded_ids)
        framer.write_handle(handle)
        handle.close()
        handle.close()
        waiter()

    def import_pack_via_framer(self, framer):
        '''Import a pack from the given framer.'''
        handle, waiter = self.get_unpack_handle()
        for frame in framer.iter_stream():
            handle.write(frame)
        handle.close()
        waiter()

    def get_commit_id(self, ref_name):
        '''Return the commit_id for a given name.'''
        command_string = 'git-rev-parse %s' % ref_name
        commit_id = self.shell_to_string(command_string).strip()
        if commit_id == ref_name:
            raise CommitNotFound('not commit for "%s"' % ref_name)
        return commit_id

    def note_ref(self, upstream_name, commit_id):
        '''Note a commit id as refs/heads/[upstream_name].'''
        head_file = pjoin(self.vc_dir, 'refs', 'heads', upstream_name)
        handle = open(head_file, 'w')
        print >> handle, commit_id
        handle.close()

    def merge(self, new_head_id):
        '''Do a merge from HEAD to new_head_id.

        Do a plain checkout for new repositories.
        '''
        if self.is_new():
            command_string = 'git checkout -b master -f %s' \
                             % new_head_id
        else:
            current_head_id = self.get_commit_id('HEAD')
            command_string = "git resolve %s %s 'merge'" \
                             % (current_head_id, new_head_id)
        self.shell_to_string(command_string)

# vim:ai:et:sts=4:sw=4:tw=0:
