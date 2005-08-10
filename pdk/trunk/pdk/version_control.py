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
    """
    process = popen2.Popen3(command_string, capturestderr = True)
    if stdin:
        shutil.copyfileobj(stdin, process.tochild)
    process.tochild.close()
    result = process.wait()
    output = process.fromchild.read()
    if debug:
        error = process.childerr.read()
        print >> sys.stderr, '###+', command_string
        print >> sys.stderr, '####', output
        print >> sys.stderr, '####', error
    if result:
        raise VersionControlError, 'command "%s" failed' % command_string
    return output


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


class VersionControl(object):
    """
    Library Interface to pdk version control
    """

    def __init__(self):
        pass

    def create(self, path=None):
        """
        Initialize version control
        """
        start_path = path or os.getcwd()  # questionable, but: baby steps!
        vc_path = start_path + '/VC'
        work_path = start_path + '/work'
        os.mkdir(work_path)
        os.chdir(work_path)
        _shell_command('git-init-db')
        git_path = work_path + '/.git'
        os.symlink(git_path, vc_path)
        os.chdir(start_path)


    def clone(self, product_URL, branch_name, local_head_name):
        """
        call git commands to create local workspace from
        depot at upstream url
        """
        needs_setup = True
        if needs_setup:
            git_path = '.git/'
            _shell_command([('git-init-db')])

        curl_source = product_URL + '/work/snap.tar'
        curl_command = 'curl -s ' + curl_source + \
                       ' | (tar Cx %s)' % git_path
        _shell_command(curl_command)

        branch_path = git_path + 'branches/'
        os.mkdir(branch_path)

        branch_filename = branch_path + branch_name
        branch_file = file(branch_filename, 'w')
        branch_file.write(product_URL) 
        branch_file.close()

        source = git_path + 'HEAD'
        target = git_path + 'refs/heads/' + local_head_name
        shutil.copy(source, target)
        _shell_command('git-read-tree %s' % local_head_name)
        _shell_command('git-checkout-cache -a')


    def add(self, name):
        """
        Initialize version control
        """
        cmd = 'git-update-cache --add ' + name
        return _shell_command(cmd)


    def commit(self, head_name, remark):
        """
        call git commands to commit local work
        """
        files = _shell_command('git-diff-files --name-only').split()
        _shell_command('git-update-cache ' + ' '.join(files))
        sha1 = _shell_command('git-write-tree').strip()

        print sys.stdout, "foo1", sha1

        filename = '.git/refs/heads/' + head_name
        comment_handle = StringIO(remark)
        the_file = file(filename, 'w')
        output = _shell_command('git-commit-tree ' + sha1, comment_handle)
        the_file.write(str(output))
        the_file.close()


    def update(self, upstream_name):
        """
        update the version control
        """
        config_file_name = 'work/.git/branches/' + upstream_name
        config_file = file(config_file_name, 'r')
        remote_URL = config_file.read().strip()
        config_file.close()

        curl_source = remote_URL + 'VC/HEAD'
        remote_commit_id = _shell_command('curl -s  ' + curl_source).strip()

        os.chdir('work')
        cmd_str = 'git-http-pull -c ' + remote_commit_id + \
                  ' ' + remote_URL + 'VC/'
        _shell_command(cmd_str)

        command_string = 'git-read-tree ' + remote_commit_id
        _shell_command(command_string)

        command_string = 'git-merge-cache git-merge-one-file-script -a'
        _shell_command(command_string)
        os.chdir('..')


def patch(args):
    """Perform a version control patch command"""
    file_name = args[0]
    command_string = 'git-apply ' + file_name
    _shell_command(command_string)
##    git-update-cache progeny.com/apache.xml
##    pdk commit master "Required commit remark"


# vim:ai:et:sts=4:sw=4:tw=0:
