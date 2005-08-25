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

# JS5.sh
# $Progeny$
#
# test Jam 5 functional requirements

# get Utility functions
. atest/test_lib.sh
. atest/utils/test_channel.sh


# -----------------------------------------------------------
# Initial customer workspace creation.
# -----------------------------------------------------------
pdk workspace create customer
pushd customer
    pushd work

# -----------------------------------------------------------
# setup: "create" a local file

        cp ${tmp_dir}/atest/abstract_comps/JS5-*.xml .
        cp JS5-1.xml JS5.xml
        
# execute: "add" and "commit" the file for version control
#          remove the file, and "update" from version control

        pdk add JS5.xml
        pdk commit Jam Session 5 testing
        rm JS5.xml
        pdk update

# evaluate: see if we got the file back from version control

        diff -u JS5.xml JS5-1.xml
        
# -----------------------------------------------------------
# setup: make a change to the file already in version control

        cp JS5-2.xml JS5.xml

# execute: commit the change to version control
#          remove the file, and update from vc

        pdk commit Jam Session 5 testing
        rm JS5.xml
        pdk update

# evaluate: see if we got our change back from version control

        diff -u JS5.xml JS5-2.xml

# -----------------------------------------------------------
# setup: make an undesired change to a file

        cp JS5-3.xml JS5.xml

# execute:
        pdk revert JS5.xml

# evaluate: see if the file is back in its original state
        diff -u JS5.xml JS5-2.xml

# -----------------------------------------------------------
# setup:
# execute: remove a file from version control

        pdk remove JS5.xml
        pdk commit Jam Session 5 testing

# evaluate: see if the file was actually removed

        pdk update
        test -f JS5.xml || gone=1
        if [ "$gone" != "1" ]; then
            bail "pdk remove JS5.xml failed"
        fi

# -----------------------------------------------------------
# More functions that need to be tested:
# -----------------------------------------------------------
        # pdk diff
        # pdk move some other other descriptor files
        # pdk cat
        # pdk update -r previous version
        # pdk revert
    popd
popd

# vim:ai:et:sts=4:sw=4:tw=0:
