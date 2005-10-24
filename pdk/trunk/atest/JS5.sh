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

# -----------------------------------------------------------
# setup: "create" a local file

    cp ${tmp_dir}/atest/abstract_comps/JS5-*.xml .
    cp JS5-1.xml JS5.xml

# execute: "add" and "commit" the file for version control
#          remove the file, and "update" from version control

    pdk add JS5.xml
    pdk commit -m 'Jam Session 5 testing'
    rm JS5.xml
    pdk update

# evaluate: see if we got the file back from version control

    diff -u JS5.xml JS5-1.xml

# -----------------------------------------------------------
# setup: make a change to the file already in version control

    cp JS5-2.xml JS5.xml

# execute: commit the change to version control
#          remove the file, and update from vc

    pdk commit -m 'Jam Session 5 testing'
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
# setup: make a local change to a file

    cp JS5-3.xml JS5.xml

# execute: cat a file in version control

    pdk cat JS5.xml >> JS5-cat.xml

# evaluate: see if pdk reports the file in its original state

    diff -u JS5-cat.xml JS5-2.xml

# -----------------------------------------------------------
# setup:
# execute: remove a file from version control

    pdk remove JS5.xml || status=$?
    [ -f 'JS5.xml' ] || fail 'JS5.xml should still exist after pdk remove.'
    [ "$status" = 4 ] || fail 'pdk remove should fail when file exists'
    pdk commit -m 'Jam Session 5 testing'

    rm JS5.xml
    pdk remove JS5.xml
    pdk commit -m 'remove JS5'

    pdk status | egrep -q '^unknown: JS5.xml' \
        && fail 'JS5 should not be in version control.'

    cp JS5-1.xml JS5.xml
    pdk commit -m 'add it back' JS5.xml
    rm JS5.xml
    pdk remove JS5.xml
    pdk commit -m 'remove it with commit arg.' JS5.xml
    pdk status | egrep -q '^unknown: JS5.xml' \
        && fail 'JS5 should not be in version control.'

    cp JS5-1.xml a
    cp JS5-1.xml b

    pdk commit -m 'add two files: a b' a b
    rm a
    pdk commit -m 'rm a with args only' a \
        && fail 'should not be able to rm with args only'

    pdk status | egrep -q '^deleted: a' \
        && fail 'a should be in "deleted" state.'

    rm b
    pdk remove a b
    pdk commit -m 'rm both files at once.'

    pdk status | egrep -q '^unknown: a' \
        && fail 'a should not be in version control.'
    pdk status | egrep -q '^unknown: b' \
        && fail 'b should not be in version control.'


# do a more rigorous test of revert

    echo >>a 1
    echo >>b 1
    echo >>c 1
    pdk commit -m 'add a and b' a b c
    echo >>a 2
    echo >>b 2
    echo >>c 2
    pdk revert a c

    diff -u - a <<EOF
1
EOF
    diff -u - b <<EOF
1
2
EOF
    diff -u - c <<EOF
1
EOF

# -----------------------------------------------------------
# More functions that need to be tested:
# -----------------------------------------------------------
        # pdk status
        # pdk diff
        # pdk move some other other descriptor files
        # pdk update -r previous version
popd

# vim:ai:et:sts=4:sw=4:tw=0:
