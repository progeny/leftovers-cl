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
from pdk.exceptions import InputError

# Obviously at least one of these two needs to work for PDK to be useful.
try:
    # for working with deb packages
    import apt_inst
    import apt_pkg
    import smart.backends.deb.debver as debver
    from GnuPGInterface import GnuPG as gpg
except ImportError:
    pass

try:
    # for working with rpm packages
    import rpm as rpm_api
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
            result = self.contents[contents_key]
        return result

    def __getitem__(self, key):
        special_version_names = {'version.epoch': 'epoch',
                                 'version.version': 'version',
                                 'version.release': 'release' }
        if key in special_version_names:
            return getattr(self.version, special_version_names[key])

        try:
            return getattr(self, key)
        except AttributeError, e:
            raise KeyError, e

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

    def __len__(self):
        return len(self.contents)

    def _get_values(self):
        '''Return an immutable value representing the full identity.'''
        field_list = ('format', 'role', 'name', 'version', 'arch',
                      'blob_id')
        contents = [ getattr(self, f) for f in field_list
                     if hasattr(self, f) ]
        return tuple(['package'] + contents)

    def __hash__(self):
        return hash(self._get_values())

    def __str__(self):
        return '<Package %r>' % (self._get_values(),)

    __repr__ = __str__

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

    def __str__(self):
        return '<dver %r>' % self.full_version

    __repr__ = __str__

def sanitize_deb_header(header):
    """Normalize the whitespace around the deb header/control contents."""
    return header.strip() + '\n'

class DebTags(object):
    '''Wraps an apt tags section object with more pythonic dict operations.
    '''
    def __init__(self, apt_tags):
        self.tags = apt_tags

    def __contains__(self, item):
        return bool(self.tags.has_key(item))

    def __getitem__(self, attribute):
        if self.tags.has_key(attribute):
            return self.tags.get(attribute)
        else:
            raise LookupError(attribute)

class _Dsc(object):
    """Handle debian source packages (dsc file + friends)."""
    type_string = 'dsc'
    format_string = 'deb'
    role_string = 'source'

    def parse(self, control, blob_id):
        """Parse control file contents. Returns a package object."""
        tags = apt_pkg.ParseSection(control)
        return self.parse_tags(tags, blob_id)

    def parse_tags(self, apt_tags, blob_id):
        '''Parse an apt tags section object directly.

        Returns a package object.
        '''
        tags = DebTags(apt_tags)
        raw_file_list = tags['Files']
        extra_files = []
        for line in raw_file_list.strip().splitlines():
            (md5sum, dummy, name) = line.strip().split()
            extra_files.append(('md5:' + md5sum, name))
        extra_files = tuple(extra_files)

        # be tolerant of both dsc's and apt source stanzas.
        if 'Source' in tags:
            name = tags['Source']
        else:
            name = tags['Package']

        version = DebianVersion(tags['Version'])

        fields = { 'blob-id': blob_id,
                   'name': name,
                   'version': version,
                   'arch': tags['Architecture'],
                   'extra-file': extra_files }

        if 'Directory' in tags:
            fields['directory'] = tags['Directory']

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

dsc = _Dsc()

class _Deb(object):
    """Handle deb packages. (binary)"""
    type_string = 'deb'
    format_string = 'deb'
    role_string = 'binary'

    def parse(self, control, blob_id):
        """Parse control file contents. Returns a package object."""
        tags = apt_pkg.ParseSection(control)
        return self.parse_tags(tags, blob_id)

    def parse_tags(self, apt_tags, blob_id):
        '''Parse an apt tags section object directly.

        Returns a package object.
        '''
        tags = DebTags(apt_tags)
        name = tags['Package']
        version = DebianVersion(tags['Version'])

        sp_name = name
        sp_version = version
        if 'Source' in tags:
            sp_name = tags['Source']
            if re.search(r'\(', sp_name):
                match = re.match(r'(\S+)\s*\((.*)\)', sp_name)
                (sp_name, sp_raw_version) = match.groups()
                sp_version = DebianVersion(sp_raw_version)

        contents = { 'blob-id': blob_id,
                     'name': name,
                     'version': version,
                     'sp-name' : sp_name,
                     'sp-version' : sp_version,
                     'arch': tags['Architecture'] }

        if 'MD5Sum' in tags:
            contents['raw_md5sum'] = tags['MD5Sum']

        if 'Filename' in tags:
            contents['raw_filename'] = tags['Filename']

        return Package(contents, self)

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

deb = _Deb()

class _UDeb(_Deb):
    '''Handle udeb packages. (special binary)'''
    type_string = 'udeb'
    format_string = 'deb'
    role_string = 'binary'

    def get_filename(self, package):
        """Return a udeb filename for use in an apt repo."""
        version_string = package.version.string_without_epoch
        return '%s_%s_%s.udeb' % (package.name, version_string,
                                    package.arch)

udeb = _UDeb()

def get_rpm_header(handle):
    """Extract an rpm header from an rpm package file."""
    ts = rpm_api.TransactionSet('/', rpm_api._RPMVSF_NODIGESTS
                            | rpm_api._RPMVSF_NOSIGNATURES)
    header = ts.hdrFromFdno(handle.fileno())
    handle.close()
    return header

class RPMVersion(object):
    """A comparable RPM package version."""
    def __init__(self, header = None, version_tuple = None):
        if header:
            if header[rpm_api.RPMTAG_EPOCH]:
                self.epoch = str(header[rpm_api.RPMTAG_EPOCH])
            else:
                self.epoch = ''
            self.version = header[rpm_api.RPMTAG_VERSION]
            self.release = header[rpm_api.RPMTAG_RELEASE]
        else:
            self.epoch, self.version, self.release = version_tuple
        self.tuple = (self.epoch or '',  self.version, self.release)
        self.string_without_epoch = '-'.join([self.version, self.release])
        self.full_version = '/'.join(self.tuple)

    def __cmp__(self, other):
        if isinstance(other, basestring):
            other = RPMVersion(version_tuple = other.split('/'))
        return rpm_api.labelCompare(self.tuple, other.tuple)

    def __str__(self):
        return '<rver %r>' % self.full_version

    __repr__ = __str__

class _Rpm(object):
    """Handle binary rpm packages."""
    type_string = 'rpm'
    format_string = 'rpm'
    role_string = 'binary'

    def parse(self, raw_header, blob_id):
        """Parse an rpm header. Returns a package object."""
        header = rpm_api.headerLoad(raw_header)
        source_rpm = header[rpm_api.RPMTAG_SOURCERPM]

        # work around rpm oddity
        if source_rpm == []:
            source_rpm = None

        return Package({ 'blob-id': blob_id,
                         'name': header[rpm_api.RPMTAG_NAME],
                         'version': RPMVersion(header),
                         'arch': header[rpm_api.RPMTAG_ARCH],
                         'source-rpm': source_rpm }, self)

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

rpm = _Rpm()

class _SRpm(_Rpm):
    """Handle source rpm packages."""
    type_string = 'srpm'
    role_string_string = 'source'

    def get_filename(self, package):
        """Return a reasonable srpm package filename."""
        version_string = package.version.string_without_epoch
        return '%s-%s.src.rpm' % (package.name, version_string)

srpm = _SRpm()

def get_package_type(filename = '', format = ''):
    """Return a packge type for a filename or package reference format."""
    if filename.endswith('.deb') or format == 'deb':
        return deb
    elif filename.endswith('.udeb') or format == 'udeb':
        return udeb
    elif filename.endswith('.dsc') or format == 'dsc':
        return dsc
    elif filename.endswith('.src.rpm') or format == 'srpm':
        return srpm
    elif filename.endswith('.rpm') or format == 'rpm':
        return rpm
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
