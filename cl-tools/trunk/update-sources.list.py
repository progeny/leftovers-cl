#! /usr/bin/python
#
# update-sources.list --
#
#       Update /etc/apt/sources.list with the sources.list fragments
#       in /etc/apt/sources.list.d.
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
import shutil
import tempfile

sources_list = "/etc/apt/sources.list"
sources_list_d = "/etc/apt/sources.list.d"

magic_value_begin = "### begin-auto"
magic_value_end = "### end-auto"

def main():
    if len(sys.argv) != 0:
        print "Usage: %s" % sys.argv[0]
        sys.exit(1)

    if not os.path.exists(sources_list_d):
        print "%s: %s does not exist (exiting)" % (sys.argv[0], sources_list_d)
        sys.exit(1)

    # Make a backup of SOURCES_LIST:
    shutil.copy(sources_list, sources_list + ".bak")

    sources_list_new = tempfile.mktemp()

    file_old = open(sources_list, "r")
    file_new = open(sources_list_new, "w")

    # Copy SOURCES_LIST to SOURCES_LIST_NEW up to the point where
    # MAGIC_VALUE_BEGIN is found:
    line = file_old.readline()
    magic_value_begin_found = False
    while line:
        if line[0:len(magic_value_begin)] == magic_value_begin:
            magic_value_begin_found = True
            break
        file_new.write(line)
        line = file_old.readline()

    # If MAGIC_VALUE_BEGIN was never found, exit now:
    if not magic_value_begin_found:
        file_old.close()
        file_new.close()
        os.unlink(sources_list_new)
        sys.exit(0)

    # Write MAGIC_VALUE_BEGIN, and a warning, to SOURCES_LIST_NEW:
    file_new.write(magic_value_begin)
    file_new.write("\n")
    file_new.write("# Do not edit between the lines marked \"%s\"" \
                   % magic_value_begin)
    file_new.write("\n")
    file_new.write("# and \"%s\"--these line are automatically managed" \
                   % magic_value_end)
    file_new.write("\n")
    file_new.write("# by update-sources.list and any changes to them will be")
    file_new.write("\n")
    file_new.write("# lost. Instead, edit the files in %s." % sources_list_d)
    file_new.write("\n")
        
    # Concatenate the files in SOURCES_LIST_D to SOURCES_LIST_NEW:
    sources_list_d_files = os.listdir(sources_list_d)
    sources_list_d_files.sort()
    for file in sources_list_d_files:
        file_new.write("\n")
        f = open(sources_list_d + "/" + file)
        l = f.readline()
        while l:
            file_new.write(l)
            l = f.readline()

    # Write MAGIC_VALUE_END to SOURCES_LIST_NEW:
    file_new.write(magic_value_end)
    file_new.write("\n")

    # Read and discard the lines between MAGIC_VALUE_BEGIN and
    # MAGIC_VALUE_END from SOURCES_LIST:
    while line:
        if line[0:len(magic_value_end)] == magic_value_end:
            break
        line = file_old.readline()

    # Copy the remainder of SOURCES_LIST to SOURCES_LIST_NEW:
    line = file_old.readline()
    while line:
        file_new.write(line)
        line = file_old.readline()

    file_old.close()
    file_new.close()

    # Copy the new sources.list into place:
    shutil.copy(sources_list_new, sources_list)

    os.unlink(sources_list_new)

    sys.exit(0)

if __name__ == "__main__":
    main()
