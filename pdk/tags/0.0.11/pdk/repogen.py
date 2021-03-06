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
repogen.py 

Generate a repository from component & cache
"""
import os
import os.path
from time import strftime, gmtime
import re
import md5
import optparse
from sets import Set
from itertools import chain
from pdk import workspace
from pdk.component import ComponentDescriptor, Metafilter
from pdk.exceptions import SemanticError, InputError, CommandLineError, \
                IntegrityFault
import pdk.log as log
from pdk.util import ensure_directory_exists, pjoin, LazyWriter
from pdk.package import udeb

logger = log.get_logger()

__revision__ = "$Progeny$"

# The following lists are derived from the field sort order in apt.
# As of apt 0.5.28.1, that is in apt-pkg/tagfile.cc, starting at
# line 363.
package_field_order = [ "Package", "Essential", "Status", "Priority",
                        "Section", "Installed-Size", "Maintainer",
                        "Architecture", "Source", "Version", "Replaces",
                        "Provides", "Depends", "Pre-Depends", "Recommends",
                        "Suggests", "Conflicts", "Conffiles", "Filename",
                        "Size", "MD5Sum", "SHA1Sum", "Description" ]

source_field_order = [ "Package", "Source", "Binary", "Version", "Priority",
                       "Section", "Maintainer", "Build-Depends",
                       "Build-Depends-Indep", "Build-Conflicts",
                       "Build-Conflicts-Indep", "Architecture",
                       "Standards-Version", "Format", "Directory", "Files" ]


def compile_product(component_name):
    """Compile the product described by the component."""

    cache = workspace.current_workspace().cache
    compiler = Compiler(cache)

    repo_types = { 'report': compiler.dump_report,
                   'apt-deb': compiler.create_debian_pool_repo,
                   'raw': compiler.create_raw_package_dump_repo }

    product = ComponentDescriptor(component_name).load(cache)
    if product in product.meta:
        contents = dict(product.meta[product])
    else:
        contents = {}

    if 'repo-type' in contents:
        repo_type_string = contents['repo-type']
    else:
        try:
            first_package = product.packages[0]
        except IndexError:
            message = 'The component given to repogen must have ' + \
                      'at least one package.'
            raise InputError(message)
        if first_package.format == 'deb':
            repo_type_string = 'apt-deb'
        else:
            repo_type_string = 'raw'

    if repo_type_string not in repo_types:
        message = 'invalid repo-type given for %s' % component_name
        raise InputError, message
    repo_type = repo_types[repo_type_string]

    if os.path.exists('repo'):
        os.system('rm -rf repo')

    repo_type(product, contents)

class DebianPoolInjector(object):
    """This class handles the details of putting a package into a
    traditional Debian-style pool.  It also creates apt-style headers
    for the package index.
    """

    def __init__(self, cache, package, section, repo_dir):
        self.cache = cache
        self.package = package
        self.section = section
        self.repo_dir = pjoin(repo_dir)

    def get_subsection(self):
        '''Get the repo subsection for this package.

        Used for udebs to divert their metadata into debian-installer.
        '''
        if self.package.package_type == udeb:
            return 'debian-installer'
        else:
            return None

    def get_pool_dir(self):
        """Return the top-level absolute path for the pool."""
        if self.package.role == 'binary':
            name = self.package.sp_name
        else:
            name = self.package.name

        return pjoin(self.repo_dir, 'pool', self.section, name[0], name)


    def get_pool_location(self):
        """Where should the given package be put?"""
        repo_path = self.get_pool_dir()
        repo_filename = self.package.filename
        return pjoin(repo_path, repo_filename)


    def get_relative_pool_path(self):
        """Return the top-level path for the pool, relative to what
        will become the base URI for the repository."""
        abs_path = str(self.get_pool_dir())
        rel_path = ""
        fn = ""
        psplit = os.path.split
        while fn != "pool":
            (abs_path, fn) = psplit(abs_path)
            if rel_path:
                rel_path = pjoin(fn, rel_path)
            else:
                rel_path = fn
        return rel_path


    def get_extra_pool_locations(self):
        """Return a dict { pool_location: fileref }

        Return a dictionary relating pool_locations to
        filerefs. This method only handles extra files. (diff.gz etc.)
        """
        if not hasattr(self.package, 'extra_file'):
            return {}
        pool_dir = self.get_pool_dir()
        return dict([ (pjoin(pool_dir, filename), blob_id)
                      for blob_id, filename in self.package.extra_file ])


    def get_links(self):
        """Return { pool_location: fileref } for all package's filerefs

        Relate all pool locations associated with this package to their
        respective filerefs.

        This is useful for putting packages into a repository.
        """
        locations = self.get_extra_pool_locations()
        locations.update(dict([ (self.get_pool_location(),
                                 self.package.blob_id) ]))
        return locations


    def get_file_size_and_hash(self):
        """Return (size, md5) for the main package file."""

        fn = self.cache.file_path(self.package.blob_id)
        size = os.stat(fn).st_size

        f = open(fn)
        m = md5.new(f.read())
        digest = m.hexdigest()
        f.close()

        return (size, digest)


    def header_transform(self, headers):
        """Transform the raw dpkg headers into headers suitable for apt."""

        # Get the data we need to add to the headers.
        # Type:
        is_source = self.package.role == "source"

        # Relative path:
        pool_path = self.get_relative_pool_path()
        if not is_source:
            pool_path = os.path.join(pool_path, self.package.filename)

        # File size and MD5:
        (size, md5_digest) = self.get_file_size_and_hash()

        # Most transformations happen on single-line fields, and
        # multi-line fields are always at the end of the headers.
        # Thus, we split the headers into two groups.
        multis = []
        singles = []
        in_multi = False
        for line in headers:
            if in_multi:
                multis.append(line)
            else:
                if re.search(r':\s*$', line) or re.search(r'^ ', line):
                    in_multi = True
                    multis.append(line)
                else:
                    singles.append(line)

        # Now transform the singles into a list of tuples.
        singles_tuples = [tuple(re.split(r':\s+', x, 1)) for x in singles]

        # Change the tuple list as needed, outputting to a dict.
        singles_dict_out = {}

        for (field, value) in singles_tuples:
            if is_source and field == "Source":
                singles_dict_out["Package"] = value
            else:
                singles_dict_out[field] = value

        # Append extra fields.
        if is_source:
            singles_dict_out["Directory"] = pool_path + "\n"
        else:
            singles_dict_out["Size"] = "%d\n" % (size,)
            singles_dict_out["Filename"] = pool_path + "\n"
            singles_dict_out["MD5Sum"] = md5_digest + "\n"

        # Only multi-line header change: if this is source, add
        # information for the .dsc file.
        if is_source:
            multis.append(" %s %d %s\n" % (md5_digest, size,
                                           self.package.filename))

        # Change singles back into a list of lines.
        singles = []
        if is_source:
            field_order = source_field_order
        else:
            field_order = package_field_order
        for key in field_order:
            if singles_dict_out.has_key(key):
                singles.append("%s: %s" % (key, singles_dict_out[key]))

        # Recombine with the multis and return.
        return singles + multis


    def get_apt_header(self):
        """Return the full apt header for the package the object
        handles.
        """

        header_fn = self.cache.get_header_filename(self.package.blob_id)
        header_info = open(header_fn)
        header_lines = header_info.readlines()
        header_info.close()
        header_lines = self.header_transform(header_lines)
        header_lines.append("\n")
        return header_lines


    def get_architectures(self, available_archs):
        """Return the architecture this package supports."""
        if self.package.role == 'source':
            arches = ['source']
        elif self.package.arch == 'all':
            arches = available_archs - Set(['source'])
        else:
            arches = [ self.package.arch ]

        return arches


    def link_to_cache(self):
        """Hard-link the cache file into the proper location in the
        pool.
        """

        pexist = os.path.exists
        locations = self.get_links()
        for link_dest, blob_id in locations.items():
            link_src = self.cache.file_path(blob_id)
            if pexist(link_dest):
                if os.path.samefile(link_src, link_dest):
                    continue
                else:
                    message =  ", %s exists and is not %s"  \
                               % (link_dest, link_src)
                    raise IntegrityFault(message)
            link_dest_dir = os.path.dirname(link_dest)
            ensure_directory_exists(link_dest_dir)
            try:
                os.link(link_src, link_dest)
            except OSError, message:
                raise IntegrityFault(
                    "%s: Cannot link %s to %s" \
                    % (message, link_src,link_dest)
                    )

class DebianPoolRepo(object):
    """Create a full repository from a Debian pool, using
    apt-ftparchive to do the actual work.  Injectors are used to write
    the pool before running apt-ftparchive.

    WARNING: Deprecated!  Use DebianDirectPoolRepo instead."""

    repo_dir_name = 'repo'
    tmp_dir_name = 'tmp'

    def __init__(self, work_dir, dist, arches, sections):
        self.work_dir = work_dir
        self.dist = dist
        self.arches = arches
        self.sections = sections
        self.file_lists = self.get_file_lists()


    def get_repo_dir(self):
        """Return the top level repo directory."""
        return os.path.join(self.work_dir, self.repo_dir_name)
    repo_dir = property(get_repo_dir)


    def get_tmp_dir(self):
        """Return the path for a temporary work area."""
        return os.path.join(self.work_dir, self.tmp_dir_name
                            , self.repo_dir_name, self.dist)
    tmp_dir = property(get_tmp_dir)


    def get_file_lists(self):
        """Get a dictionary of LazyWriters keyed by purpose.

        Key format is ('list' or 'override', section, arch)
        """
        lists = {}
        for file_type in ('list', 'overrides'):
            for arch in self.arches:
                for section in self.sections:
                    key = (file_type, section, arch)
                    file_name = '-'.join([file_type, section, arch])
                    full_name = self.tmp_dir[file_name]
                    lists[key] = LazyWriter(full_name)
        return lists


    def get_file_list(self, arch, section):
        """Return a single file list for an architecture and section."""
        return self.file_lists[('list', section, arch)]

    def get_overrides_file(self, arch, section):
        """Return a single overrides file for an architecture and
        section."""
        return self.file_lists[('overrides', section, arch)]


    def write_to_lists(self, injector):
        """Record this package in the appropriate file lists."""
        for arch in injector.get_architectures(self.arches):
            handle = self.file_lists[('list', injector.section, arch)]
            print >> handle, injector.get_pool_location()


    def flush_lists(self):
        """Flush all file handles associated with this object.

        Probably only useful for unit testing."""
        for handle in self.file_lists.values():
            if handle.is_started():
                handle.flush()


    def get_one_dir(self, section, arch):
        """Return the index directory path for a given section and
        architecture."""
        base = pjoin(self.repo_dir, self.dist)
        if arch == 'source':
            arch_dir = 'source'
        else:
            arch_dir = 'binary-%s' % arch
        return pjoin(base, section, arch_dir)


    def get_all_dirs(self):
        """Calculate and return a list of all the package index
        directories supported by this package."""
        all_dirs = Set()
        for arch in self.arches:
            for section in self.sections:
                all_dirs.add(self.get_one_dir(section, arch))
        return all_dirs


    def make_all_dirs(self):
        """Make all directories needed for apt-ftparchive.

        This only applies to directories which are not otherwise created
        while writing filelists, etc.
        """
        for needed_dir in self.get_all_dirs():
            os.makedirs(needed_dir)


    def invoke_archiver(self):
        """Actually invoke apt-ftparchive."""
        bin = 'apt-ftparchive'
        config = self.tmp_dir.config
        status = os.system('%s -q generate %s' % (bin, config))
        if status:
            print status
            raise StandardError, (
                'archiver (%s) returned %d' % (bin, status)
            )


    def write_repo(self):
        """After all injectors have been added properly, create
        the repo."""
        self.flush_lists()
        self.invoke_archiver()


    def write_releases(self, writer):
        """Write all Release files for the repository."""
        for section in self.sections:
            for arch in self.arches:
                release_path = pjoin(
                    self.get_one_dir(section, arch)
                    , 'Release'
                    )
                handle = LazyWriter(release_path)
                writer.write(handle, section, arch)
        release_path = pjoin(self.repo_dir, self.dist, 'Release')
        writer.write_outer(LazyWriter(release_path)) 


class DebianDirectPoolRepo(DebianPoolRepo):
    """Create a full repository from a Debian pool.  Use injectors
    both to create the pool on the fly and to write the indexes."""

    def _iter_file_list_keys(self):
        '''Yield a series of keys suitable for use as file_list keys.

        See get_file_lists.
        '''
        for arch in self.arches:
            for section in self.sections:
                if arch == "source":
                    yield (section, None, arch)
                else:
                    for subsection in (None, 'debian-installer'):
                        yield (section, subsection, arch)

    def get_file_lists(self):
        """Get a dictionary of LazyWriters keyed by section and arch.

        Key format is (section, subsection, arch)

        Subsection should be None or 'debian-installer'.
        """
        lists = {}
        for key in self._iter_file_list_keys():
            section, subsection, arch = key
            if arch == "source":
                file_name = "%s/%s/source/Sources" \
                            % (self.dist, section)
            else:
                if subsection:
                    file_name = "%s/%s/%s/binary-%s/Packages" \
                                % (self.dist, section, subsection, arch)
                else:
                    file_name = "%s/%s/binary-%s/Packages" \
                                % (self.dist, section, arch)
            full_name = pjoin(self.repo_dir, file_name)
            lists[key] = LazyWriter(full_name)
        return lists


    def get_file_list(self, arch, section):
        """Return the package indexes for a single section and
        architecture."""
        return self.file_lists[(section, arch)]


    def get_overrides_file(self, arch, section):
        """In the parent class, this gets the overrides.  Since we
        don't use apt-ftparchive, flag any use of this function."""
        raise RuntimeError, "get_overrides_file() doesn't work here"


    def write_to_lists(self, injector):
        """Record this package in the appropriate file lists."""
        for arch in injector.get_architectures(self.arches):
            subsection = injector.get_subsection()
            handle = self.file_lists[(injector.section, subsection, arch)]
            handle.write("".join(injector.get_apt_header()))


    def write_repo(self):
        """Write the repository index files."""
        self.flush_lists()
        for file_list in self.file_lists.values():
            if file_list.is_started():
                os.system("gzip -n < %s > %s.gz"
                          % (file_list.name, file_list.name))


class DebianReleaseWriter(object):
    """This class writes Release files for a whole repository,
    including the toplevel Release file and the per-component files.
    """

    def __init__(self, contents, raw_arches, raw_sections, search_path):
        self.archive = contents['archive']
        self.version = contents['version']
        self.origin = contents['origin']
        self.label = contents['label']
        self.suite = contents['suite']
        self.codename = contents['codename']
        self.release_time = contents['date']
        self.description = contents['description']
        self.search_path = str(search_path)

        self.arches = list(raw_arches)
        self.arches.sort()

        debian_order = ['main', 'contrib', 'non-free']
        if Set(debian_order) >= Set(raw_sections):
            sort_table = dict(zip(debian_order, range(len(debian_order))))
            def _sec_cmp(a, b):
                """Sort compare function using a special table."""
                return cmp(sort_table[a], sort_table[b])
        else:
            _sec_cmp = cmp
        self.sections = list(raw_sections)
        self.sections.sort(_sec_cmp)


    def write(self, handle, section, arch):
        """Write a component-level Release file."""
        data = [ ('Archive', self.archive),
                 ('Version', self.version),
                 ('Component', section),
                 ('Origin', self.origin),
                 ('Label', self.label),
                 ('Architecture', arch) ]

        for label, value in data:
            print >> handle, "%s: %s" % (label, value)
        handle.flush()


    def write_outer(self, handle):
        """Write the toplevel Release file."""
        apt_handle = os.popen('apt-ftparchive release %s | grep -v ^Date'
                              % str(self.search_path))
        sums = apt_handle.read()
        status = apt_handle.close()

        if status:
            print status
            raise SemanticError, 'archiver returned %d' % status

        print >> handle, 'Origin: %s' % self.origin
        print >> handle, 'Label: %s' % self.label
        print >> handle, 'Suite: %s' % self.suite
        print >> handle, 'Version: %s' % self.version
        print >> handle, 'Codename: %s' % self.codename
        print >> handle, 'Date: %s' % self.release_time
        print >> handle, 'Architectures: %s' % ' '.join(self.arches)
        print >> handle, 'Components: %s' % ' '.join(self.sections)
        print >> handle, 'Description: %s' % self.description
        handle.write(sums)


def get_apt_component_name(ref):
    """Extract an apt-component name from a component reference"""
    return os.path.basename(ref[:-4])

class Compiler:
    """This class acts as a generic wrapper to all the little tasks
    needed to create a repository from a product.
    """

    def __init__(self, cache):
        self.cache = cache


    def deb_scan_arches(self, packages):
        """Return arches for a list of debian packages."""
        arches = Set()
        for package in packages:
            if package.role == 'source':
                arches.add('source')
            else:
                if package.arch != 'all':
                    arches.add(package.arch)
        return arches


    def create_debian_pool_repo(self, product, provided_contents):
        """Do the work of creating a pool repo given packages."""

        # some sane defaults for contents
        default_date = strftime("%a, %d %b %Y %H:%M:%S +0000", gmtime())
        default_apt_suite_name = get_apt_component_name(product.ref)
        contents = { 'suite': default_apt_suite_name,
                     'version' : '0',
                     'origin': default_apt_suite_name,
                     'label': default_apt_suite_name,
                     'codename': default_apt_suite_name,
                     'date': default_date,
                     'description': default_apt_suite_name,
                     'split-apt-components': ''}
        contents.update(provided_contents)

        suite = contents['suite']
        if contents['split-apt-components']:
            # an apt splittable component should not directly reference
            # packages
            if product.direct_packages:
                raise InputError, 'No direct package references ' + \
                      'allowed with split-components is in effect'
            packages_dict = {}
            # sort packages belonging to various apt_components in a dict
            # keyed by apt component name
            for apt_component in product.direct_components:
                apt_name = get_apt_component_name(apt_component.ref)
                packages_dict[apt_name] = apt_component.packages
        else:
            # default behavior: dists/$compname/main .
            # see default suite value in contents above.
            packages_dict = { 'main': product.packages }


        filtered_packages_dict = {}
        for apt_component, packages in packages_dict.items():
            new_list = [ Metafilter(product.meta, p) for p in packages ]
            filtered_packages_dict[apt_component] = new_list

        packages_dict = filtered_packages_dict

        sections = packages_dict.keys()
        all_packages = Set(chain(*packages_dict.values()))
        arches = self.deb_scan_arches(all_packages)

        # Set True to use apt-ftparchive, False to use the direct version.
        cwd = os.getcwd()
        suitepath = pjoin('dists', suite)
        if False:
            repo = DebianPoolRepo(cwd, suitepath, arches, sections)
        else:
            repo = DebianDirectPoolRepo(cwd, suitepath, arches, sections)

        search_path = pjoin(repo.repo_dir, repo.dist)
        contents['archive'] = suite
        writer = DebianReleaseWriter(contents, arches, sections,
                                     search_path)
        repo.make_all_dirs()
        for section, packages in packages_dict.items():
            for package in packages:
                injector = DebianPoolInjector(self.cache, package, section,
                                              repo.repo_dir)
                repo.write_to_lists(injector)
                injector.link_to_cache()
        repo.write_repo()
        repo.write_releases(writer)

    def create_raw_package_dump_repo(self, component, dummy):
        """Link all the packages in the product to the repository."""
        os.mkdir('repo')
        for raw_package in component.packages:
            package = Metafilter(component.meta, raw_package)
            os.link(self.cache.file_path(package.blob_id),
                    os.path.join('repo', package.filename)
                    )

    def dump_report(self, component, contents):
        """Instead of building a repo, dump a report of component contents.
        """
        if 'format' not in contents:
            raise InputError, 'Component descriptor missing format element'

        format = contents['format']
        lines = []
        for raw_package in component.packages:
            cache_location = self.cache.file_path(raw_package.blob_id)
            filtered = Metafilter(component.meta, raw_package)
            package = overlay_getitem(filtered, cache_location, '')
            lines.append(format % package)
        lines.sort()
        for line in lines:
            print line
        print

def generate(argv):
    """
    Generate a file-system repository for a linux product
    """
    my_parser = optparse.OptionParser()
    opts, args = my_parser.parse_args(args=argv)
    logger.info(str(opts), str(args))
    if not args:
        raise CommandLineError("No product file name given")
    product_file = args[0]
    compile_product(product_file)

class overlay_getitem(object):
    """A dict like delegator that returns a default for missing keys.

    Also converts None to the the default value.

    Also adds a cache_location value

    fd['missing'] -> ''
    """
    def __init__(self, target, cache_location, default):
        self.target = target
        self.cache_location = cache_location
        self.default = default

    def __getitem__(self, key):
        if key in ('cache-location', 'cache_location'):
            return self.cache_location
        try:
            value = self.target[key]
            if value is None:
                return self.default
            else:
                return value
        except KeyError:
            return self.default

# vim:ai:et:sts=4:sw=4:tw=0:
