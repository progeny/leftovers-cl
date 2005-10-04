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
from pdk.version_control import VersionControl, CommitNotFound
from pdk.cache import Cache
from pdk.channels import OutsideWorldFactory, WorldData
from pdk.exceptions import ConfigurationError, SemanticError, \
     CommandLineError
from pdk.util import pjoin, make_self_framer

# current schema level for this pdk build
schema_target = 4

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
        migrate(None)
        return

    if schema_number == 3:
        sources_dir = pjoin('etc', 'sources')
        if os.path.exists(sources_dir):
            os.remove(sources_dir)
        open(pjoin('etc', 'schema'), 'w').write('4\n')
        migrate(None)
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

def pull(args):
    """
    pull: Bring changes from a remote workspace into this workspace.
    usage: pull [upstream-name]

    Bring working copy up-to-date with HEAD rev.

    """
    if len(args) != 1:
        raise CommandLineError('requires a remote workspace path')
    remote_path = args[0]
    local = current_workspace()
    local.pull(remote_path)

# Externally-exposed function -- pdk channel update
def world_update(args):
    '''Read channels and sources and update our map of the outside world.
    '''

    if len(args) > 0:
        raise CommandLineError, 'update takes no arguments'
    workspace = current_workspace()
    workspace.world_update()

def push(args):
    """Publish the HEAD of this workspace to another workspace.

    This command also pushes the cache. The remote HEAD must appear in
    the history of this HEAD or the remote workspace will reject the
    push.

    This command takes a remote workspace path as an argument.
    """
    if len(args) != 1:
        raise CommandLineError('requires a remote workspace path')
    remote_path = args[0]
    local = current_workspace()
    local.push(remote_path)

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
        world_data = WorldData.load_from_stored(self.channel_data_source)
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

    def pull(self, upstream_name):
        """
        Get latest changes from version control
        """
        section = self.world.get_workspace_section(upstream_name)
        framer = section.get_framer()

        local_commit_ids = self.vc.get_all_refs()
        net = Net(framer, self)
        new_head_id = net.send_pull_pack(local_commit_ids)
        self.vc.import_pack_via_framer(framer)
        self.vc.note_ref(upstream_name, new_head_id)
        self.vc.merge(upstream_name)
        net.send_pull_blob_list(section)
        net.send_done()
        framer.close()

    def push(self, upstream_name):
        """
        Get latest changes from version control
        """
        section = self.world.get_workspace_section(upstream_name)
        framer = section.get_framer()
        head_id = self.vc.get_commit_id('HEAD')
        try:
            remote_head = self.vc.get_commit_id(upstream_name)
            remote_commit_ids = self.vc.get_rev_list([remote_head])
        except CommitNotFound:
            remote_commit_ids = []
        section = self.world.get_workspace_section(upstream_name)
        remote_blob_ids = section.cache_adapter.blob_ids
        net = Net(framer, self)
        net.send_push_blobs(remote_blob_ids)
        try:
            net.send_push_pack(head_id, remote_commit_ids)
        finally:
            net.send_done()
        framer.close()

    def world_update(self):
        """Update remote index files for outside world."""
        self.world.fetch_world_data()

    def acquire(self, blob_ids):
        '''Get cache adapters and use them to download package files.'''
        for adapter in self.world.get_cache_adapters(blob_ids):
            framer = adapter.adapt()
            self.cache.import_from_framer(framer)

class Net(object):
    '''Encapsulates the details of most framer conversations.

    send_* methods correspond to handle_* methods on remote processes.
    (mostly)
    '''
    def __init__(self, framer, local_workspace):
        self.framer = framer
        self.ws = local_workspace

    def send_done(self):
        '''Indicate that we are done speaking with the remote process.'''
        self.framer.write_stream(['done'])

    def send_push_pack(self, head_id, remote_commit_ids):
        '''Intitiate pushing of a pack file.

        head_id is where the pack starts.
        remote_commit_ids are what we do not need to send.
        '''
        self.framer.write_stream(['push-pack'])
        self.framer.write_stream(['HEAD', head_id])
        self.ws.vc.send_pack_via_framer(self.framer, [head_id],
                                        remote_commit_ids)
        self.framer.assert_frame('status')
        status = self.framer.read_frame()
        if status == 'ok':
            pass
        elif status == 'out-of-date':
            raise SemanticError('Out of date. Run pdk pull and try again.')
        else:
            assert False, 'Unknown status: %s' % status

    def handle_push_pack(self):
        '''Receive a pack.

        Send back an "out-of-date" status if the pack does not include
        the current HEAD in its history.
        '''
        self.framer.assert_frame('HEAD')
        head_id = self.framer.read_frame()
        self.framer.assert_end_of_stream()

        self.ws.vc.import_pack_via_framer(self.framer)
        if self.ws.vc.is_valid_new_head(head_id):
            self.ws.vc.merge(head_id)
            self.framer.write_stream(['status', 'ok'])
        else:
            self.framer.write_stream(['status', 'out-of-date'])

    def send_pull_pack(self, local_commit_ids):
        '''Initiate pulling a pack file.

        local_commit_ids are ids which do not need to be sent.
        '''
        self.framer.write_stream(['pull-pack'])
        self.framer.write_stream(local_commit_ids)

        self.framer.assert_frame('HEAD')
        new_head_id = self.framer.read_frame()
        self.framer.assert_end_of_stream()
        return new_head_id

    def handle_pull_pack(self):
        '''Handle a pull pack request.'''
        remote_commit_ids = list(self.framer.iter_stream())
        head_id = self.ws.vc.get_commit_id('HEAD')
        self.framer.write_stream(['HEAD', head_id])
        self.ws.vc.send_pack_via_framer(self.framer, [head_id],
                                     remote_commit_ids)

    def send_pull_blob_list(self, section):
        '''Initiate pulling the remote blob_list.'''
        self.framer.write_stream(['pull-blob-list'])
        handle = open(section.channel_file, 'w')
        for frame in self.framer.iter_stream():
            handle.write(frame)
        handle.close()

    def handle_pull_blob_list(self):
        '''Handle a pull blob list request.'''
        index_handle = open(self.ws.cache.get_index_file())
        self.framer.write_handle(index_handle)
        index_handle.close()

    def handle_pull_blobs(self):
        '''Handle a pull blobs request.'''
        blob_ids = list(self.framer.iter_stream())
        for blob_id in blob_ids:
            self.ws.cache.send_via_framer(blob_id, self.framer)
        self.framer.write_stream(['done'])

    def send_push_blobs(self, remote_blob_ids):
        '''Intitiate pushing blobs.'''
        self.framer.write_stream(['push-blobs'])
        cache = self.ws.cache
        for blob_id in cache.iter_sha1_ids():
            if blob_id in remote_blob_ids:
                continue
            cache.send_via_framer(blob_id, self.framer)
        self.framer.write_stream(['done'])

    def handle_push_blobs(self):
        '''Handle a push blobs request.'''
        cache = self.ws.cache
        cache.import_from_framer(self.framer)
        cache.write_index()

    def listen_loop(self):
        '''Start an "event loop" for handling requests.

        Terminates on "done".
        '''
        handler_map = { 'push-pack': self.handle_push_pack,
                        'push-blobs': self.handle_push_blobs,
                        'pull-pack': self.handle_pull_pack,
                        'pull-blob-list': self.handle_pull_blob_list,
                        'pull-blobs': self.handle_pull_blobs, }

        while 1:
            first = self.framer.read_frame()
            if first == 'done':
                break
            self.framer.assert_end_of_stream()
            handler_map[first]()

def listen(args):
    '''Start an event loop for handling requests via standard in and out.

    Not intended to be invoked by users.
    '''
    if len(args) != 1:
        raise CommandLineError('requires a workspace path')
    framer = make_self_framer()
    local_workspace = _Workspace(args[0])
    net = Net(framer, local_workspace)
    net.listen_loop()

def adapt(args):
    '''Start an event loop for handling direct download requests.

    Not intended to be invoked by users.
    '''
    if len(args) != 0:
        raise CommandLineError('no arguments allowed')
    framer = make_self_framer()
    workspace = current_workspace()

    downloads = []
    while 1:
        first = framer.read_frame()
        if first == 'end-adapt':
            break
        blob_id = first
        url = framer.read_frame()
        downloads.append((blob_id, url))
    framer.assert_end_of_stream()

    for blob_id, url in downloads:
        from pdk.channels import FileLocator
        locator = FileLocator(url, None, blob_id)
        workspace.cache.import_file(locator)
    framer.write_stream(['done'])

# vim:ai:et:sts=4:sw=4:tw=0:
