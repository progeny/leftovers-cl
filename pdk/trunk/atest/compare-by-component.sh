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

# compare-by-component.sh
# $Progeny$
#
# Besides working on whole projects, compare should work on single
# components.

pdk workspace create testroot
testrepo=$(pwd)/testrepo
testroot=$(pwd)/testroot
cachedir=${testroot}/cache
workdir=${testroot}/work
packages=$(pwd)/packages

# Create a pile of packages 
mkdir -p ${testrepo}/dists/test/main/binary-i386
cp ${packages}/python_2.3.5-2_all.deb ${testrepo}/dists/test/main/binary-i386
(cd ${testrepo} && apt-ftparchive packages dists) \
    > ${testrepo}/dists/test/main/binary-i386/Packages

cd ${workdir}
pdk package add progeny.com/python-2.3.xml ${packages}/python_2.3.3-6_all.deb || fail "could not import package"

pdk compare progeny.com/python-2.3.xml file://${testrepo},test,main \
    > test.out

echo 'progeny.com/python-2.3.xml|python|test-main|2.3.3-6|2.3.5-2' \
    | diff -u - test.out \
    || fail
