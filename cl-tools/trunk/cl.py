#! /usr/bin/python
#
# cl.py: library routines for use in cl-tools
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
# Written by Ian Murdock <imurdock@progeny.com>
#         and Jeff Licquia <licquia@progeny.com>.

import apt_pkg
import rhpl.comps

default_config = { "Dir::Comps": "var/lib/cl-tools/comps",
                   "Dir::Comps::Available": "available",
                   "Dir::Comps::Installed": "installed" }

def _retrieve_config_dir_path(key):
    path = ""
    while len(path) < 1 or path[0] != "/":
        path = apt_pkg.Config[config_key] + path
        config_key = string.join(string.split(config_key, "::")[:-1], "::")
    return path

def init(options, argv):
    global default_config

    apt_pkg.InitConfig()

    for key in default_config.keys():
        apt_pkg.Config[key] = default_config[key]

    args = apt_pkg.ParseCommandLine(apt_pkg.Config, options, argv)

    apt_pkg.InitSystem()

    return args

# Use a callback system to report status.

status_cb = None

def register_status_cb(cb):
    global status_cb
    status_cb = cb

def status(s):
    if status_cb:
        status_cb(s)

# XXX apt_pkg should provide some mechanism for iterating over
# the lines in sources.list. It's pretty silly that we have to
# parse it ourselves.

def parse_sources_list(path = None):
    recognized_repo_types = ("deb", "deb-src")

    if path is None:
        path = _retrieve_config_dir_path("Dir::Etc::SourceList")

    repos = []
    f = open(path)
    for line in f:
        items = line.split()
        if items[0] in recognized_repo_types:
            repos.append((items[0], items[1], items[2], tuple(items[3:])))

    return tuple(repos)

def update_apt():
    os.system("aptitude update")

def update_available():
    compsdir = _retrieve_config_dir_path("Dir::Comps")
    availabledir = _retrieve_config_dir_path("Dir::Comps::Available")

    for (fmt, uri, dist, comps) in cl.parse_sources_list():
        if fmt == "deb":
            # For each (APT) component, construct a URL to
            # the comps.xml file and check if it exists in
            # a protocol-specific way.
            for comp in comps:
                status("  Checking %s/%s..." % (dist, comp))

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
                        status("not a component.")
                        continue
                elif proto == "file":
                    # Check the file system to verify that comps.xml
                    # exists:
                    if not os.path.exists(path):
                        status("not a component.")
                        continue
                else:
                    status("protocol `%s' not supported." % proto)
                    continue

                # Download the comps.xml and save it to COMPSDIR:
                comps_xml = "%s/%s.xml" % (compsdir, comp)
                comps_xml_tmp = "%s/.%s.xml" % (compsdir, comp)
                urllib.urlretrieve(url, comps_xml_tmp)
                if os.path.exists(comps_xml):
                    if filecmp.cmp(comps_xml, comps_xml_tmp):
                        os.unlink(comps_xml_tmp)
                        status("up-to-date.")
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

                status("updated.")

def install(id):
    availabledir = _retrieve_config_dir_path("Dir::Comps::Available")
    installeddir = _retrieve_config_dir_path("Dir::Comps::Installed")
    comps_xml_available = "%s/%s.xml" % (availabledir, id)
    comps_xml_installed = "%s/%s.xml" % (installeddir, id)

    if os.path.exists(comps_xml_installed):
        status("Component %s already installed." % id)
        return

    if not os.path.exists(comps_xml_available):
        status("Component %s not found (did you run --update?)" % id)
        return

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
