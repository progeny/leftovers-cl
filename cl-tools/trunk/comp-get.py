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

import sys
import apt_pkg

sys.path.append("/usr/share/cl-tools")
import cl

cachedir = "/var/lib/cl-tools"
compsdir = cachedir + "/comps"
availabledir = compsdir + "/available"
installeddir = compsdir + "/installed"

# For each source in SOURCES_LIST, check the source for a comps.xml,
# and if one exists, download it and save it to COMPSDIR; then, for
# each subcomponent, create a link to the comps.xml in
# AVAILABLEDIR using the subcomponent name, so the user can
# manipulate it using that name. Also call "aptitude update" so
# the APT database is up to date with any component updates.
def comps_update():
    cl.update_apt()

    print "Updating component metadata:"
    cl.update_available()

    print "Done."

# List the components currently available.
def comps_list_available():
    for package in cl.get_available():
        print package

# List the components currently installed.
def comps_list_installed():
    for package in cl.get_installed():
        print package

def status_cb(s):
    print s

def main():
    action_list = { "update": (comps_update, False),
                    "install": (cl.install, True),
                    "remove": (cl.remove, True),
                    "upgrade": (cl.upgrade, False),
                    "list-available": (comps_list_available, False),
                    "list-installed": (comps_list_installed, False) }

    def usage(status):
        print """Usage: %s [OPTIONS] COMMAND [COMPONENT]

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
    purge = False
    options = [ ('p', 'purge', "APT::Get::Purge") ]
    args = cl.init(options, sys.argv)
    if apt_pkg.Config.has_key("APT::Get::Purge"):
        purge = apt_pkg.Config["APT::Get::Purge"]

    action = args.pop(0)
    if action not in action_list.keys():
        usage(1)

    cl.register_status_cb(status_cb)

    (action_call, param) = action_list[action]
    if (param and len(args) < 1) or (not param and len(args) > 0):
        usage(1)

    try:
        if param:
            action_call(args[0])
        else:
            action_call()
    except Exception, e:
        print str(e)

if __name__ == "__main__":
    main()
