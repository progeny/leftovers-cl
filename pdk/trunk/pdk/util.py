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
util.py

Catchall module for utilities not clearly belonging anywhere else.
Currently contains path manipulation, parsing of vertical bar separated
fields, and generators which iterate of files using fixed block sizes.
"""
__revision__ = "$Progeny$"
import os
import sys
import inspect
from cElementTree import ElementTree
from elementtree.ElementTree import XMLTreeBuilder
from xml.sax.writer import XmlWriter

def caller():
    """Report the caller of the current function

    Very useful during debugging.
    """
    record = inspect.stack()[2] # caller's caller
    source = os.path.basename(record[1])
    line = record[2]
    func = record[3]
    text = record[4]
    return "%s(%d):%s:%s" % (source, line, func, text)
    
# These _must_ come from "real" python elementtree
from elementtree.ElementTree import Comment as et_comment
from elementtree.ElementTree import ProcessingInstruction \
     as et_processing_instruction

class path(object):
    '''Utility class for handling paths with less typing.

    str(path("project", "super")) -> "project/super"

    # note the trailing ()
    path("project", "super")() -> "project/super"
    path("project")["s-u-p-e-r"]() -> "project/s-u-p-e-r"
    path("project").a.b.c.super() -> "project/a/b/c/super"
    path("/")() -> "/"
    path("project", ".", "super")() -> "project/super"
    path("project").super[".."]() -> "project"

    The basic idea is: given a starting path object, you can use
    item or attribute access to contruct longer paths.

    The actual path is accessible by converting the object to 
    a string or just calling to object.

    '''
    def __init__(self, *args):
        """Set base path"""
        self.base = str(os.path.normpath(os.path.join(*args)))

    def __str__(self):
        """return self as a string """
        return self.str()

    def __call__(self):
        """return self as a string """
        return self.str()

    def str(self):
        """return self as a string """
        return self.base

    def __add__(self, segment):
        """Append a new path from self + component"""
        return path(self.base, str(segment))

    def __getattr__(self, attribute):
        """Append a new path from self + attribute
        It is handy for path.smith = "path/smith"
        """
        return self + attribute

    __getitem__ = __getattr__

    def __cmp__(self, other_object):
        """Compare self to string or other path"""
        other = str(other_object)
        return cmp(self.base, other)

    def __repr__(self):
        """Return representation"""
        return '<path %s>' % self.base + '- %s' % hash(self.base)

    def __hash__(self):
        """Return a hash of path"""
        return hash(self.base)


def cpath(*args):
    """Get an absolute path object pointing to the current directory."""
    return path(os.getcwd(), *args)

def split_pipe(handle):
    """convert a file/list of "<key>|<value" pairings into a map"""
    summary = {}
    for line in handle:
        line = line.strip()
        if not line:
            continue
        key, value = line.split('|', 1)
        item = summary.setdefault(key, [])
        item.append(value)
    return summary

default_block_size = 16384

def gen_file_fragments(filename, block_size = default_block_size):
    """Run gen_fragments on a whole file."""
    return gen_fragments(open(filename), None, block_size)

def gen_fragments(handle, max_size = None, block_size = default_block_size):
    """Generate a series of fragments of no more than block_size.

    Fragments are read from handle.

    If the max_size parameter is provided it acts as a limit on the total
    number of bytes read.
    """
    bytes_remaining = max_size or block_size
    while(bytes_remaining):
        this_read = min(block_size, bytes_remaining)
        data = handle.read(this_read)
        if data:
            yield data
        else:
            break
        if max_size:
            bytes_remaining -= len(data)


def assert_python_version():
    """single location to assure installed version of python"""
    if [2, 3] > sys.version_info[:2]:
        raise Exception, "This program requires python 2.3 or greater"

def ensure_directory_exists(the_path):
    '''Create the base cache directory if needed.'''
    real_path = os.path.abspath(str(the_path))
    if not os.path.exists(real_path):
        os.makedirs(real_path)

def get_remote_file(remote_url, local_filename):
    '''Obtain a remote file via url.

    Copies the file to local_filename and attempts to set the last
    modified time.
    '''
    import pycurl
    curl = pycurl.Curl()
    curl.setopt(curl.URL, remote_url)
    handle = open(local_filename, 'w')
    curl.setopt(curl.USERAGENT, 'pdk')
    curl.setopt(curl.WRITEFUNCTION, handle.write)
    curl.setopt(curl.NOPROGRESS, False)
    curl.setopt(curl.FAILONERROR, True)
    curl.setopt(curl.OPT_FILETIME, True)
    curl.perform()
    handle.close()
    mtime = curl.getinfo(curl.INFO_FILETIME)
    curl.close()
    if mtime != -1:
        print os.utime(local_filename, (mtime, mtime))

def make_path_to(file_path):
    """Given a file path, create the directory up to the 
    file location.
    """
    # Candidate for pdk.util? 
    file_path = os.path.abspath(file_path)
    assert file_path.find('bin/cache') == -1
    #print('make_path_to', file_path, 'from', caller())
    path_part = os.path.split(file_path)[0]
    if path_part and not os.path.isdir(path_part):
        ensure_directory_exists(path_part)

def find_cache_path(directory=None):
    """return the cache directory location, by looking for the
    work-in-progress directory, and appending "cache"
    """
    result = None

    if (directory): 
        base = find_base_dir(directory) 
    else:
        environ_key = 'PDK_CACHE_PATH'
        if (environ_key in os.environ):
            base = os.environ[environ_key]
        else:
            base = find_base_dir(os.getcwd())

    if base:
        result = os.path.join(base, 'cache')
    else:
        # This is so wrong:
        result = os.path.join(os.getcwd(), 'cache')
        # This would be more sensible
        #raise IOError("No cache path found for %s" % directory)

    ensure_directory_exists(result)
    return result

def find_base_dir(directory=os.getcwd()):
    """Locate the directory above the current directory, containing
    the work, cache, and svn directories.

    Returns None if 'work' is not to be found in the current path.
    """
    # Based on the client-side (only-side) directory structure 
    # proposal.
    #
    # This is awful in its way.  We don't know where the top of our 
    # workspace really is, so we look for markers.
    #
    # Is this too much like guessing?  
    # See python -c "import this"
    # 
    # We need a way to know for certain where the top of the 
    # workspace really is.
    parts = directory.split(os.path.sep)
    parts = list(parts)
    try:
        position = parts.index('work')
        result = os.path.sep.join(parts[:position])
    except ValueError:
        result = None
        while parts:
            base_candidate = os.path.sep.join(parts)
            for marker in 'cache', 'work':
                mark_path = os.path.join(base_candidate, marker)
                if os.path.isdir(mark_path):
                    result = base_candidate
                    break
            parts.pop()
    return result


# Design by contract (DBC) extensions
class NotMet(Exception):
    "An exception for PBC violations"
    pass

def precondition(function, invariant):
    "Assert a precondition."
    def _prewrapper(*args, **kwargs):
        """Prepends a function with a precondition call"""
        if not invariant(*args, **kwargs):
            raise NotMet(invariant.__name__, args, kwargs)
        return function(*args, **kwargs)
    return _prewrapper

def postcondition(function, invariant):
    "Assert a post-condition"
    def _postwrapper(*args, **kwargs):
        """Appends a result check onto a function"""
        result = function(*args, **kwargs)
        if not invariant(result, *args, **kwargs):
            raise NotMet(invariant.__name__, result, *args, **kwargs)
        return result
    return _postwrapper

def notnull(*args):
    """Returns true if none of the arguments are null"""
    return None not in args


class PrettyWriter(object):
    '''Handle low-level details of writing pretty indented xml.'''
    def __init__(self, handle, encoding):
        self.writer = XmlWriter(handle, encoding = encoding)
        self.indent = 0

    def start_document(self):
        '''Start the document.'''
        self.writer.startDocument()

    def end_document(self):
        '''End the document.'''
        self.writer.endDocument()

    def start_element(self, name, attributes):
        '''Start an element with children.'''
        self.tab()
        self.writer.startElement(name, attributes)
        self.newline()
        self.indent += 2

    def end_element(self, name):
        '''End an element with children.'''
        self.indent -= 2
        self.tab()
        self.writer.endElement(name)
        self.newline()

    def text_element(self, name, attributes, text):
        '''Start and end an element with no element children.'''
        self.tab()
        self.writer.startElement(name, attributes)
        self.writer.characters(text, 0, len(text))
        self.writer.endElement(name)
        self.newline()

    def pi(self, target, text):
        '''Handle inserting a processing instruction.'''
        self.tab()
        self.writer.processingInstruction(target, text)
        self.newline()

    def comment(self, text):
        '''Insert a comment.'''
        self.tab()
        # work around the python xml writer weirdness
        save_packing = self.writer._packing
        self.writer._packing = 0
        self.writer.comment(text, 0, len(text))
        self.writer._packing = save_packing
        # self.newline()

    def tab(self):
        '''Insert whitespace characters representing an indentation.'''
        self.writer.characters(self.indent * ' ', 0, self.indent)

    def newline(self):
        '''Insert a \\n to end a line.'''
        self.writer.characters('\n', 0, 1)

def write_pretty_xml_to_handle(tree, handle):
    '''Helper function for write_pretty_xml.'''
    writer = PrettyWriter(handle, 'utf-8')
    writer.start_document()
    def _write_element(element, indent):
        '''Recursively write bits of the element tree to PrettyWriter.'''
        if element.text and element.text.strip():
            writer.text_element(element.tag, element.attrib, element.text)
        else:
            writer.start_element(element.tag, element.attrib)
            for item in element:
                if item.tag == et_comment:
                    writer.comment(item.text)
                elif item.tag == et_processing_instruction:
                    writer.pi(*item.text.split(' ', 1))
                else:
                    _write_element(item, indent + 2)
            writer.end_element(element.tag)
    _write_element(tree.getroot(), 0)
    writer.end_document()

def write_pretty_xml(tree, destination):
    '''Take an elementtree structure and write it as pretty indented xml.'''
    if hasattr(destination, 'write'):
        write_pretty_xml_to_handle(tree, destination)
    else:
        handle = open(destination, 'w')
        try:
            write_pretty_xml_to_handle(tree, handle)
        finally:
            handle.close()

class PDKXMLTreeBuilder(XMLTreeBuilder):
    '''Behave like the elementtree base but also add comments and pis.'''
    def __init__(self):
        XMLTreeBuilder.__init__(self)
        parser = self._parser
        parser.CommentHandler = self.comment
        parser.ProcessingInstructionHandler = self.pi

    def comment(self, text):
        '''Add a comment element'''
        comment = self._target.start(et_comment, {})
        comment.text = text
        self._target.end(et_comment)

    def pi(self, target, text):
        '''Add a processing instruction.'''
        pi = self._target.start(et_processing_instruction, {})
        pi.text = ' '.join([target, text])
        self._target.end(et_processing_instruction)

def parse_xml(source):
    '''Return an ElementTree.

    Includes comments and processing instructions.
    '''
    tree = ElementTree()
    tree.parse(source, PDKXMLTreeBuilder())
    return tree

def WithAccessLogging(instance, its_name):
    """Debugging Aid
    Class wrapper to log access to attributes
    """
    class add_in(object):
        """WithAccess add-in wrapper"""
        def __init__(self, log):
            self.log = log
        def __getattr__(self, name):
            """Return an attribute, after reporting it"""
            self.log.info(
                caller()
                , "Accessing %s.%s" % (its_name, name)
                )
            return getattr(instance, name)
        def __setattr__(self, name, value):
            """Set an attribute, after reporting it"""
            self.log.info(caller()
                , "Setting %s.%s to %s" % (
                    its_name, name, str(value)
                    )
                )
            setattr(instance, name, value)
    return add_in()


# vim:ai:et:sts=4:sw=4:tw=0:
