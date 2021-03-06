#! /usr/bin/python
#
# comp2repo.py --
#
#       Build an APT repository from a comps.xml component specification.
#
# Copyright (C) 2004 Progeny Linux Systems, Inc.
#
# $Progeny$

import os
import sys
import apt_pkg
import getopt
import glob
import re
import rhpl.comps
import string
import urllib

def usage():
    print """Usage: %s [--dry-run] comps.xml UPSTREAM
       %s --update UPSTREAM uri dist comp

 e.g., %s ./comps.xml --update sarge http://archive.progeny.com/debian sarge main
       %s ./comps.xml sarge

Options are:

  --dry-run    don't actually update the component, just print
               what would be done to update it
  --update     update to upstream Packages and Sources files
               and cache the result as the upstream UPSTREAM""" \
        % (sys.argv[0], sys.argv[0], sys.argv[0], sys.argv[0])
    sys.exit(1)

options = [ 'dry-run', 'update' ]

dryrun = 0
update = 0

cachedir = os.environ["HOME"] + "/.cl-tools"

# parse command line

opts, args = getopt.getopt(sys.argv[1:], '', options)
for opt in opts:
    if opt[0] == "--dry-run":
        dryrun = 1
    elif opt[0] == "--update":
        update = 1

if update:
    if len(args) != 4:
        usage()
    upstream_id = args[0]
    upstream_apt_uri = args[1]
    upstream_apt_dist = args[2]
    upstream_apt_comp = args[3]
else:
    if len(args) != 2:
        usage()
    comps_xml = args[0]
    upstream_id = args[1]

# if we were passed the --update flag, download the Packages and
# Sources files from upstream

# XXX - need to enforce only one upstream source for a given upstream_id

if update:
    if not dryrun:
        if not os.path.exists(cachedir):
            os.mkdir(cachedir)
        url_base = "%s/dists/%s/%s" \
              % (upstream_apt_uri, upstream_apt_dist, upstream_apt_comp)
        url = url_base + "/binary-i386/Packages.gz"
        cache_packages = cachedir + "/Packages." + upstream_id + "." + \
              urllib.quote_plus(url_base)
        print "Downloading %s..." % url
        if not dryrun:
            urllib.urlretrieve(url, cache_packages + ".gz")
            os.system("zcat %s > %s" \
                      % (cache_packages + ".gz", cache_packages))
            os.unlink(cache_packages + ".gz")

        url = url_base + "/source/Sources.gz"
        cache_sources = cachedir + "/Sources." + upstream_id + "." + \
              urllib.quote_plus(url_base)
        print "Downloading %s..." % url
        if not dryrun:
            urllib.urlretrieve(url, cache_sources + ".gz")
            os.system("zcat %s > %s" \
                      % (cache_sources + ".gz", cache_sources))
            os.unlink(cache_sources + ".gz")

        print "Done."

        sys.exit(0)

# initialize python apt bindings
apt_pkg.init()

# parse comps.xml using Red Hat's comps module
comps = rhpl.comps.Comps(comps_xml)

# create binary-i386 and source directories if they don't already exist
if not os.path.exists("./binary-i386"):
    os.mkdir("binary-i386")
if not os.path.exists("./source"):
    os.mkdir("source")

# determine the upstream uri given UPSTREAM_ID

cache_packages = glob.glob(cachedir + "/Packages.%s.*" % (upstream_id))[0]
cache_sources = glob.glob(cachedir + "/Sources.%s.*" % (upstream_id))[0]
cache_packages_basename = os.path.basename(cache_packages)
url_base = urllib.unquote_plus(cache_packages_basename[len(upstream_id) + 10:])
m = re.search("dists", url_base)
upstream_apt_uri = url_base[0:m.start() - 1]

# extract the information we need from the local Packages and
# Sources and the upstream Packages and Sources.. we end up
# with two dictionaries, PACKAGES and PACKAGES_UPSTREAM, that
# map package names to a [version, binary package filename,
# source package directory, source package filename(s)] tuple

packages = {}
packages_upstream = {}
sources = {}
sources_upstream = {}

# initialize PACKAGES to contain all packages listed in comps.xml;
# this handles the case where the upstream Packages knows about a
# package but the local Packages doesn't
for group in comps.groups.values():
    for (type, package) in group.packages.values():
        packages[package] = ["0", "", "", []]

# seed the SOURCES dictionary with information from the Sources file
if os.path.exists("./source/Sources"):
    sources_file = apt_pkg.ParseTagFile(open("./source/Sources", "r"))
    while sources_file.Step() == 1:
        package = sources_file.Section.get("Package")
        version = sources_file.Section.get("Version")
        directory = sources_file.Section.get("Directory")
        file_list = sources_file.Section.get("Files")
        # the Files section contains an md5sum per line, so every
        # 3rd string in FILES is a file name
        i = 1
        files = []
        for s in string.split(file_list):
            if i % 3 == 0:
                files.append(s)
            i = i + 1
        sources[package] = [version, directory, files]

# seed the PACKAGES dictionary with information from the Packages file,
# pulling the appropriate information from the SOURCES dictionary
if os.path.exists("./binary-i386/Packages"):
    packages_file = apt_pkg.ParseTagFile(open("./binary-i386/Packages", "r"))
    while packages_file.Step() == 1:
        package = packages_file.Section.get("Package")
        version = packages_file.Section.get("Version")
        filename = packages_file.Section.get("Filename")
        source_package = packages_file.Section.get("Source")
        # if a Source line isn't specified, then the name of the source
        # package is the same as the name of the binary package
        if source_package is None:
            source_package = package
        # if the Source line includes a version number (in parenthesis
        # after the name), then use it; otherwise,
        # the version is the same as the version of the binary package
        m = re.search("\\(\S+\\)", source_package)
        if m is None:
            source_version = version
        else:
            source_version = source_package[m.start()+1:m.end()-1]
            source_package = source_package[:m.start()-1]
        if sources.has_key(source_package):
            #if sources[source_package][0] != source_version:
            #    # XXX probably need to do something here more than warn
            #    print "warning: version mismatch for source package `%s' " \
            #          "(expected %s, got %s)" \
            #          % (source_package, source_version, \
            #             sources[source_package][0])
            source_directory = sources[source_package][1]
            source_files = sources[source_package][2]
            packages[package] = [version, filename, source_directory, \
                                 source_files]
        #else:
        #    print "warning: could not find source package for binary " \
        #          "package `%s' (`%s')" % (package, source_package)

# do the same for the upstream Packages and Sources files

sources_file = apt_pkg.ParseTagFile(open(cache_sources, "r"))
while sources_file.Step() == 1:
    package = sources_file.Section.get("Package")
    version = sources_file.Section.get("Version")
    directory = sources_file.Section.get("Directory")
    file_list = sources_file.Section.get("Files")
    # the Files section contains an md5sum per line, so every
    # 3rd string in FILES is a file name
    i = 1
    files = []
    for s in string.split(file_list):
        if i % 3 == 0:
            files.append(s)
        i = i + 1
    sources_upstream[package] = [version, directory, files]

packages_file = apt_pkg.ParseTagFile(open(cache_packages, "r"))
while packages_file.Step() == 1:
    package = packages_file.Section.get("Package")
    version = packages_file.Section.get("Version")
    filename = packages_file.Section.get("Filename")
    source_package = packages_file.Section.get("Source")
    # if a Source line isn't specified, then the name of the source
    # package is the same as the name of the binary package
    if source_package is None:
        source_package = package
    # if the Source line includes a version number (in parenthesis
    # after the name), then use it; otherwise,
    # the version is the same as the version of the binary package
    m = re.search("\\(\S+\\)", source_package)
    if m is None:
        source_version = version
    else:
        source_version = source_package[m.start()+1:m.end()-1]
        source_package = source_package[:m.start()-1]
    if sources_upstream.has_key(source_package):
        #if sources_upstream[source_package][0] != source_version:
        #    # XXX probably need to do something here more than warn
        #    print "warning: version mismatch for source package `%s' " \
        #          "(expected %s, got %s)" \
        #          % (source_package, source_version, \
        #             sources_upstream[source_package][0])
        source_directory = sources_upstream[source_package][1]
        source_files = sources_upstream[source_package][2]
        packages_upstream[package] = [version, filename, source_directory, \
                                      source_files]
    #else:
    #    print "warning: could not find source package for binary " \
    #          "package `%s' (`%s')" % (package, source_package)

# now, for every package in PACKAGES, compare with the version in
# PACKAGES_UPSTREAM, and if there's a newer version upstream,
# download it (unless the --dry-run flag is set, in which case we
# just print a message)

for package in packages.keys():
    version = packages[package][0]
    if packages_upstream.has_key(package):
        version_upstream = packages_upstream[package][0]
    else:
        print "warning: package `%s' does not exist upstream" % package
        # set to "" so it will never be newer
        version_upstream = ""
    if apt_pkg.VersionCompare(version_upstream, version) > 0:
        # get the binary package
        url = upstream_apt_uri + "/" + packages_upstream[package][1]
        print "Downloading %s..." % url
        if not dryrun:
            os.chdir("./binary-i386")
            # download new version
            newfile = os.path.basename(packages_upstream[package][1])
            #urllib.urlretrieve(url, newfile)
            os.system("wget -O %s %s" % (newfile, url))
            # remove old version
            oldfile = os.path.basename(packages[package][1])
            if os.path.exists(oldfile):
                os.unlink(oldfile)
            os.chdir("..")
        # get the source package
        dir = packages_upstream[package][2]
        for file in packages_upstream[package][3]:
            url = upstream_apt_uri + "/" + dir + "/" + file
            print "Downloading %s..." % url
            if not dryrun:
                os.chdir("./source")
                # download new version
                newfile = os.path.basename(file)
                # XXX should check md5sum here..
                if not os.path.exists(newfile):
                    #urllib.urlretrieve(url, newfile)
                    os.system("wget -O %s %s" % (newfile, url))
                os.chdir("..")
        for file in packages[package][3]:
            if not dryrun:
                os.chdir("./source")
                # remove old version
                oldfile = os.path.basename(file)
                if os.path.exists(oldfile):
                    # don't remove the file if just downloaded it
                    # XXX kludge
                    delete = 1
                    for f in packages_upstream[package][3]:
                        if os.path.basename(f) == oldfile:
                            delete = 0
                    if delete:
                        os.unlink(oldfile)
                os.chdir("..")

# create the APT repo metadata

# XXX this is currently pretty inflexibile and assumes the
# Progeny layout convention of dists/cl/COMPONENT/...

# We assume the group with an id that comes first alphabetically is
# the name of the component repository, due to our naming conventions
# for components (<foo>, <foo>-devel, <foo>-i18n-<lang> etc.). This
# is inflexible too and should eventually be specified in comps.xml
# directly.

def compare_groups(group1, group2):
    if group1.id < group2.id:
        return -1
    elif group1.id > group2.id:
        return 1
    else:
        return 0

k = comps.groups.values()
k.sort(compare_groups)
id = k[0].id; name = k[0].name

os.chdir("../../../")
os.system("apt-ftparchive packages dists/cl/%s/binary-i386 " \
    "> dists/cl/%s/binary-i386/Packages" % (id, id))
os.chdir("./dists/cl/%s" % id)
os.chdir("./binary-i386")
os.system("gzip -c Packages > Packages.gz")
f = open("./Release", "w")
f.write("Archive: cl\n")
f.write("Component: %s\n" % id)
f.write("Version: 3.0.0\n")
f.write("Label: %s\n" % name)
f.write("Architecture: i386\n")
f.write("Origin: Progeny\n")
f.close()
os.chdir("..")
os.chdir("../../../")
os.system("apt-ftparchive sources dists/cl/%s/source " \
    "> dists/cl/%s/source/Sources" % (id, id))
os.chdir("./dists/cl/%s" % id)
os.chdir("./source")
os.system("gzip -c Sources > Sources.gz")
os.chdir("..")

print "Component updated."
