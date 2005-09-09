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

def create(workspace):
    '''Create the sources directory in the workspace.'''
    source = RemoteSources(workspace)
    source.create()
    return source

class RemoteSources(object):
    '''Represents the list of remote workspaces from which we can update.'''
    def __init__(self, workspace):
        self.workspace = workspace
        self.vc = workspace.version_control()
        self.vc_dir = os.path.join(workspace.location, 'VC')
        self.sources_dir = os.path.join(workspace.location, 'sources')

    def create(self):
        '''Create the symlink to the internal vc dir. (i.e. .git/remotes)'''
        os.symlink(self.vc.remotes_dir, self.sources_dir)

    def subscribe(self, remote_url, name):
        '''Create the file representing an individual subscription.'''
        source_file = os.path.join(self.sources_dir, name)
        open(source_file, 'w').write("URL: %s\n" % remote_url)

# vim:ai:et:sts=4:sw=4:tw=0:
