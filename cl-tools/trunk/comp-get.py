#! /usr/bin/python
#
# comp-get --
#
#       A simple command-line component management tool.
#
# Copyright (C) 2004 Progeny Linux Systems, Inc.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published
# by the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty
# of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# Written by Ian Murdock <imurdock@progeny.com>.

import os
import sys
import apt_pkg
import filecmp
import getopt
import httplib
import re
import rhpl.comps
import shutil
import urllib
import urlparse

cachedir="/var/cache/cl-tools"
#cachedir="./cl-tools"
availabledir = cachedir + "/available"
installeddir = cachedir + "/installed"

sources_list = "/etc/apt/sources.list"

# For each source in SOURCES_LIST, check the source for a comps.xml,
# and if one exists, download it and save it to AVAILABLE_DIR.
# Also call "apt-get update" so the APT database is up to date with
# any component updates.
def comps_update():
    os.system("apt-get update")

    print "Updating component metadata:"

    # XXX apt_pkg should provide some mechanism for iterating over
    # the lines in sources.list. It's pretty silly that we have to
    # parse it ourselves.

    file = open(sources_list, "r")
    line = file.readline()
    lineno = 0
    while line:
        elem = line.split()
        if len(elem) != 0:
            fmt = elem[0]
            if fmt == "deb":
                # This is a "deb" line. Parse it into its constituent
                # elements (uri, dist, and comps).
                if len(elem) != 4:
                    print "%s: parse error at line %d" % (sources_list, lineno)
                    print "  %s" % line
                    sys.exit(1)
                uri = elem[1]
                dist = elem[2]
                comps = elem[3:]

                # For each (APT) component, construct a URL to
                # the comps.xml file and check if it exists in
                # a protocol-specific way.
                for comp in comps:
                    print "  Checking %s/%s..." % (dist, comp),

                    url = "%s/dists/%s/%s/comps.xml" % (uri, dist, comp)
                    (proto, host, path, x, y, z) = urlparse.urlparse(url)
                    if proto == "http":
                        # Connect to the HTTP server to verify that
                        # comps.xml exists:
                        h = httplib.HTTP(host)
                        h.putrequest("GET", path)
                        h.putheader("Host", host)
                        h.putheader("Accept", "application/xml")
                        h.endheaders()
                        (code, message, headers) = h.getreply()
                        if code != 200:
                            print "not a component."
                            continue
                    elif proto == "file":
                        # Check the file system to verify that comps.xml
                        # exists:
                        if not os.path.exists(path):
                            print "not a component."
                            continue
                    else:
                        print "protocol `%s' not supported." % proto
                        continue

                    # Download the comps.xml and save it to AVAILABLEDIR:
                    comps_xml = "%s/%s.xml" % (availabledir, comp)
                    comps_xml_tmp = "%s/.%s.xml" % (availabledir, comp)
                    urllib.urlretrieve(url, comps_xml_tmp)
                    if os.path.exists(comps_xml):
                        if filecmp.cmp(comps_xml, comps_xml_tmp):
                            os.unlink(comps_xml_tmp)
                            print "up-to-date."
                            continue
                    os.rename(comps_xml_tmp, comps_xml)
                    print "updated."
        line = file.readline()
        lineno = lineno + 1
    file.close()

    # XXX merge all comps.xml fragments into a single comps.xml file
    # and use that for further operations?

    print "Done."

# Install the component ID. If DEVEL is True, install the component's
# development support.
def comp_install(id, devel):
    comps_xml_available = "%s/%s.xml" % (availabledir, id)
    comps_xml_installed = "%s/%s.xml" % (installeddir, id)

    if os.path.exists(comps_xml_installed):
        print "Component %s already installed." % id
        sys.exit(1)

    if not os.path.exists(comps_xml_available):
        print "Component %s not found (did you run --update?)" % id
        sys.exit(1)

    # Parse comps.xml:
    comp = rhpl.comps.Comps(comps_xml_available)

    # Build the list of packages to install:
    packages = ""
    for group in comp.groups.values():
        # Only add the packages in the main component, unless DEVEL is
        # True.
        if group.id != id:
            if not (devel and group.id == id + "-devel"):
                continue
        for (type, package) in group.packages.values():
            # Only add the "mandatory" and "default" packages:
            if type == "mandatory" or type =="default":
                if packages == "":
                    packages = packages + package
                else:
                    packages = packages + " " + package

    # Call apt-get install to install PACKAGES:
    if os.system("apt-get install %s" % packages) != 0:
        # Installation failed:
        return

    # Copy the comps.xml used during installation to INSTALLEDDIR for
    # later use during upgrade and remove operations:
    shutil.copy(comps_xml_available, comps_xml_installed)

# Remove the component ID.
def comp_remove(id):
    comps_xml_installed = "%s/%s.xml" % (installeddir, id)

    if not os.path.exists(comps_xml_installed):
        print "Component %s not installed." % id
        sys.exit(1)

    # Parse comps.xml:
    comp = rhpl.comps.Comps(comps_xml_installed)

    # Build the list of packages to remove:
    packages = ""
    for group in comp.groups.values():
        for (type, package) in group.packages.values():
            # Verify that the package is actually installed before adding
            # it to the list, to suppress spurious warnings:
            if not os.path.exists("/var/lib/dpkg/info/%s.list" % package):
                continue
            if packages == "":
                packages = packages + package
            else:
                packages = packages + " " + package

    # Call dpkg --remove to remove PACKAGES:
    if os.system("dpkg --remove %s" % packages) != 0:
        # Removal failed:
        return

    # Remove the comps.xml used during installation from INSTALLEDDIR:
    os.unlink(comps_xml_installed)

# Upgrade installed components to current versions. If DEVEL is True,
# upgrade the components' development support.
def comps_upgrade(devel):
    for file in os.listdir(installeddir):
        comps_xml_available = "%s/%s" % (availabledir, file)
        comps_xml_installed = "%s/%s" % (installeddir, file)

        m = re.search("\S+\\.xml", file)
        if m is None:
            # Eh?
            continue
        else:
            id = file[m.start():m.end() - 4]

        if not os.path.exists(comps_xml_available):
            # No updated information for this component is available:
            continue

        if filecmp.cmp(comps_xml_installed, comps_xml_available):
            # Component is unchanged:
            continue

        # Parse comps.xml:
        comp_available = rhpl.comps.Comps(comps_xml_available)
        comp_installed = rhpl.comps.Comps(comps_xml_installed)

        # Build the list of packages in the newest version of the
        # component:
        packages_available = ""
        for group in comp_available.groups.values():
            # Only add the packages in the main component, unless
            # DEVEL is True.
            if group.id != id:
                if not (devel and group.id == id + "-devel"):
                    continue
            for (type, package) in group.packages.values():
                # Only add the "mandatory" and "default" packages:
                if type == "mandatory" or type =="default":
                    if packages_available == "":
                        packages_available = packages_available + package
                    else:
                        packages_available = packages_available + " " + package

        # Build the list of packages in the currently installed
        # version of the component:
        packages_installed = ""
        for group in comp_installed.groups.values():
            # Only add the packages in the main component, unless
            # DEVEL is True.
            if group.id != id:
                if not (devel and group.id == id + "-devel"):
                    continue
            for (type, package) in group.packages.values():
                # Only add the "mandatory" and "default" packages:
                if type == "mandatory" or type =="default":
                    if packages_installed == "":
                        packages_installed = packages_installed + package
                    else:
                        packages_installed = packages_installed + " " + package

        # Build dictionaries of available and installed packages, for
        # use in determining which packages have been added and which
        # packages have been removed from the component:

        available = {}
        for package in packages_available.split():
            available[package] = True

        installed = {}
        for package in packages_installed.split():
            installed[package] = True

        os.system("apt-get upgrade")

        # Each package in the AVAILABLE dictionary that is not in the
        # INSTALLED dictionary is a new package. Install it:
        packages = ""
        for package in available.keys():
            if not installed.has_key(package):
                if packages == "":
                    packages = packages + package
                else:
                    packages = packages + " " + package
        if packages != "":
            if os.system("apt-get install %s" % packages) != 0:
                # Installation failed:
                return

        # Each package in the INSTALLED dictionary that is not in the
        # AVAILABLE dictionary is a package that has been removed.
        # Remove it:
        packages = ""
        for package in installed.keys():
            if not available.has_key(package):
                if packages == "":
                    packages = packages + package
                else:
                    packages = packages + " " + package
        if packages != "":
            if os.system("dpkg --remove %s" % packages) != 0:
                # Removal failed:
                return

        # Update the comps.xml used during installation in INSTALLEDDIR:
        shutil.copy(comps_xml_available, comps_xml_installed)

# List the components currently available.
def comps_list_available():
    for file in os.listdir(availabledir):
        m = re.search("\S+\\.xml", file)
        if m is None:
            # Eh?
            continue
        else:
            id = file[m.start():m.end() - 4]

        print id

# List the components currently installed.
def comps_list_installed():
    for file in os.listdir(installeddir):
        m = re.search("\S+\\.xml", file)
        if m is None:
            # Eh?
            continue
        else:
            id = file[m.start():m.end() - 4]

        print id

def main():
    update = False
    install = False
    remove = False
    upgrade = False
    list_available = False
    list_installed = False

    def usage(status):
        print """Usage: %s COMMAND [OPTIONS] [COMPONENT]

Commands are:
  update             Update component information using sources from
                     /etc/apt/sources.list
  install COMPONENT  Install the component COMPONENT via the apt-get
                     command
  remove COMPONENT   Remove the component COMPONENT via the apt-get
                     command  
  upgrade            Upgrade installed components to current versions
                     via the apt-get command
  list-available     List the components currently available
  list-installed     List the components currently installed

Options are:
  --devel            Install component's development support""" \
          % sys.argv[0]
        sys.exit(status)

    # parse command line
    if sys.argv[1] == "update":
        update = True
    elif sys.argv[1] == "install":
        install = True
    elif sys.argv[1] == "remove":
        remove = True
    elif sys.argv[1] == "upgrade":
        upgrade = True
    elif sys.argv[1] == "list-available":
        list_available = True
    elif sys.argv[1] == "list-installed":
        list_installed = True
    else:
        usage(1)

    options = [ 'devel' ]

    devel = False

    try:
        opts, args = getopt.getopt(sys.argv[2:], '', options)
    except getopt.GetoptError, e:
        print e
        usage(1)
    for opt in opts:
        if opt[0] == "--devel":
            devel = True
                                
    # initialize apt_pkg:
    apt_pkg.init()

    if update:
        if len(args) != 0:
            usage(1)
        comps_update()
    elif install:
        if len(args) != 1:
            usage(1)
        comp_install(args[0], devel)
    elif remove:
        if len(args) != 1:
            usage(1)
        comp_remove(args[0])
    elif upgrade:
        if len(args) != 0:
            usage(1)
        comps_upgrade(devel)
    elif list_available:
        if len(args) != 0:
            usage(1)
        comps_list_available()
    elif list_installed:
        if len(args) != 0:
            usage(1)
        comps_list_installed()

if __name__ == "__main__":
    main()
