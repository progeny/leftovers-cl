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

# apt-compatible.sh
#
# test that our new repo is compatible (at least in some small extent) with
# apt.

. atest/test_lib.sh

# Create a component to build a repository from
pdk package add aptable.xml packages/apache*.deb packages/apache*.dsc
pdk package add aptable.xml packages/*xsok*.deb packages/*xsok*.dsc

pdk repogen aptable.xml || bail "Cannot compile myrepo.xml"

# -------------------------------------------
# Setup  APT
# -------------------------------------------
# Set up the dir structures
NEWROOT=$(pwd)/apt-setup
mkdir -p ${NEWROOT}/etc/apt 
mkdir -p ${NEWROOT}/cachedir/archives/partial
mkdir -p ${NEWROOT}/statedir/lists/partial
touch ${NEWROOT}/statedir/dpkg
# set up the overrides file
OVERRIDE=${NEWROOT}/overrides.conf
(
    echo "Dir \"${NEWROOT}\""
    echo "{"
    echo "    State \"statedir\""
    echo "    {"
    echo "        status \"dpkg\";"
    echo "    };"
    echo "    Cache \"cachedir\";"
    echo "};"
    echo ""
) > ${OVERRIDE}
# Create the sources.list file
SOURCESLIST=${NEWROOT}/etc/apt/sources.list
echo deb file:$(pwd)/repo/ aptable main> ${SOURCESLIST}
echo deb-src file:$(pwd)/repo/ aptable main >> ${SOURCESLIST}
cat $SOURCESLIST

# Try to use apt on the current repository

apt-get -c ${OVERRIDE} update || 
    bail "apt-get has fallen and it can't get update"

apt-cache -c ${OVERRIDE} search apache | 
    grep apache || 
        bail "can't find apache in repo"

apt-cache -c ${OVERRIDE} search xsok |
    grep xsok || 
        bail "Can't find xsok in repo"

apt-get -c ${OVERRIDE} --dry-run source apache2-common ||
    bail "can't find source for apache"

apt-get -c ${OVERRIDE} --dry-run source xsok ||
    bail "can't find source for xsok"
