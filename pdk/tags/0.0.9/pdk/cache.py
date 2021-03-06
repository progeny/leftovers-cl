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
cache.py

Manage a cache of packages and other files, all for use
when referenced by component descriptors.

Cache is indexed by 'blob', which is currently an sha1 
checksum.

Cache contains .header files.
"""

__revision__ = "$Progeny$"

import sys
import os
import os.path
import re
from stat import ST_INO, ST_SIZE
from itertools import chain
import sha
import md5
import gzip
import pycurl
from shutil import copy2
from urlparse import urlparse
from cStringIO import StringIO
from tempfile import mkstemp
from pdk.package import get_package_type
from pdk.util import ensure_directory_exists, gen_fragments, \
     gen_file_fragments, make_path_to, get_remote_file
from pdk.progress import ConsoleProgress, CurlAdapter
from pdk.exceptions import SemanticError, ConfigurationError
from pdk.channels import FileLocator

# Debugging aids
import pdk.log

log = pdk.log.get_logger()

def calculate_checksums(file_path):
    """Calculate both sha-1 and md5 checksums for a file, returned 
    as blob_ids
    """
    readsize = (1024 * 16)
    md5_calc = md5.new()
    sha1_calc = sha.new()
    input_file = open(file_path)
    while True:
        block = input_file.read(readsize)
        if not block:
            break
        md5_calc.update(block)
        sha1_calc.update(block)
    input_file.close()
    return 'sha-1:' + sha1_calc.hexdigest(), \
           'md5:' + md5_calc.hexdigest()

class CacheImportError(SemanticError):
    """Generic error for trouble importing to cache"""
    pass

########################################################################
class SimpleCache(object):
    """A moderately dumb data structure representing a physical cache
    directory on disk.

    Special capabilities are:
        1) the naming algorithm for file paths
        2) Checksumming & linking of contents by md5/sha1
        3) Awareness and use of a backing cache
    """

    def __init__(self, cache_path):
        self.path = os.path.abspath(cache_path)
        if os.path.exists(cache_path) and not os.path.isdir(cache_path):
            raise ConfigurationError("%s is not a directory path"
                                     % cache_path)
        # Check for a backing cache
        backing_path = os.path.join(cache_path, '.backing')
        if os.path.exists(backing_path):
            self.backing = SimpleCache(backing_path)
        else:
            self.backing = None

    def make_relative_filename(self, filename):
        """Calculate where the file should exist within the cache"""
        filename = os.path.split(filename)[1] or filename
        dirpath = '.'
        if ':' in filename:
            # md5 or sha-1 sum
            scheme, name = filename.split(':')
            dirpath = os.path.join(scheme, name[:2])
        # Note: else path is just ./filename
        return os.path.join(dirpath, filename)

    def file_path(self, filename):
        """Calculate the full file path (not absolute) for a file"""
        return os.path.join(
            self.path
            , self.make_relative_filename(filename)
            )

    def __contains__(self, filepath):
        """Determine if the cache already contains a file"""
        result = False
        if filepath and not os.path.basename(filepath).startswith('.'):
            local_path =  self.file_path(filepath)
            result = os.path.exists(local_path)
        return result

    def import_file(self, locator):
        '''Download and incorporate a potentially remote source.

        locator - A FileLocator

        If the locator has a blob_id, it is used to verify the correctness
        of the acquired file. If the blob_id is missing, the file is not
        verified.
        '''
        local_filename = self.make_download_filename()
        try:
            parts = [ p for p in (locator.base_uri, locator.filename) if p ]
            full_url = '/'.join(parts)
            parts = urlparse(full_url)
            scheme = parts[0]
            if scheme in ('file', ''):
                source_file = parts[2]
                try:
                    copy2(source_file, local_filename)
                    self.umask_permissions(local_filename)

                except IOError, e:
                    if e.errno == 2 and os.path.exists(local_filename):
                        raise CacheImportError('%s not found' % full_url)
                    else:
                        raise
            else:
                try:
                    get_remote_file(full_url, local_filename)
                except pycurl.error, msg:
                    raise CacheImportError('%s, %s' % (msg, full_url))
            self.incorporate_file(local_filename, locator.blob_id)
        finally:
            if os.path.exists(local_filename):
                os.unlink(local_filename)

    def _add_links(self, source, blob_ids):
        '''Create visible links to the blob contained in source.

        Assume the blob_ids are correct.
        '''
        seed = self.make_download_filename()
        try:
            # optimization opportunity
            # we could attempt linking directly from source
            # to visible link to save on a copy here.
            copy2(source, seed)
            for blob_id in blob_ids:
                filename = self.file_path(blob_id)
                if os.path.exists(filename):
                    continue
                make_path_to(filename)
                os.link(seed, filename)
        finally:
            os.unlink(seed)

    def umask_permissions(self, filename):
        '''Set the filename permissions according to umask.'''
        current_umask = os.umask(0)
        os.umask(current_umask)
        new_mode = 0666 & ~current_umask
        os.chmod(filename, new_mode)

    def make_download_filename(self):
        """Create a pathname convenient for creating files for 
        later linkage into the cache.
        """

        # mkstemp actually creates the file, so we must enusre this can
        # succeed.
        ensure_directory_exists(self.path)
        temp_fd, temp_fname = mkstemp('.partial', '.', self.path)
        os.close(temp_fd)

        self.umask_permissions(temp_fname)

        return temp_fname

    def incorporate_file(self, filepath, blob_id):
        """Places a temp file in its final cache location, 
        by md5 and sha1, and unlinks the original filepath.
        """
        # Link it according to the given blob ids - note: does
        # not affect backing cache
        if self.backing:
            blob_ids = self.backing.incorporate_file(filepath, blob_id)
        else:
            blob_ids = calculate_checksums(filepath)
            if blob_id:
                if not blob_id in blob_ids:
                    message = 'Checksum mismatch: %s vs. %s.' \
                              % (blob_id, str(blob_ids))
                    raise CacheImportError(message)

        self._add_links(filepath, blob_ids)
        return blob_ids

    def __iter__(self):
        for record in os.walk(self.path):
            filenames = record[2] # (dir, subdirs, filename)
            for filename in filenames:
                yield filename

    def get_inode(self, blob_id):
        """Return the inode of a file given blob_id"""
        filepath = self.file_path(blob_id)
        return os.stat(filepath)[ST_INO]

    def write_index(self):
        """Write an index file describing the contents of the cache."""
        index_file = os.path.join(self.path, 'blob_list.gz')
        handle = gzip.open(index_file, 'w')
        regex = re.compile('(sha-1:|md5:)[a-fA-F0-9]+$')
        for filename in self:
            if regex.match(filename):
                path = self.make_relative_filename(filename)
                handle.write('%s %s\n' % (filename, path))
        handle.flush()
        handle.close()

class Cache(SimpleCache):
    """Manage and report on the contents of the cache

    Adds higher-level functions
    """
    def __init__(self, cache_path):
        SimpleCache.__init__(self, cache_path)
        ensure_directory_exists(self.path)


    def get_header_filename(self, blob_id):
        "Return the filename of a blob's header file"
        fname = self.file_path(blob_id) + '.header'
        return fname
    def push(self, remote_url):
        """Execute a cache push."""
        if remote_url.startswith('http://'):
            pusher = NetPush(self)
            curl = pycurl.Curl()
            curl.setopt(curl.URL, remote_url)
            curl.setopt(curl.POST, True)
            curl.setopt(curl.HTTPHEADER, ['Content-Type: application/x-pdk',
                                          'Transfer-Encoding: chunked',
                                          'Content-Length:'])
            curl.setopt(curl.READFUNCTION, \
                        ReadAdapter(pusher.gen_offer()).read)
            response = StringIO()
            curl.setopt(curl.WRITEFUNCTION, response.write)
            curl.setopt(curl.NOPROGRESS, False)
            curl.setopt(curl.FAILONERROR, True)
            progress = ConsoleProgress('push: ' + remote_url)
            adapter = CurlAdapter(progress)
            curl.setopt(curl.PROGRESSFUNCTION, adapter.callback)
            curl.perform()

            needed_blob_ids = response.getvalue().splitlines()
            uploads = []
            for blob_id in needed_blob_ids:
                if blob_id:
                    uploads.append(pusher.gen_upload(blob_id))

            iterator = chain(*uploads)
            curl.setopt(curl.READFUNCTION, ReadAdapter(iterator).read)
            curl.setopt(curl.WRITEFUNCTION, sys.stdout.write)
            curl.perform()
            curl.close()
        else:
            # Perform a local push
            destination = Cache(remote_url)
            rexpr = re.compile('sha-1:[a-fA-F0-9]+$')
            for blob_id in self:
                if rexpr.match(blob_id) and blob_id not in destination:
                    local_filename = self.file_path(blob_id)
                    locator = FileLocator('', local_filename, blob_id)
                    destination.import_file(locator)
                    destination.write_index()


    def add_header(self, header, blob_id):
        """ write a header to a file, identified by blob_id"""
        # Always start with a temp file
        temp_path = self.make_download_filename()
        try:
            # Fill it.
            open(temp_path, 'w').write(header)
            # Link it to the appropriate blob_id.header file
            filename = self.get_header_filename(blob_id)
            try:
                os.link(temp_path, filename)
            except OSError, msg:
                # file exists
                if msg.errno == 17:
                    pass
                else:
                    raise
        finally:
            # Get rid of the temp file
            os.unlink(temp_path)


    def load_package(self, blob_id, package_format):
        """Load the raw header data into memory from a package
        """
        package_type = get_package_type(format = package_format)
        header_file = self.get_header_filename(blob_id)

        # check if the header file is already present
        # don't bother with synchronization issues.
        if os.path.basename(header_file) not in self:
            # Suck the header out and install it
            blob_filename = self.file_path(blob_id)
            try:
                header = package_type.extract_header(blob_filename)
            except IOError, error:
                if error.errno == 2:
                    message = "Missing package file in file cache\n"
                    message += "ref = '%s'\n" % blob_id
                    message += "Consider running pdk download on any new "
                    message += "or recently modified components."
                    raise SemanticError, message
            self.add_header(header, blob_id)

        header = open(header_file).read()
        return package_type.parse(header, blob_id)

########################################################################
# Deal with file transfers
#
# Ultimately, this is not how this should be done.  There should be a
# method on cache to import a file, and that method should use some of
# this plumbing. It should determine whether the file is on the local
# file system, a different filesystem, or a separate curl-accessible 
# machine.  It should know whether to copy the file, and from where,
# and it should link it into the cache.
#
# However, right now, there is at least separation between the Cache
# proper, and all the file-copy plumbing.  But by all rights we need
# to finish the refactoring.
#

def gen_payloads(handle):
    """Read in the application/x-pdk protocol. Generate payload tuples.

    Each tuple yielded is of the form (name, size, handle).
    The caller is expected to know what to do with the handle (read
    up to 'size' bytes, one presumes).
    """
    while 1:
        line = handle.readline()
        if not line:
            break
        name, size_string = line.strip().split()
        size = int(size_string)
        # Returns handle so the user can continue reading from the 
        # file
        yield (name, size, handle)
        # Consume the trailing blank line, presumably left behind
        # by the routine that called this one.
        line = handle.readline()


class ReadAdapter(object):
    """Provide a file like read function over an iterator yielding strings.

        blocks: an iterator yielding bytes of reasonable size.
    """
    def __init__(self, blocks):
        self.blocks = iter(blocks)
        self.buffer = ''

    def read(self, size):
        """Behave like the file.read function."""
        for block in self.blocks:
            self.buffer += block
            if size <= len(self.buffer):
                break

        value = self.buffer[:size]
        self.buffer = self.buffer[size:]
        return value

class NetPush(object):
    """Push files between caches on separate machines.

    Handles only low level details. This code only writes to file handles
    and yields blocks of text.
    """
    def __init__(self, local_cache):
        self.local_cache = local_cache

    def gen_offer(self):
        """Generate text blocks associated with offering blob-ids."""
        payload = StringIO()
        for blob_id in self.local_cache.iter_sha1_ids():
            print >> payload, blob_id
            # Awww, crap. We avoided loading all the ids, only to
            # collect them in a big string here. :-(
            # it's a pain that we need the size.
        size = len(payload.getvalue())
        payload.reset()
        yield 'offer %d\n' % size
        for block in gen_fragments(payload, size):
            yield block
        yield '\n'

    def gen_upload(self, blob_id):
        """Generate text blocks associated with uploading a cache file."""
        filename = self.local_cache.file_path(blob_id)
        size = os.stat(filename)[ST_SIZE]
        yield '%s %d\n' % (blob_id, size)
        for block in gen_file_fragments(filename):
            yield block
        yield '\n'

    def receive(self):
        """Receive offers and cache files.

        On offer, scan the remote (local to me) cache and print out any
        offered blob_ids not already in the remote (local to me) cache.

        On blob_id, add it's contents to the remote (local to me) cache.
        """
        print 'Content-Type: text/plain'
        print
        for name, size, handle in gen_payloads(sys.stdin):
            if name == 'offer':
                # Received an offer, so return the list of blobs
                # we don't already have
                for blob_id in handle.read(size).splitlines():
                    if blob_id not in self.local_cache:
                        print blob_id
            elif name.startswith('sha-1:'):
                temp_file = self.local_cache.make_download_filename()
                try:
                    local_handle = open(temp_file, 'w')
                    for block in gen_fragments(handle, size):
                        local_handle.write(block)
                    local_handle.close()
                    locator = FileLocator('', temp_file, name)
                    self.local_cache.import_file(locator)
                finally:
                    os.unlink(temp_file)
        self.local_cache.write_index()
        print


# vim:ai:et:sts=4:sw=4:tw=0:
