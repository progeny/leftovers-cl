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
package.py


Houses functionality for representing deb and rpm source and binary
packages.
"""

import re
import rfc822
from cStringIO import StringIO as stringio
from pdk.exceptions import InputError

# Obviously at least one of these two needs to work for PDK to be useful.
try:
    # for working with deb packages
    import apt_inst
    import smart.backends.deb.debver as debver
    from GnuPGInterface import GnuPG as gpg
except ImportError:
    pass

try:
    # for working with rpm packages
    import rpm
except ImportError:
    pass


__revision__ = "$Progeny$"

class Package(object):
    """Represents a logical package.

    Fields may be accessed as attributes or items, and dashes are
    converted to underscores as needed.
    """
    __slots__ = ('contents', 'package_type', 'version')
    def __init__(self, contents, package_type):
        self.contents = dict(contents)
        self.package_type = package_type
        self.version = self.contents['version']

    def find_key(self, key):
        """Be forgiving about key lookups. s/-/_/g"""
        if key in self.contents:
            return key
        dashed_key = str(key).replace('_', '-')
        if dashed_key in self.contents:
            return dashed_key
        return None

    def __contains__(self, key):
        return self.find_key(key) != None

    def __getattr__(self, key):
        result = None
        contents_key = self.find_key(key)
        if contents_key == None:
            if hasattr(self.contents, key):
                result = getattr(self.contents, key)
            else:
                raise AttributeError(key)
        else:
            result = self[contents_key]
        return result

    def __getitem__(self, key):
        contents_key = self.find_key(key)
        if contents_key == None:
            raise KeyError(key)
        return self.contents.get(contents_key)

    def __setitem__(self, item, value):
        raise TypeError('object does not support item assignment')

    def get_filename(self):
        """Defer filename calculation to the package type object."""
        return self.package_type.get_filename(self)
    filename = property(get_filename)

    def get_type(self):
        """Defer the type string to the package type object."""
        return self.package_type.type_string
    type = property(get_type)

    def get_format(self):
        """Defer the format string to the package type object."""
        return self.package_type.format_string
    format = property(get_format)

    def get_role(self):
        """Defer the role string to the package type object."""
        return self.package_type.role_string
    role = property(get_role)

    def get_bindings_dict(self):
        """Get a dictionary for this object but with undashified fields."""
        bindings = {}
        for key, value in self.contents.items():
            undashified_key = str(key).replace('-', '_')
            bindings[undashified_key] = value
        bindings['filename'] = self.filename
        bindings['format'] = self.format
        bindings['role'] = self.role
        bindings['type'] = self.type
        bindings['epoch'] = self.version.epoch
        bindings['version'] = self.version.version
        bindings['release'] = self.version.release
        return bindings

    def __len__(self):
        return len(self.contents)

    def _get_values(self):
        '''Return an immutable value representing the full identity.'''
        return tuple(['package'] + self.contents.items()
                     + [self.package_type])

    def __hash__(self):
        return hash(self._get_values())

    def __cmp__(self, other):
        return cmp(self._get_values(), other._get_values())

    def __getstate__(self):
        return (self.contents, self.package_type)

    def __setstate__(self, state):
        self.__init__(*state)

def split_deb_version(raw_version):
    """Break a debian version string into it's component parts."""
    return re.match(debver.VERRE, raw_version).groups()

class DebianVersion(object):
    """A comparable Debian package version number."""
    def __init__(self, original_header):
        self.original_header = original_header
        self.epoch, self.version, self.release = \
            split_deb_version(original_header)
        self.string_without_epoch = \
            synthesize_version_string(None, self.version, self.release)
        self.full_version = \
            synthesize_version_string(self.epoch, self.version,
                                      self.release)
    def __cmp__(self, other):
        if isinstance(other, basestring):
            other = DebianVersion(other)
        from smart.backends.deb.debver import vercmp as smart_vercmp
        return smart_vercmp(self.original_header, other.original_header)

def sanitize_deb_header(header):
    """Normalize the whitespace around the deb header/control contents."""
    return header.strip() + '\n'

class Dsc(object):
    """Handle debian source packages (dsc file + friends)."""
    type_string = 'dsc'
    format_string = 'deb'
    role_string = 'source'

    def parse(self, control, blob_id):
        """Parse control file contents. Returns a package object."""
        handle = stringio(control)
        message = rfc822.Message(handle)

        raw_file_list = message['Files']
        extra_files = []
        for line in raw_file_list.strip().splitlines():
            (md5sum, dummy, name) = line.strip().split()
            extra_files.append(('md5:' + md5sum, name))
        extra_files = tuple(extra_files)

        # be tolerant of both dsc's and apt source stanzas.
        if 'Source' in message:
            name = message['Source']
        else:
            name = message['Package']

        version = DebianVersion(message['Version'])

        fields = { 'blob-id': blob_id,
                   'name': name,
                   'version': version,
                   'arch': message['Architecture'],
                   'extra-file': extra_files,
                   'raw': control }
        return Package(fields, self)

    def extract_header(self, filename):
        """Extract control file contents from a dsc file."""
        handle  = open(filename)
        full_text = handle.read()
        if re.search(r'(?m)^=', full_text):
            handle.seek(0)
            extractor = gpg()
            extractor.options.extra_args = ['--skip-verify']
            null = open('/dev/null', 'w')
            process = extractor.run(['--decrypt'],
                                    create_fhs=['stdout'],
                                    attach_fhs={'stdin': handle,
                                                'stderr': null})
            header = process.handles['stdout'].read()
            process.wait()
            handle.close()
            null.close()
        else:
            header = full_text
        handle.close()
        return sanitize_deb_header(header)

    def get_filename(self, package):
        """Return a dsc filename for use in an apt repo."""
        version_string = synthesize_version_string(None,
                                                   package.version.version,
                                                   package.version.release)
        return '%s_%s.dsc' % (package.name, version_string)

