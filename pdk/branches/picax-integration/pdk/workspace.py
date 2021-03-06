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
import optparse
from urlparse import urlsplit
from itertools import chain
from pdk.package import Package
from pdk.progress import ConsoleProgress
from pdk.version_control import VersionControl, CommitNotFound
from pdk.cache import Cache
from pdk.channels import OutsideWorldFactory, WorldData, ChannelBackedCache
from pdk.exceptions import ConfigurationError, SemanticError, \
     CommandLineError, InputError
from pdk.util import pjoin, make_self_framer, cached_property, \
     relative_path, get_remote_file_as_string, make_ssh_framer, \
     make_fs_framer, get_remote_file
from pdk.semdiff import print_bar_separated, print_man, \
     iter_diffs, iter_diffs_meta, field_filter, filter_data
from pdk.component import ComponentDescriptor, ComponentMeta
from pdk.repogen import compile_product

# current schema level for this pdk build
schema_target = 4

class NotAWorkspaceError(ConfigurationError):
    '''A workspace op was requested on or in a non workspace directory.'''
    pass

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

def current_workspace(given_directory = None):
    """
    Locate the current workspace and return the workspace object.

    This works on the assumption/presumption that you are in a
    workspace currently.  It merely looks upward in the directory
    tree until it finds its' marker files/dirs, and then instances
    the Workspace object with that directory as its base.
    """
    if given_directory is None:
        given_directory = os.getcwd()

    directory, schema_number = find_workspace_base(given_directory)
    assert_schema_current(directory, schema_number)
    if not directory:
        raise NotAWorkspaceError("Not currently a workspace: '%s'"
                                 % given_directory)
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


class command_args(object):
    '''Represents common operations on results from optparse.'''
    def __init__(self, opts, args):
        self.opts = opts
        self.args = args

    def get_new_directory(self):
        '''Get a new directory.

        The directory must not already exist.
        '''
        new_dir = self.pop_arg('new directory')
        if os.path.exists(new_dir):
            raise SemanticError('Already exists: "%s"' % new_dir)
        return new_dir

    def get_one_reoriented_file(self, workspace):
        '''Get exactly one filename, reoriented to the workspace. '''
        if len(self.args) != 1:
            raise CommandLineError('requires a single filename')
        return workspace.reorient_filename(self.pop_arg('filename'))

    def get_reoriented_files(self, workspace, minimum = 1):
        '''Get a minimum number of filenames, reoriented to the workspace.
        '''
        if len(self.args) < minimum:
            message = 'Must provide at least %d filename.' % minimum
            raise CommandLineError(message)
        return [ workspace.reorient_filename(f) for f in self.args ]

    def pop_arg(self, description):
        '''Remove an argument from self.args.

        description is used to form more friendly error messages.
        '''
        if len(self.args) == 0:
            raise CommandLineError('required argument: %s', description)
        return self.args.pop(0)

    def assert_no_args(self):
        '''Assert that no arguments have been given.'''
        if len(self.args) != 0:
            raise CommandLineError('command takes no arguments')

class command_args_spec(object):
    '''Factory for creating command_args objects.

    The spec is a series of strings. For details of which strings are
    available read the source code to the create function.
    '''
    def __init__(self, usage, *spec):
        self.usage = usage
        self.spec = spec

    def create(self, raw_args):
        '''Create a new command_args object, processing raw_args.'''
        parser = optparse.OptionParser(usage = self.usage)
        op = parser.add_option
        for item in self.spec:
            if item == 'commit-msg':
                op('-f', '--commit-msg-file',
                   dest = 'commit_msg_file',
                   help = 'File containing a prewritten commit message.',
                   metavar = 'FILE')

                op("-m", "--commit-msg",
                   dest = "commit_msg",
                   help = "Commit message to use",
                   metavar = 'MESSAGE')

            elif item == 'channels':
                op("-c", "--channel",
                   action = "append",
                   dest = "channels",
                   type = "string",
                   help = "A channel name.")

            elif item == 'machine-readable':
                op("-m", "--machine-readable",
                   action = "store_true",
                   dest = "machine_readable",
                   default = False,
                   help = "Make the output machine readable.")

            elif item == 'no-report':
                op("-R", "--no-report",
                   action = "store_false",
                   dest = "show_report",
                   default = True,
                   help = "Don't bother showing the report.")

            elif item == 'dry-run':
                op("-n", "--dry-run",
                   action = "store_false",
                   dest = "save_component_changes",
                   default = True,
                   help = "Don't save changes after processing.")

            elif item == 'output-dest':
                op('-o', '--out-file', '--out-dest',
                   dest = 'output_dest',
                   help = "Destination for output.",
                   metavar = "DEST")

            elif item == 'show-unchanged':
                op('--show-unchanged',
                   action = "store_true",
                   dest = 'show_unchanged',
                   default = False,
                   help = "Show unchanged items in report.")

            else:
                assert False, "Unknown command line specification. '%s'" \
                       % item

        opts, args = parser.parse_args(args = raw_args)
        return command_args(opts, args)

def make_invokable(fn, *spec):
    '''Make the given function an "invokable".

    Spec strings are optional and may directly follow the function argument.

    Invokables are special because their --help options work properly
    based on the command spec and function doc string.
    '''
    def _invoke(raw_args):
        '''Actually invoke the function.'''
        doc_string = fn.__doc__.strip()
        args = command_args_spec(doc_string, *spec).create(raw_args)
        fn(args)
    return _invoke

# For external linkage
def create(args):
    """usage: pdk workspace create DIRECTORY

    Creates a new workspace for pdk.

    The directory should not exist.
    """
    # Friends don't let friends nest workspaces.
    if currently_in_a_workspace():
        raise SemanticError(
            "%s is Already in a workspace"
            % os.getcwd()
            )

    new_workspace_dir = args.get_new_directory()
    if not args:
        raise CommandLineError("requires an argument")
    create_workspace(new_workspace_dir)

create = make_invokable(create)

def repogen(args):
    """usage: pdk repogen COMPONENT

    Generate a file-system repository for a linux product.
    """
    ws = current_workspace()
    product_file = args.get_one_reoriented_file(ws)
    get_desc = ws.get_component_descriptor
    if args.opts.output_dest:
        repo_dir = pjoin(ws.location,
                         ws.reorient_filename(args.opts.output_dest))
    else:
        repo_dir = pjoin(ws.location, 'repo')
    compile_product(product_file, ws.cache, repo_dir, get_desc)

repogen = make_invokable(repogen, 'output-dest')

def add(args):
    """usage: pdk add FILES

    Put files under version control, scheduling it for addition to the
    repository.  It will be added on the next commit.
    """
    ws = current_workspace()
    files = args.get_reoriented_files(ws, 0)
    return ws.add(files)

add = make_invokable(add)

def remove(args):
    """usage: pdk remove FILES

    Remove files from version control. The removal is essentially
    noted in the changeset of the next commit.
    """
    ws = current_workspace()
    files = args.get_reoriented_files(ws, 0)
    return ws.remove(files)

remove = make_invokable(remove)

def cat(args):
    """usage: pdk cat FILE

    Output the content of specified file from the HEAD commit in
    version control.
    """
    ws = current_workspace()
    name = args.get_one_reoriented_file(ws)
    result = ws.cat(name).read().strip()
    print >> sys.stdout, result
    return result

cat = make_invokable(cat)

def revert(args):
    """usage: pdk revert FILES

    Restore pristine copies of files from the HEAD commit in version
    control.
    """
    ws = current_workspace()
    files = args.get_reoriented_files(ws, 1)
    return ws.revert(files)

revert = make_invokable(revert)

def commit(args):
    """usage: pdk commit [options] FILES

    Commit changes to files in the work area.

    If FILES are present, the scope of the commit is limited to these
    files. If it is empty, all commit-worthy files are committed.

    Naming files which have not been added will work and can be
    considered a shortcut around the pdk add command.

    If no commit message is provided through options, $EDITOR will be
    invoked to obtain a commit message.
    """
    ws = current_workspace()
    files = args.get_reoriented_files(ws, 0)
    ws.commit(args.opts.commit_msg_file, args.opts.commit_msg, files)

commit = make_invokable(commit, 'commit-msg')

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

def status(dummy):
    """
    status: Show the current version control status of files in this
    work area.
    """
    ws = current_workspace()
    ws.status()

def log(args):
    """
    log: Show version control history.
    """
    ws = current_workspace()
    ws.log(args)

def pull(args):
    """usage: pdk pull REMOTE_NAME

    Bring version control info from a remote workspace into this
    workspace. Bring working copy up-to-date with remote HEAD
    revision.

    The remote name should be configured as a channel of type
    'source' in the workspace channels file.
    """
    remote_path = args.pop_arg('remote workspace name')
    local = current_workspace()
    local.pull(remote_path)

pull = make_invokable(pull)

# Externally-exposed function -- pdk channel update
def world_update(args):
    '''usage: pdk channel update

    Reads channel configuration and downloads all metadata.
    '''
    args.assert_no_args()
    workspace = current_workspace()
    workspace.world_update()

world_update = make_invokable(world_update)

def push(args):
    """usage: pdk push REMOTE_NAME

    Publish the HEAD of this workspace to another workspace.

    This command also pushes the cache. The remote HEAD must appear in
    the history of this HEAD or the remote workspace will reject the
    push.

    The remote name should be configured as a channel of type
    'source' in the workspace channels file.
    """
    remote_path = args.pop_arg('remote workspace name')
    local = current_workspace()
    local.push(remote_path)

push = make_invokable(push)

def semdiff(args):
    """usage: pdk semdiff [options] COMPONENT [COMPONENT]

    Return a report containing meaningful component changes.

    Works against version control, two arbitrary components, or a
    component and a set of channels.

    Caveat: When comparing against version control, only the named
    component is retrieved from version control. Sub components are
    found in the work area. This could affect metadata differences.
    """
    workspace = current_workspace()
    cache = ChannelBackedCache(workspace.world, workspace.cache)
    files = args.get_reoriented_files(workspace)

    if args.opts.machine_readable:
        printer = print_bar_separated
    else:
        printer = print_man

    get_desc = workspace.get_component_descriptor
    if args.opts.channels:
        ref = files[0]
        old_meta = ComponentMeta()
        desc = get_desc(ref)
        component = desc.load(old_meta, cache)
        old_package_list = component.direct_packages
        world_index = workspace.world.get_limited_index(args.opts.channels)
        new_package_list = [ i.package
                             for i in world_index.get_all_candidates() ]
        new_meta = {}
    elif len(files) == 1:
        ref = files[0]
        # Get old
        old_meta = ComponentMeta()
        old_desc = get_desc(ref, workspace.vc.cat(ref))
        old_component = old_desc.load(old_meta, cache)
        old_package_list = old_component.direct_packages
        # Get new
        new_meta = ComponentMeta()
        new_desc = get_desc(ref)
        new_component = new_desc.load(new_meta, cache)
        new_package_list = new_component.direct_packages
    elif len(files) == 2:
        ref = files[1]
        # get old
        old_meta = ComponentMeta()
        old_desc = get_desc(old_meta, files[0])
        old_component = old_desc.load(old_meta, cache)
        old_package_list = old_component.direct_packages
        # Get new
        new_meta = ComponentMeta()
        new_desc = get_desc(files[1])
        new_component = new_desc.load(new_meta, cache)
        new_package_list = new_component.direct_packages
    else:
        raise CommandLineError("Argument list is invalid")

    diffs = iter_diffs(old_package_list, new_package_list)
    diffs_meta = iter_diffs_meta(old_meta, new_meta)
    data = filter_data(chain(diffs, diffs_meta), args.opts.show_unchanged)
    printer(ref, data)

semdiff = make_invokable(semdiff, 'machine-readable', 'channels',
                         'show-unchanged')

def dumpmeta(args):
    """usgage: pdk dumpmeta COMPONENTS

    Prints all component metadata to standard out.
    """
    workspace = current_workspace()
    get_desc = workspace.get_component_descriptor
    cache = workspace.cache
    component_refs = args.get_reoriented_files(workspace)
    for component_ref in component_refs:
        meta = ComponentMeta()
        get_desc(component_ref).load(meta, cache)
        for item in meta:
            predicates = meta[item]
            for key, value in predicates.iteritems():
                if key in field_filter:
                    continue
                if isinstance(item, Package):
                    ref = item.blob_id
                    name = item.name
                    type_string = item.type
                else:
                    ref = item.ref
                    name = ''
                    type_string = 'component'
                print '|'.join([ref, type_string, name, key, str(value)])

dumpmeta = make_invokable(dumpmeta)

def run_resolve(args, assert_resolved, abstract_constraint):
    '''Take care of details of running descriptor.resolve.

    raw_args - passed from command handlers
    do_assert - warn if any references are not resolved
    show_report - show a human readable report of what was done
    dry_run - do not save the component after we are finished
    '''
    workspace = current_workspace()
    get_desc = workspace.get_component_descriptor
    component_names = args.get_reoriented_files(workspace)
    os.chdir(workspace.location)
    for component_name in component_names:
        descriptor = get_desc(component_name)
        channel_names = args.opts.channels
        world_index = workspace.world.get_limited_index(channel_names)
        descriptor.resolve(world_index, abstract_constraint)
        descriptor.setify_child_references()

        if assert_resolved:
            descriptor._assert_resolved()

        if args.opts.show_report:
            if args.opts.machine_readable:
                printer = print_bar_separated
            else:
                printer = print_man

            descriptor.diff_self(workspace, printer,
                                 args.opts.show_unchanged)

        if args.opts.save_component_changes:
            descriptor.write()

def resolve(args):
    """usage: pdk resolve COMPONENTS

    Resolves abstract package references.

    If the command succeeds, the component will be modified in
    place. Abstract package references will be populated with concrete
    references.

    If no channel names are given, resolve uses all channels to
    resolve references.

    A warning is given if any unresolved references remain.
    """
    run_resolve(args, True, True)

resolve = make_invokable(resolve, 'machine-readable', 'no-report',
                         'dry-run', 'channels', 'show-unchanged')

def upgrade(args):
    """usage: pdk upgrade COMPONENTS

    Upgrades concrete package references by package version.

    If the command succeeds, the component will be modified in
    place. Package references with concrete children will be examined
    to see if channels can provide newer packages. If this is the
    case, all concrete refrences which are grouped by an abstract
    reference are removed and replaced with references to newer
    pacakges.

    If no channel names are given, resolve uses all channels to
    resolve references.
    """
    run_resolve(args, False, False)

upgrade = make_invokable(upgrade, 'machine-readable', 'no-report',
                         'dry-run', 'channels', 'show-unchanged')

def download(args):
    """usage: pdk download FILES

    Acquire copies of the package files needed by the descriptor
    FILES. The needed package files will be located based on the
    package indexes of configured channels.
    """
    workspace = current_workspace()
    get_desc = workspace.get_component_descriptor
    component_names = args.get_reoriented_files(workspace)
    for component_name in component_names:
        descriptor = get_desc(component_name)
        descriptor.download(workspace)

download = make_invokable(download)

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

    def reorient_filename(self, filename):
        '''Return the given path relative to self.location.'''
        return relative_path(self.location, filename)

    def add(self, files):
        """
        Add an item to local version control
        """
        return self.vc.add(files)

    def remove(self, files):
        """
        Remove an item from local version control
        """
        return self.vc.remove(files)

    def cat(self, name):
        """
        Remove an item from local version control
        """
        return self.vc.cat(name)

    def revert(self, files):
        """
        Remove an item from local version control
        """
        return self.vc.revert(files)

    def commit(self, commit_msg_file, commit_msg, files):
        """
        Commit changes to version control
        """
        self.vc.commit(commit_msg_file, commit_msg, files)
        self.cache.write_index()

    def update(self):
        """
        Get latest changes from version control
        """
        self.vc.update()

    def status(self):
        """
        Show version control status of files in work area.
        """
        self.vc.status(self.config_dir)

    def log(self, limits):
        """
        Show version control history.
        """
        self.vc.log(limits)

    def pull(self, upstream_name):
        """
        Get latest changes from version control
        """
        conveyor = Conveyor(self, upstream_name)
        conveyor.pull()

    def push(self, upstream_name):
        """
        Get push local history to a remote workspace.
        """
        conveyor = Conveyor(self, upstream_name)
        conveyor.push()

    def world_update(self):
        """Update remote index files for outside world."""
        self.world.fetch_world_data()

    def acquire(self, blob_ids):
        '''Get cache loaders and use them to download package files.'''
        for loader in self.world.get_cache_loaders(blob_ids):
            loader.load(self.cache)

    def get_component_descriptor(self, oriented_name, handle = None):
        '''Using oriented_name, create a new component descriptor object.'''
        if not handle:
            full_path = pjoin(self.location, oriented_name)
            if os.path.exists(full_path):
                handle = open(full_path)
            else:
                message = 'Component descriptor "%s" does not exist.' \
                          % oriented_name
                raise InputError(message)
        return ComponentDescriptor(oriented_name, handle,
                                   self.get_component_descriptor)

class Net(object):
    '''Encapsulates the details of most framer conversations.

    send_* methods correspond to handle_* methods on remote processes.
    (mostly)
    '''
    protocol_version = '0'

    def __init__(self, framer, local_workspace):
        self.framer = framer
        self.ws = local_workspace

    def verify_protocol(self):
        '''Verify that the remote can speak our protocol version.'''
        self.framer.write_stream(['verify-protocol'])
        self.framer.write_stream(self.protocol_version)
        frame = self.framer.read_frame()
        if frame == 'protocol-ok':
            pass
        elif frame == 'error':
            message = self.framer.read_frame()
            raise SemanticError, message
        self.framer.assert_end_of_stream()

    def handle_verify_protocol(self):
        '''Handle protocl verification'''
        self.framer.assert_frame(self.protocol_version)
        self.framer.assert_end_of_stream()
        self.framer.write_stream(['protocol-ok'])

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
        op_status = self.framer.read_frame()
        if op_status == 'ok':
            pass
        elif op_status == 'out-of-date':
            raise SemanticError('Out of date. Run pdk pull and try again.')
        else:
            assert False, 'Unknown status: %s' % op_status

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
            self.ws.vc.merge(head_id, True)
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
        # first figure out everything we need to do
        needed_blobs = []
        for blob_id in cache.iter_sha1_ids():
            if blob_id in remote_blob_ids:
                continue
            needed_blobs.append((blob_id, cache.get_size(blob_id)))
        total_size = 0
        for dummy, size in needed_blobs:
            total_size += size

        progress = ConsoleProgress('Pushing blobs to remote...')
        progress.start()
        pushed_size = 0
        for blob_id, size in needed_blobs:
            cache.send_via_framer(blob_id, self.framer)
            pushed_size += size
            progress.write_bar(total_size, pushed_size)
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
                        'pull-blobs': self.handle_pull_blobs,
                        'verify-protocol': self.handle_verify_protocol, }

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
    try:
        local_workspace = current_workspace(args[0])
    except NotAWorkspaceError, e:
        framer.write_stream(['error', str(e)])
        return
    net = Net(framer, local_workspace)
    net.listen_loop()

class Conveyor(object):
    '''Adapter for dealing with widely divergent pull/push strategies.

    Pulling over anonymous https is very different from pulling over
    a framer either on the local machine or via ssh.

    Currently there is only one way to push.

    channel       - the channel object
    vc            - A version control object.
    upstream_name - The name associated with the workspace in channels.xml.

    Call self.pull() to actually initiate a pull.
    Call self.push() to actually initiate a push.
    '''
    def __init__(self, workspace, upstream_name):
        self.workspace = workspace
        self.world = self.workspace.world
        self.channel = self.world.get_workspace_section(upstream_name)
        self.full_path = self.channel.full_path
        self.vc = self.workspace.vc
        self.upstream_name = upstream_name

        parts = urlsplit(self.full_path)
        if parts[0] == 'http':
            self.pull = self._anon_http_pull_strategy
            self.push = None
        else:
            self.pull = self._framer_pull_strategy
            self.push = self._framer_push_strategy

    def _get_framer(self):
        '''Get a framer suitable for communicating with this workspace.'''
        path = self.full_path
        parts = urlsplit(path)
        if parts[0] == 'file' and parts[1]:
            framer = make_ssh_framer(parts[1], parts[2])
        else:
            framer = make_fs_framer(path)
        return framer

    def _anon_http_pull_strategy(self):
        '''Run a pull.

        This method is run when the path indicates that we need to do
        an anonymous http pull.
        '''
        try:
            schema_url = self.full_path + '/etc/schema'
            schema_number = \
                int(get_remote_file_as_string(schema_url).strip())
        except ValueError:
            message = "Remote workspace has invalid schema number."
            raise SemanticError, message
        if schema_number != schema_target:
            raise SemanticError, 'Workspace schema mismatch with remote.'

        blob_list_url = self.full_path + '/etc/cache/blob_list.gz'
        get_remote_file(blob_list_url, self.channel.channel_file)

        git_path = self.full_path + '/etc/git'
        self.vc.direct_pull(git_path, self.upstream_name)

    def _framer_pull_strategy(self):
        '''Run a pull.

        This method is run when the path indicates that we need to
        communicate with a remote process over pipes.
        '''
        local_commit_ids = self.vc.get_all_refs()
        framer = self._get_framer()

        net = Net(framer, self.workspace)
        net.verify_protocol()
        new_head_id = net.send_pull_pack(local_commit_ids)
        self.vc.import_pack_via_framer(framer)
        self.vc.note_ref(self.upstream_name, new_head_id)
        self.vc.merge(self.upstream_name)
        net.send_pull_blob_list(self.channel)
        net.send_done()
        framer.close()

    def _framer_push_strategy(self):
        '''Run a push.

        This method is run when the path indicates that we need to
        communicate with a remote process over pipes.
        '''
        framer = self._get_framer()
        head_id = self.vc.get_commit_id('HEAD')
        try:
            remote_head = self.vc.get_commit_id(self.upstream_name)
            remote_commit_ids = self.vc.get_rev_list([remote_head])
        except CommitNotFound:
            remote_commit_ids = []
        raw_package_info = self.world.all_package_info.raw_package_info
        remote_blob_ids = [ r.blob_id for r in raw_package_info
                            if r.section_name == self.upstream_name ]
        net = Net(framer, self.workspace)
        net.verify_protocol()
        net.send_push_blobs(remote_blob_ids)
        try:
            net.send_push_pack(head_id, remote_commit_ids)
        finally:
            net.send_done()
        framer.close()


# vim:ai:et:sts=4:sw=4:tw=0:
