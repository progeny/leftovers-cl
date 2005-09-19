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

# compile.sh 
# $Progeny$
#
# add -> prc works. Make sure the resulting repo looks sane. Packages
# in the repo should be hard linked to the cache.

. atest/test_lib.sh
testroot=$(pwd)
project=$(pwd)/idempotent
cachedir=${project}/etc/cache
packages=$(pwd)/packages
pdk workspace create idempotent


# Create a component descriptor
cd ${project}
cat >product.xml <<EOF
<?xml version="1.0"?>
<component>
  <meta>
    <origin>community</origin>
    <label>distro</label>
    <version>1.0</version>
    <codename>zip</codename>
    <suite>stable</suite>
    <date>Tue, 22 Mar 2005 21:20:00 +0000</date>
    <description>Hello World!</description>
  </meta>
  <contents>
    <component>main.xml</component>
  </contents>
</component>

EOF


cat >main.xml <<EOF
<?xml version="1.0"?>
<component>
  <contents>
    <component>progeny.com/apache.xml</component>
  </contents>
</component>
EOF


# Install all the packages into the local cache
pdk package add progeny.com/apache.xml \
    ${packages}/apache2-common_2.0.53-5_i386.deb \
    ${packages}/apache2_2.0.53-5.dsc \


pdk repogen product.xml

test -d './repo' || fail "mising repo directory"
test -d ${cachedir} || fail "missing cache directory"

# Copy information from the repo for comparison
cp repo/dists/stable/Release MainRelease.hold
cp repo/dists/stable/main/binary-i386/Release BinRelease.hold
cp repo/dists/stable/main/source/Release SrcRelease.hold
cp repo/dists/stable/main/source/Sources Sources.hold
cp repo/dists/stable/main/binary-i386/Packages Packages.hold

# copy cache information for comparison
ls -R ${cachedir} | sort > cachedir.hold
rm -r repo

echo Import it again, just to see what happens.
pdk package add progeny.com/apache.xml \
    ${packages}/apache2-common_2.0.53-5_i386.deb \
    ${packages}/apache2_2.0.53-5.dsc \

pdk repogen product.xml

# Ensure we have indices in all the places we expect them
assert_exists repo/dists/stable/Release
assert_exists repo/dists/stable/main/binary-i386/Release
assert_exists repo/dists/stable/main/source/Release
assert_exists repo/dists/stable/main/source/Sources 
assert_exists repo/dists/stable/main/binary-i386/Packages 

# MAke sure the release files are the same
diff -us repo/dists/stable/main/source/Sources Sources.hold ||
    bail "Sources files differ"
diff -us repo/dists/stable/main/binary-i386/Packages Packages.hold ||
    bail "Packages files differ"
diff -us repo/dists/stable/Release MainRelease.hold || 
    bail "release files differ"
diff -us repo/dists/stable/main/binary-i386/Release BinRelease.hold ||
    bail "binary release files differ"
diff -us repo/dists/stable/main/source/Release SrcRelease.hold ||
    bail "source Release files differ"

echo "Diffing ${cachedir}"
ls -R ${cachedir} | sort | diff -s cachedir.hold -

# Note that in this test, we don't care what the results are, just
# that they are the same.