class Deb(object):
    """Handle deb packages. (binary)"""
    type_string = 'deb'
    format_string = 'deb'
    role_string = 'binary'

    def parse(self, control, blob_id):
        """Parse control file contents. Returns a package object."""
        handle = stringio(control)
        message = rfc822.Message(handle)

        name = message['Package']
        version = DebianVersion(message['Version'])

        sp_name = name
        sp_version = version
        if 'Source' in message:
            sp_name = message['Source']
            if re.search(r'\(', sp_name):
                match = re.match(r'(\S+)\s*\((.*)\)', sp_name)
                (sp_name, sp_raw_version) = match.groups()
                sp_version = DebianVersion(sp_raw_version)

        return Package({ 'blob-id': blob_id,
                         'name': name,
                         'version': version,
                         'sp-name' : sp_name,
                         'sp-version' : sp_version,
                         'arch': message['Architecture'],
                         'raw': control }, self)

    def extract_header(self, filename):
        """Extract control file contents from a deb package."""
        handle = open(filename)
        control = apt_inst.debExtractControl(handle)
        handle.close()
        return sanitize_deb_header(control)

    def get_filename(self, package):
        """Return a deb filename for use in an apt repo."""
        version_string = package.version.string_without_epoch
        return '%s_%s_%s.deb' % (package.name, version_string,
                                    package.arch)

def get_rpm_header(handle):
    """Extract an rpm header from an rpm package file."""
    ts = rpm.TransactionSet('/', rpm._RPMVSF_NODIGESTS
                            | rpm._RPMVSF_NOSIGNATURES)
    header = ts.hdrFromFdno(handle.fileno())
    handle.close()
    return header

class RPMVersion(object):
    """A comparable RPM package version."""
    def __init__(self, header = None, version_tuple = None):
        if header:
            if header[rpm.RPMTAG_EPOCH]:
                self.epoch = str(header[rpm.RPMTAG_EPOCH])
            else:
                self.epoch = ''
            self.version = header[rpm.RPMTAG_VERSION]
            self.release = header[rpm.RPMTAG_RELEASE]
        else:
            self.epoch, self.version, self.release = version_tuple
        self.tuple = (self.epoch or '',  self.version, self.release)
        self.string_without_epoch = '-'.join([self.version, self.release])
        self.full_version = '/'.join(self.tuple)

    def __cmp__(self, other):
        if isinstance(other, basestring):
            other = RPMVersion(version_tuple = other.split('/'))
        return rpm.labelCompare(self.tuple, other.tuple)

class Rpm(object):
    """Handle binary rpm packages."""
    type_string = 'rpm'
    format_string = 'rpm'
    role_string = 'binary'

    def parse(self, raw_header, blob_id):
        """Parse an rpm header. Returns a package object."""
        header = rpm.headerLoad(raw_header)
        return Package({ 'blob-id': blob_id,
                         'name': header[rpm.RPMTAG_NAME],
                         'version': RPMVersion(header),
                         'arch': header[rpm.RPMTAG_ARCH],
                         'source-rpm': header[rpm.RPMTAG_SOURCERPM],
                         'raw': raw_header }, self)

    def extract_header(self, filename):
        """Extract an rpm header from an rpm package file."""
        handle = open(filename)
        raw_header = get_rpm_header(handle).unload(1)
        return raw_header

    def get_filename(self, package):
        """Return a reasonable rpm package filename."""
        version_string = package.version.string_without_epoch
        return '%s-%s.%s.rpm' % (package.name, version_string,
                                 package.arch)

class SRpm(Rpm):
    """Handle source rpm packages."""
    type_string = 'srpm'
    role_string_string = 'source'

    def get_filename(self, package):
        """Return a reasonable srpm package filename."""
        version_string = package.version.string_without_epoch
        return '%s-%s.src.rpm' % (package.name, version_string)

def get_package_type(filename = '', format = ''):
    """Return a packge type for a filename or package reference format."""
    if filename.endswith('.deb') or format == 'deb':
        return Deb()
    elif filename.endswith('.dsc') or format == 'dsc':
        return Dsc()
    elif filename.endswith('.src.rpm') or format == 'srpm':
        return SRpm()
    elif filename.endswith('.rpm') or format == 'rpm':
        return Rpm()
    else:
        raise UnknownPackageTypeError((filename, format))

class UnknownPackageTypeError(InputError):
    """Exception used when a package type cannot be determined."""
    pass

def synthesize_version_string(epoch, version, release):
    """Reassemble a debian version string from it's parts."""
    dpkg_version = ''
    if epoch:
        dpkg_version += epoch + ':'
    if version:
        dpkg_version += version
    if release:
        dpkg_version += '-' + release
    return dpkg_version
