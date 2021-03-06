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
import popen2
import shutil
from cElementTree import ElementTree
from elementtree.ElementTree import XMLTreeBuilder
from xml.sax.writer import XmlWriter
from pdk.progress import ConsoleProgress, CurlAdapter
from pdk.exceptions import ConfigurationError, CommandLineError

normpath = os.path.normpath

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

def cpath(*args):
    """Get an absolute path object pointing to the current directory."""
    return os.path.normpath(os.path.join(os.getcwd(), *args))

def pjoin(*args):
    '''Act like os.path.join but also normalize the result.'''
    return normpath(os.path.join(*args))

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
        raise ConfigurationError, \
              "This program requires python 2.3 or greater"

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
    progress = ConsoleProgress(remote_url)
    adapter = CurlAdapter(progress)
    curl.setopt(curl.PROGRESSFUNCTION, adapter.callback)

    curl.perform()
    handle.close()
    mtime = curl.getinfo(curl.INFO_FILETIME)
    curl.close()
    if mtime != -1:
        os.utime(local_filename, (mtime, mtime))

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
    pdk_parser = PDKXMLTreeBuilder()
    tree.parse(source, pdk_parser)
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

    if len(base_parts) > len(file_parts):
        raise ValueError("%s not within %s" % (file_path, base_dir))
    
    # Bite off bits from the left, ensuring they're the same.
    while base_parts:
        base_bit = base_parts.pop(0)
        file_bit = file_parts.pop(0)
        if base_bit != file_bit:
            raise ValueError("%s not within %s" % (file_path, base_dir))

    if file_parts:
        result = os.path.join(*file_parts)
    else:
        result = '.'

    # git commands require trailing slashes on directories. 
    if os.path.isdir(result):
        result += "/"
    return result
    
def shell_command(command_string, stdin = None, debug = False):
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
        raise CommandLineError, 'command "%s" failed' % command_string
    return output

def moo(args):
    """our one easter-egg, used primarily for plugin testing"""
    print "This program has batcow powers"
    print " _____        "
    print " }    \  (__) "
    print " }_    \ (oo) "
    print "   / ---' lJ  "
    print "  / |    ||   "
    print " *  /\---/\   "
    print "    ~~   ~~   "
    print "Have you mooed today?"
    if args:
        print "You said '%s'" % ' '.join([str(x) for x in args])

# vim:ai:et:sts=4:sw=4:tw=0:
