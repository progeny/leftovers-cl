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
import string
import apt_pkg
import filecmp
import getopt
import httplib
import re
import rhpl.comps
import shutil
import urllib
import urlparse

sys.path.append("/usr/share/cl-tools")
import cl

cachedir = "/var/lib/cl-tools"
compsdir = cachedir + "/comps"
availabledir = compsdir + "/available"
installeddir = compsdir + "/installed"

sources_list = "/etc/apt/sources.list"

# For each source in SOURCES_LIST, check the source for a comps.xml,
# and if one exists, download it and save it to COMPSDIR; then, for
# each subcomponent, create a link to the comps.xml in
# AVAILABLEDIR using the subcomponent name, so the user can
# manipulate it using that name. Also call "aptitude update" so
# the APT database is up to date with any component updates.
def comps_update():
    os.system("aptitude update")

    print "Updating component metadata:"

    for (fmt, uri, dist, comps) in cl.parse_sources_list(sources_list):
        if fmt == "deb":
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

                # Download the comps.xml and save it to COMPSDIR:
                comps_xml = "%s/%s.xml" % (compsdir, comp)
                comps_xml_tmp = "%s/.%s.xml" % (compsdir, comp)
                urllib.urlretrieve(url, comps_xml_tmp)
                if os.path.exists(comps_xml):
                    if filecmp.cmp(comps_xml, comps_xml_tmp):
                        os.unlink(comps_xml_tmp)
                        print "up-to-date."
                        continue
                os.rename(comps_xml_tmp, comps_xml)

                # Create links to the downloaded comps.xml in
                # AVAILABLEDIR using each of the subcomponent names,
                # so they can be manipulated using the names:
                comp = rhpl.comps.Comps(comps_xml)
                for group in comp.groups.values():
                    comps_xml_sub = "%s/%s.xml" % (availabledir, group.id)
                    if not os.path.exists(comps_xml_sub):
                        os.symlink(comps_xml, comps_xml_sub)

                print "updated."

    print "Done."

# Install the component ID.
def comp_install(id):
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
    packages_to_install = []
    for group in comp.groups.values():
        # Only add the packages in the subcomponent ID, not the other
        # subcomponents.
        if group.id != id:
            continue
        for (type, package) in group.packages.values():
            # Only add the "mandatory" and "default" packages:
            if type == "mandatory" or type =="default":
                packages_to_install.append(package)

    packages = string.join(packages_to_install, " ")

    # Call aptitude install to install PACKAGES_TO_INSTALL:
    os.system("aptitude install %s" % packages)

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
    packages_to_remove = []
    for group in comp.groups.values():
        # Only remove the packages in the subcomponent ID, not the
        # other subcomponents.
        if group.id != id:
            continue
        for (type, package) in group.packages.values():
            # Verify that the package is actually installed before adding
            # it to the list, to suppress spurious warnings:
            if not os.path.exists("/var/lib/dpkg/info/%s.list" % package):
                continue
            packages_to_remove.append(package)

    # XXX need to be smarter here about only removing packages that
    # aren't depended upon by a package in another component..

    packages = string.join(packages_to_remove, " ")

    # Call aptitide remove to remove PACKAGES_TO_REMOVE:
    # XXX we always succeed here, pending implementation of the above
    # check ("need to be smarter here...")
    os.system("dpkg --remove %s" % packages)

    # Remove the comps.xml used during installation from INSTALLEDDIR:
    os.unlink(comps_xml_installed)

# Upgrade installed components to current versions.
def comps_upgrade():
    components_updated = []
    packages_to_install = []
    packages_to_remove = []

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

        # Build dictionaries of available and installed packages, for
        # use in determining which packages have been added and which
        # packages have been removed from the component:

        packages_available = {}
        for group in comp_available.groups.values():
            # Only add the packages in the subcomponent ID, not the
            # other subcomponents.
            if group.id != id:
                continue
            for (type, package) in group.packages.values():
                # Only add the "mandatory" and "default" packages:
                if type == "mandatory" or type =="default":
                    packages_available[package] = True

        packages_installed = {}
        for group in comp_installed.groups.values():
            # Only add the packages in the subcomponent ID, not the
            # other subcomponents.
            if group.id != id:
                continue
            for (type, package) in group.packages.values():
                # Only add the "mandatory" and "default" packages:
                if type == "mandatory" or type =="default":
                    packages_installed[package] = True

        # Each package in the PACKAGES_AVAILABLE dictionary that is not
        # in the PACKAGES_INSTALLED dictionary is a new package. Add it
        # to the list of packages to be installed:
        for package in packages_available.keys():
            if not packages_installed.has_key(package):
                packages_to_install.append(package)

        # Each package in the PACKAGES_INSTALLED dictionary that
        # is not in the PACKAGES_AVAILABLE dictionary is a package that
        # has been removed. Add it to the list of packages to be
        # removed.
        for package in packages_installed.keys():
            if not packages_available.has_key(package):
                packages_to_remove.append(package)

        components_updated.append(id)

    # Deal with the case where a package has moved from one component
    # to another (i.e., don't remove it):
    for package in packages_to_remove:
        try:
            i = packages_to_install.index(package)
        except ValueError, e:
            continue
        if i >= 0:
            packages_to_remove.remove(package)
            
    os.system("aptitude upgrade")

    # Install packages that have been added to a component:
    packages = string.join(packages_to_install, " ")
    if packages != "":
        os.system("aptitude install %s" % packages)

    # Remove packages that have been removed from a component:
    packages = string.join(packages_to_remove, " ")
    if packages != "":
        # XXX we always succeed here too (see comp_remove)
        os.system("dpkg --remove %s" % packages)

    os.system("aptitude upgrade")

    for id in components_updated:
        comps_xml_available = "%s/%s.xml" % (availabledir, id)
        comps_xml_installed = "%s/%s.xml" % (installeddir, id)
        # Update the comps.xml used during installation in INSTALLEDDIR:
        shutil.copy(comps_xml_available, comps_xml_installed)

# List the components currently available.
def comps_list_available():
    available = []
    for file in os.listdir(availabledir):
        m = re.search("\S+\\.xml", file)
        if m is None:
            # Eh?
            continue
        else:
            id = file[m.start():m.end() - 4]
        available.append(id)

    available.sort()

    for package in available:
        print package

# List the components currently installed.
def comps_list_installed():
    installed = []
    for file in os.listdir(installeddir):
        m = re.search("\S+\\.xml", file)
        if m is None:
            # Eh?
            continue
        else:
            id = file[m.start():m.end() - 4]
        installed.append(id)

    installed.sort()

    for package in installed:
        print package

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
  install COMPONENT  Install the component COMPONENT via the aptitude
                     command
  remove COMPONENT   Remove the component COMPONENT via the aptitude
                     command  
  upgrade            Upgrade installed components to current versions
                     via the aptitude command
  list-available     List the components currently available
  list-installed     List the components currently installed""" % \
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

    options = [ 'purge' ]

    purge = False

    try:
        opts, args = getopt.getopt(sys.argv[2:], '', options)
    except getopt.GetoptError, e:
        print e
        usage(1)
    for opt in opts:
        if opt[0] == "--purge":
            # XXX not actually used yet
            purge = True
                                
    # initialize apt_pkg:
    apt_pkg.init()

    if update:
        if len(args) != 0:
            usage(1)
        comps_update()
    elif install:
        if len(args) != 1:
            usage(1)
        comp_install(args[0])
    elif remove:
        if len(args) != 1:
            usage(1)
        comp_remove(args[0])
    elif upgrade:
        if len(args) != 0:
            usage(1)
        comps_upgrade()
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
