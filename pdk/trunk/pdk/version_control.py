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
import popen2
import shutil
import sys
from cStringIO import StringIO
from pdk.exceptions import IntegrityFault

## version_control
## Author:  Glen Smith
## Date:    23 June 2005
## Version: 0.0.1


####def quote(arg): 
####    """return the arg string surrounded by quotes"""
####    return "'%s'" % arg
####
####
####def flatten_args(args):
####    """return a whitespace delimited string of the args list"""
####    return " ".join( [quote(x) for x in args ])


## Command definitions ##

class VersionControlError(StandardError):
    '''Raised when there are version control problems.'''
    pass



def _shell_command(command_string, stdin = None, debug = False):
    """
    run a shell command

    stdin is text to copy to the command's stdin pipe. If null,
        nothing is sent.
    """
    process = popen2.Popen3(command_string, capturestderr = True)

    # Copy input to process, if any.
    if stdin:
        shutil.copyfileobj(stdin, process.tochild)
    process.tochild.close()

    result = process.wait()

    output = process.fromchild.read()
    if debug:
        error = process.childerr.read()
        print >> sys.stderr, '###+', command_string
        print >> sys.stderr, '###1', output
        print >> sys.stderr, '###2', error
        print >> sys.stderr, '##$!', result
    if result:
        raise VersionControlError, 'command "%s" failed' % command_string
    return output

def _cd_shell_command(path, command_string, stdin=None, debug=False):
    """Wrapper for _shell_command which includes the necessary dir
    path hijinks for version control (must execute from .git parent)

    All command parameters which are files must have already been 
    modified to be relative to the ./work directory of the project.
    """
    original_dir = os.getcwd()
    os.chdir(path)
    try:
        result = _shell_command(command_string, stdin, debug)
    finally:
        os.chdir(original_dir)
    return result


def cat(filename):
    '''Get the unchanged version of the given filename.'''
    funny_git_line = _shell_command('git-diff-files ' + filename).strip()
    if funny_git_line:
        parts = funny_git_line.split()
        git_blob_id = parts[2]
        return StringIO(_shell_command('git-cat-file blob %s'
                                       % git_blob_id))
    else:
        return open(filename)


def create(working_path):
    """Create a version control repo in the given work dir """
    # Since we're porcelain, we have to set the stage for command-line
    # tools -- saving the dir is "bread crumbs"
    starting_path = os.getcwd() 
    try:
        # If we're not there already, go to our working path
        if not starting_path.endswith(working_path):
            os.chdir(working_path)
        _shell_command('git-init-db')
    finally:
        # Follow the bread crumbs home
        os.chdir(starting_path)
    return _VersionControl(working_path)


def clone(product_URL, branch_name, local_head_name, work_dir):
    """
    call git commands to create local workspace from
    depot at upstream url
    """
    # localize a path function
    pjoin = os.path.join

    # capture starting dir
    start_dir = os.getcwd()

    # Adjust for relative paths
    if not os.path.isabs(work_dir):
        if start_dir.endswith(work_dir):
            work_dir = start_dir
        else:
            work_dir = os.path.abspath(work_dir)
    os.chdir(work_dir)
    try:
        git_path = pjoin(work_dir, '.git')

        # Get a tar file and untar it locally
        curl_source = product_URL + '/work/snap.tar'
        curl_command = 'curl -s ' + curl_source + \
                       ' | (tar Cx %s)' % git_path
        _shell_command(curl_command)

        # Make a branches directory in git
        branch_path = pjoin(git_path, 'branches')
        os.mkdir(branch_path)

        branch_filename = pjoin(branch_path, branch_name)
        branch_file = file(branch_filename, 'w')
        branch_file.write(product_URL) 
        branch_file.close()

        source = pjoin(git_path, 'HEAD')
        target = pjoin(git_path, 'refs', 'heads', local_head_name)
        shutil.copy(source, target)
        _shell_command('git-read-tree %s' % local_head_name)
        _shell_command('git-checkout-cache -a')
    finally:
        os.chdir(start_dir)


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

    def add(self, name):
        """
        Initialize version control
        """
        name = relative_path(self.work_dir, name)
        cmd = 'git-update-cache --add %s' % name
        return _cd_shell_command(self.work_dir, cmd)

    def commit(self, remark):
        """
        call git commands to commit local work
        """
        pjoin = os.path.join

        work_dir = self.work_dir
        files = _cd_shell_command(
            work_dir
            , 'git-diff-files --name-only'
            ).split()
        files = [ relative_path(work_dir, item) 
                  for item in files ]
        _cd_shell_command(
            work_dir
            , 'git-update-cache ' + ' '.join(files))

        sha1 = _cd_shell_command(work_dir, 'git-write-tree').strip()

        comment_handle = StringIO(remark)
        output = _cd_shell_command(work_dir, 'git-commit-tree ' + \
                                 sha1, comment_handle)

        filename = pjoin(work_dir, '.git/refs/heads/master')
        if os.path.exists(filename):
            the_file = file(filename, 'r')
            old_content = the_file.read().strip()
            the_file.close()
            back_filename = pjoin(
                work_dir
                , '.git'
                , 'refs'
                , 'heads'
                , old_content
                )
            os.rename(filename, back_filename)

        the_file = file(filename, 'w')
        the_file.write(str(output))
        the_file.close()


    def update(self, upstream_name):
        """
        update the version control
        """
        work_dir = self.work_dir
        original_dir = os.getcwd()
        try:
            config_file_name = 'work/.git/branches/' + upstream_name
            config_file = file(config_file_name, 'r')
            remote_URL = config_file.read().strip()
            config_file.close()

            curl_source = remote_URL + 'VC/HEAD'
            remote_commit_id = _cd_shell_command(
                work_dir
                , 'curl -s  ' + curl_source
                ).strip()

            cmd_str = 'git-http-pull -c %s %sVC/' % (
                remote_commit_id
                , remote_URL
                )
            try:
                _cd_shell_command(work_dir, cmd_str)
            except Exception, message:
                print "Message: %s" % message
                raise

            command_string = 'git-read-tree ' + remote_commit_id
            _cd_shell_command(work_dir, command_string)

            command_string = 'git-merge-cache git-merge-one-file-script -a'
            _cd_shell_command(work_dir, command_string)
        finally:
            os.chdir(original_dir)


def patch(args):
    """Perform a version control patch command"""
    file_name = args[0]
    command_string = 'git-apply ' + file_name
    _shell_command(command_string)
##    git-update-cache progeny.com/apache.xml
##    pdk commit master "Required commit remark"


#-----------------------------------------------------------------------
# Path management

def relative_path(base_dir, file_path):
    """Modify a file path to be relative to another (base) path.
    throws ValueError if file is not in the base tree.

    base_dir = any local directory path
    file_path = any relative or absolute file path under base_dir
    """
    # localize some functions
    sep = os.path.sep
    absolute = os.path.abspath

    # Make lists of the paths
    base_parts = absolute(base_dir).split(sep)
    file_parts = absolute(file_path).split(sep)

    if len(base_parts) >= len(file_parts):
        raise ValueError("%s not within %s" % (file_path, base_dir))
    
    # Bite off bits from the left, ensuring they're the same.
    while base_parts:
        base_bit = base_parts.pop(0)
        file_bit = file_parts.pop(0)
        if base_bit != file_bit:
            raise ValueError("%s not within %s" % (file_path, base_dir))

    result = os.path.join(*file_parts)

    # git commands require trailing slashes on directories. 
    if os.path.isdir(result):
        result += "/"
    return result
    


# vim:ai:et:sts=4:sw=4:tw=0:
