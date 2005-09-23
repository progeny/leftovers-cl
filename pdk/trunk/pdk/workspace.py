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
from pdk.version_control import VersionControl
from pdk.source import RemoteSources
from pdk.cache import Cache
from pdk.channels import OutsideWorldFactory, WorldData
from pdk.exceptions import ConfigurationError, SemanticError, \
     CommandLineError
from pdk.util import pjoin

# current schema level for this pdk build
schema_target = 3

def find_workspace_base(directory=None):
    """Locate the directory above the current directory, containing
    the work, cache, and svn directories.

    Returns None if a workspace is not to be found in the current path.
    """
    if directory is None:
        directory = os.getcwd()

    directory = os.path.normpath(directory)

    while True:
        schema_number = find_schema_number(directory)
        if schema_number:
            return directory, schema_number
        else:
            # no markers found. try parent.
            directory, tail = os.path.split(directory)
            # If we run out of path, quit
            if not tail:
                break

    return None, None

def current_workspace():
    """
    Locate the current workspace and return the workspace object.

    This works on the assumption/presumption that you are in a
    workspace currently.  It merely looks upward in the directory
    tree until it finds its' marker files/dirs, and then instances
    the Workspace object with that directory as its base.
    """
    directory, schema_number = find_workspace_base()
    assert_schema_current(directory, schema_number)
    if not directory:
        raise ConfigurationError("Not currently in a workspace")
    return _Workspace(directory)

def currently_in_a_workspace():
    """Determine if pwd is in a workspace"""
    directory, schema_number = find_workspace_base()
    assert_schema_current(directory, schema_number)
    return bool(schema_number)

def assert_schema_current(ws_directory, schema_number):
    """Assert that the workspace can be handled by this software."""
    if schema_number and schema_number != schema_target:
        message = "Workspace migration is required.\n" + \
                  "cd %s; pdk migrate" % os.path.abspath(ws_directory)
        raise ConfigurationError(message)

def find_schema_number(directory):
    """Try to find a schema number for the given directory.

    Returns None on failure.
    """
    schema_path = pjoin(directory, 'etc', 'schema')
    if os.path.exists(schema_path):
        schema_number = int(open(schema_path).read())
        return schema_number

    cache_dir = pjoin(directory, 'cache')
    work_dir = pjoin(directory, 'work')
    if os.path.isdir(cache_dir) and os.path.isdir(work_dir):
        return 1

    return None

def migrate(dummy):
    """Migrate the current workspace to a form supported by this software.

    Only use this command from the base of the workspace.
    """
    directory, schema_number = find_workspace_base()
    if schema_number > schema_target:
        message = 'Cannot migrate. Workspace schema newer than pdk'
        raise ConfigurationError(message)

    if directory != os.getcwd():
        message = 'Cannot migrate. Change directory to workspace base.\n' \
                  'cd %s; pdk migrate' % directory
        raise ConfigurationError(message)

    if schema_number == 1:
        os.makedirs('etc')
        os.rename(pjoin('work','.git'), pjoin('etc', 'git'))
        for item in os.listdir('work'):
            os.rename(pjoin('work', item), item)
        os.rmdir('work')
        os.rename('cache', pjoin('etc', 'cache'))
        os.rename('channels.xml', pjoin('etc', 'channels.xml'))
        if os.path.exists('sources'):
            os.remove('sources')
        os.symlink(pjoin('etc', 'git'), '.git')
        os.symlink(pjoin('git', 'remotes'), pjoin('etc', 'sources'))
        open(pjoin('etc', 'schema'), 'w').write('2\n')
        migrate(None)
        return

    if schema_number == 2:
        os.makedirs(pjoin('etc', 'channels'))
        channels_pickle = pjoin('etc', 'outside_world.cache')
        if os.path.exists(channels_pickle):
            os.remove(channels_pickle)
        open(pjoin('etc', 'schema'), 'w').write('3\n')
        return

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

    # Create empty workspace
    os.makedirs(workspace_root)
    ws = _Workspace(workspace_root)
    os.makedirs(ws.cache_dir)
    os.makedirs(ws.vc_dir)
    os.makedirs(ws.channel_dir)
    vc = ws.vc
    vc.create()
    os.symlink(pjoin('etc', 'git'), pjoin(ws.location, '.git'))
    os.symlink(pjoin('git', 'remotes'), ws.sources_dir)
    open(pjoin(ws.config_dir, 'schema'), 'w').write('%d\n' % schema_target)
    return ws


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
    if len(args) != 1:
        message = 'update_from_remote requires an upstream name.'
        raise CommandLineError(message)
    remote_name = args[0]
    ws = current_workspace()
    ws.update_from_remote(remote_name)

# Externally-exposed function -- pdk channel update
def world_update(args):
    '''Read channels and sources and update our map of the outside world.'''
    if len(args) > 0:
        raise CommandLineError, 'update takes no arguments'
    workspace = current_workspace()
    workspace.world_update()

def publish(args):
    """Publish the HEAD of this workspace to another workspace.

    This command also pushes the cache.

    This command takes a remote workspace path as an argument.
    """
    if len(args) != 1:
        raise CommandLineError('requires a remote workspace path')
    remote_path = args[0]
    local = current_workspace()
    remote_cache_path = pjoin(remote_path, 'etc', 'cache')
    local.cache.push(remote_cache_path)

    remote_vc_path = pjoin(remote_path, 'etc', 'git')
    local.vc.push(remote_vc_path)

def subscribe(args):
    """Subscribe to and initially update from a remote workspace.

    This command takes a remote workspace and a symbolic name as
    arguments. The name will be used as shorthand for the remote workspace
    in future invocations.
    """
    if len(args) != 2:
        raise CommandLineError('requires a remote workspace path and name')
    remote_path, name = args
    local = current_workspace()
    local_source = RemoteSources(local)
    remote_vc_path = os.path.join(remote_path, 'etc', 'git')
    local_source.subscribe(remote_vc_path, name)
    local.vc.update_from_remote(name)
    world_update([])


def cached_property(prop_name, create_fn):
    """Make a lazy property getter that memoizes it's value.

    The prop_name is used to create an internal symbol. When debugging
    the name should be visible so it should normally match the user
    visible property name.

    The create_fn should point to a private function which returns a
    new object. The same object will be used on successive calls to
    the property getter.

    The doc string of create_fn will be used as the property's doc string.

    Usage is simlar to the built in property function.

    name = cached_value('name', __create_name)
    # where __create_name is a function returning some object
    """
    private_name = '__' + prop_name
    def _get_property(self):
        '''Takes care of property getting details.

        Memoizes the result of create_fn.
        '''
        if hasattr(self, private_name):
            value = getattr(self, private_name)
        else:
            value = None
        if not value:
            value = create_fn(self)
            setattr(self, private_name, value)
        return value
    return property(_get_property, doc = create_fn.__doc__)

class _Workspace(object):
    """
    Library interface to pdk workspace

    Provides attributes for finding common workspace files and directories,
    as well as takes care of lazily creating related objects.

    Functions which require coordination of channels, cache, and
    version control may be found here.
    """
    def __init__(self, directory):
        self.location = os.path.abspath(directory)
        self.config_dir = pjoin(self.location, 'etc')
        self.vc_dir = pjoin(self.config_dir, 'git')
        self.cache_dir = pjoin(self.config_dir,'cache')

        self.channel_data_source = pjoin(self.config_dir, 'channels.xml')
        self.channel_dir = pjoin(self.config_dir, 'channels')
        self.outside_world_store = pjoin(self.config_dir,
                                         'outside_world.cache')

        # actually a symlink to etc/git/remotes
        self.sources_dir = pjoin(self.config_dir, 'sources')

    def __create_cache(self):
        """The cache for this workspace."""
        return Cache(self.cache_dir)
    cache = cached_property('cache', __create_cache)

    def __create_vc(self):
        """The version contorl object for this workspace."""
        return VersionControl(self.location, self.vc_dir)
    vc = cached_property('vc', __create_vc)

    def __create_world(self):
        """Get the outside world object for this workspace."""
        world_data = WorldData.load_from_stored(self.channel_data_source,
                                                self.sources_dir)
        factory = OutsideWorldFactory(world_data, self.channel_dir)
        world = factory.create()
        return world
    world = cached_property('world', __create_world)
    channels = world

    def add(self, name):
        """
        Add an item to local version control
        """
        return self.vc.add(name)

    def remove(self, name):
        """
        Remove an item from local version control
        """
        return self.vc.remove(name)

    def cat(self, name):
        """
        Remove an item from local version control
        """
        return self.vc.cat(name)

    def revert(self, name):
        """
        Remove an item from local version control
        """
        return self.vc.revert(name)

    def commit(self, remark):
        """
        Commit changes to version control
        """
        self.vc.commit(remark)
        self.cache.write_index()

    def update(self):
        """
        Get latest changes from version control
        """
        self.vc.update()

    def update_from_remote(self, upstream_name):
        """
        Get latest changes from version control
        """
        self.vc.update_from_remote(upstream_name)

    def world_update(self):
        """Update remote index files for outside world."""
        self.world.fetch_world_data()


# vim:ai:et:sts=4:sw=4:tw=0:
