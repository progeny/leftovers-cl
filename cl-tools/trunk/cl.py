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

import sys
import os
import string
import re
import filecmp
import shutil
import httplib
import urlparse
import urllib

import cPickle as pickle
# import pickle

import apt_pkg
import rhpl.comps

_default_config = { "Dir::Comps": "var/lib/cl-tools/comps/",
                    "Dir::Comps::InstalledState": "component.status" }

# Installed status is stored as a directory of dictionaries, indexed by
# component ID, with each value corresponding to a component.  The
# following fields are defined:
#   id:        Component id
#   follow:    Whether we should try to keep this component fully installed
#   status:    Component status relative to the available list
#     values: none, partial, complete, legacy
#   installed: List of installed packages from this component
#   missing:   List of packages not installed from this component
#   obsolete:  List of packages no longer part of this component

_istatus = {}

# This checks to make sure that there's a status entry for a given
# component, and creates it if not.  Callers of this function should
# also check for the "new" status and set it appropriately.
def _check_istatus(id):
    global _istatus

    defaults = { "id": id,
                 "follow": False,
                 "missing": [],
                 "installed": [],
                 "obsolete": [],
                 "status": "new" }

    if not _istatus.has_key(id):
        _istatus[id] = {}

    for key in defaults.keys():
        if not _istatus[id].has_key(key):
            _istatus[id][key] = defaults[key]

def _retrieve_config_dir_path(key):
    path = ""
    config_key = key
    while len(path) < 1 or path[0] != "/":
        path = apt_pkg.Config[config_key] + path
        config_key = string.join(string.split(config_key, "::")[:-1], "::")
    return path

def _get_installed_pkgs():
    status_path = _retrieve_config_dir_path("Dir::State::status")

    installed_pkgs = []
    status_f = open(status_path)

    status_parser = apt_pkg.ParseTagFile(status_f)
    while status_parser.Step():
        pkg_status = status_parser.Section["Status"]
        if string.find(pkg_status, "not-installed") != -1 or\
           string.find(pkg_status, "config-files") != -1:
            continue
        installed_pkgs.append(status_parser.Section["Package"])

    status_f.close()
    return installed_pkgs

def init(options, argv):
    global _default_config
    global _istatus

    apt_pkg.InitConfig()

    for key in _default_config.keys():
        apt_pkg.Config[key] = _default_config[key]

    args = apt_pkg.ParseCommandLine(apt_pkg.Config, options, argv)

    apt_pkg.InitSystem()

    istatus_path = _retrieve_config_dir_path("Dir::Comps::InstalledState")
    if os.path.exists(istatus_path):
        istatus_f = open(istatus_path)
        _istatus = pickle.load(istatus_f)
        istatus_f.close()
    else:
        _quick_status("No installed status file found; creating one.")
        update_installed()

    return args

# Use a callback system to report status.

class StatusItem:
    def __init__(self, callback, init_msg = None):
        self.callback = callback
        self.percentage = 0
        if init_msg:
            self.current_message = init_msg
            self.do_callback()

    def _default_callback(self):
        print self.current_message

    def do_callback(self):
        if self.callback:
            self.callback(self)
        else:
            self._default_callback()

    def message(self, message, percent = None):
        self.current_message = message
        if percent:
            self.percentage = percent
        self.do_callback()

    def set_percentage(self, percent):
        self.percentage = percent
        self.do_callback()

    def get_info(self):
        return (self.current_message, self.percentage)

class StatusDict(dict):
    def __init__(self, **kw):
        dict.__init__(self)
        for key in kw.keys():
            self[key] = kw[key]

    def __str__(self):
        return self["message"]

class ComponentError(StandardError):
    pass

status_cb = None

def register_status_cb(cb):
    global status_cb
    status_cb = cb

def _new_status(message):
    global status_cb
    return StatusItem(status_cb, message)

def _quick_status(message):
    global status_cb
    StatusItem(status_cb).message(message, 100)

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
        if len(items) < 1:
            continue
        if items[0] in recognized_repo_types:
            repos.append((items[0], items[1], items[2], tuple(items[3:])))

    return tuple(repos)

def update_apt():
    os.system("aptitude update")

def update_available():
    global _istatus

    do_status_update = False
    compsdir = _retrieve_config_dir_path("Dir::Comps")

    old_comps_xml_list = os.listdir(compsdir)

    for (fmt, uri, dist, comps) in parse_sources_list():
        if fmt == "deb":
            # For each (APT) component, construct a URL to
            # the comps.xml file and check if it exists in
            # a protocol-specific way.
            for comp in comps:
                status = _new_status("  Checking %s/%s..." % (dist, comp))

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
                        status.message("not a component.", 100)
                        continue
                elif proto == "file":
                    # Check the file system to verify that comps.xml
                    # exists:
                    if not os.path.exists(path):
                        status.message("not a component.", 100)
                        continue
                else:
                    status.message("protocol `%s' not supported." % proto, 100)
                    continue

                # Download the comps.xml and save it to COMPSDIR:
                comps_xml = "%s/%s.xml" % (compsdir, comp)
                comps_xml_tmp = "%s/.%s.xml" % (compsdir, comp)
                urllib.urlretrieve(url, comps_xml_tmp)

                # Remove the XML file from the list of "old" files;
                # once we're done, the list will only contain files
                # not updated.
                if os.path.basename(comps_xml) in old_comps_xml_list:
                    old_comps_xml_list.remove(os.path.basename(comps_xml))

                if os.path.exists(comps_xml):

                    # No change?  Keep the old one.
                    if filecmp.cmp(comps_xml, comps_xml_tmp):
                        os.unlink(comps_xml_tmp)
                        status.message("up-to-date.", 100)
                        continue

                    # Check for removed packages.
                    comps = rhpl.comps.Comps(comps_xml_tmp)

                    for group in comps.groups.values():

                        # If we find brand-new components, be sure to
                        # do a status update when we're done.
                        _check_istatus(group.id)
                        if _istatus[group.id]["status"] == "new":
                            do_status_update = True
                            continue

                        # Don't bother with components we're not following.
                        if not _istatus[group.id]["follow"]:
                            continue

                        # Get a list of packages referred to in this group.
                        # Package types don't matter here, since any
                        # reference means the package is not obsolete.
                        packages = map(lambda x: x[1], group.packages.values())

                        # Go through the current installed list and mark
                        # all removed packages as obsolete.
                        for pkg in _istatus[group.id]["installed"]:
                            if pkg not in packages:
                                _istatus[group.id]["obsolete"].append(pkg)

                os.rename(comps_xml_tmp, comps_xml)

                status.message("updated.", 100)

    # Get rid of comps files we didn't download.
    for comps_fn in old_comps_xml_list:
        if comps_fn[-4:] == ".xml":
            os.unlink("%s/%s" % (compsdir, comps_fn))

    if do_status_update:
        status = _new_status("New components found, updating installed status...")
        update_installed()
        status.message("done.", 100)

def update_installed():
    global _istatus

    compsdir = _retrieve_config_dir_path("Dir::Comps")
    istatus_path = _retrieve_config_dir_path("Dir::Comps::InstalledState")

    current_components = []

    # Get a list of installed packages.
    installed_pkgs = _get_installed_pkgs()

    # Now look at each available component to see what's installed.
    for file in os.listdir(compsdir):

        # Parse the component comps.xml.
        comps_xml = "%s/%s" % (compsdir, file)

        m = re.search("\S+\\.xml", file)
        if m is None:
            continue
        else:
            file_id = file[m.start():m.end() - 4]

        comp = rhpl.comps.Comps(comps_xml)

        # Compare each group in the file.
        for group in comp.groups.values():

            # Remember that we've seen this component.
            current_components.append(group.id)

            # Check for new component (or upgrading from old cl-tools).
            _check_istatus(group.id)

            # Clear out the old package lists.
            missing = []
            installed = []
            missing_optional = []

            # Look through the package list for missing and installed
            # packages.
            for (type, package) in group.packages.values():
                if package not in installed_pkgs:
                    if type in ("mandatory", "default"):
                        missing.append(package)
                    else:
                        # XXX: We don't use this yet, but we could.
                        missing_optional.append(package)
                else:
                    installed.append(package)

            # Set the new status.
            if len(missing):
                if len(installed):
                    new_status = "partial"
                else:
                    new_status = "none"
            else:
                if not len(installed):
                    new_status = "none"
                else:
                    new_status = "complete"

                    # If this is a new component and it's completely
                    # installed, assume it was installed explicitly.
                    if _istatus[group.id]["status"] == "new":
                        _istatus[group.id]["follow"] = True

            # Check the obsolete list for removed packages.
            obsolete = _istatus[group.id]["obsolete"][:]

            for package in obsolete:
                if package not in installed_pkgs:
                    obsolete.remove(package)

            # Apply all the changes.
            _istatus[group.id]["status"] = new_status
            _istatus[group.id]["missing"] = missing
            _istatus[group.id]["installed"] = installed
            _istatus[group.id]["obsolete"] = obsolete

    # Now look for components that have disappeared, and remove
    # them from the status file if they aren't important.
    for component in _istatus.keys():
        if component not in current_components:
            if not _istatus[component]["follow"]:
                del _istatus[component]
            else:
                _istatus[component]["status"] = "legacy"

    # We're done.  Save the installed status for next time.
    istatus_f = open(istatus_path, "w")
    pickle.dump(_istatus, istatus_f)
    istatus_f.close()

def install(id):
    global _istatus

    if not _istatus.has_key(id):
        raise ComponentError, "Component %s not found (did you run --update?)"\
              % id

    if _istatus[id]["status"] == "complete":
        _quick_status("Component %s is up to date." % id)
        return

    # Build the list of packages to install:
    packages = string.join(_istatus[id]["missing"], " ")

    # Call aptitude install to install PACKAGES_TO_INSTALL:
    os.system("aptitude install %s" % packages)

    # Update the installed list.
    status = _new_status("Updating list of installed components...")
    _istatus[id]["follow"] = True
    update_installed()
    status.message("done.", 100)

def remove(id):
    global _istatus

    if not _istatus.has_key(id):
        raise ComponentError, "Component %s not found (did you run --update?)"\
              % id

    if _istatus[id]["status"] == "none":
        raise ComponentError, "Component %s not installed." % id

    # Build the list of packages to remove:
    packages_to_remove = []
    for package in _istatus[id]["installed"]:
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

    # Update the installed list.
    status = _new_status("Updating list of installed components...")
    _istatus[id]["follow"] = False
    update_installed()
    status.message("done.", 100)

def upgrade():
    global _istatus

    # Look for packages to install and remove.
    packages_to_install = []
    packages_to_remove = []
    valid_packages = reduce(lambda x,y: x + y["installed"],
                            [[]] + list(_istatus.values()))

    for id in _istatus.keys():
        if _istatus[id]["follow"]:
            packages_to_install.extend(_istatus[id]["installed"])

            for package in _istatus[id]["obsolete"]:
                if package not in valid_packages:
                    packages_to_remove.append(package)

    # Install or upgrade member packages.
    packages = string.join(packages_to_install, " ")
    retval = os.system("aptitude install " + packages)
    if retval:
        raise RuntimeError, "could not upgrade components"

    # Remove packages that have been removed from components, if any.
    if len(packages_to_remove):
        packages = string.join(packages_to_remove, " ")
        os.system("dpkg --remove " + packages)

    # Take care of the rest of the packages upgrades that we may need.
    _quick_status("Upgrading non-component packages...")
    os.system("aptitude upgrade")

    # Update the installed list.
    status = _new_status("Updating list of installed components...")
    _istatus[id]["follow"] = False
    update_installed()
    status.message("done.", 100)

def get_available():
    global _istatus

    available = list(_istatus.keys())
    available.sort()
    return tuple(available)

def get_extra_packages():
    global _istatus

    comp_pkgs = reduce(lambda x,y: x[:] + y[:],
                       map(lambda x: x["installed"], _istatus.values()))

    nocomp_pkgs = []
    for pkg in _get_installed_pkgs():
        if pkg not in comp_pkgs:
            nocomp_pkgs.append(pkg)

    nocomp_pkgs.sort()
    return tuple(nocomp_pkgs)

def _get_by_status(status_list):
    global _istatus

    match = []
    for id in _istatus.keys():
        if _istatus[id]["status"] in status_list:
            match.append(id)

    match.sort()
    return tuple(match)

def get_installed():
    return _get_by_status(("complete", "legacy"))

def get_partial():
    return _get_by_status(("partial",))

def get_legacy():
    return _get_by_status(("legacy",))
