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

# compile-dup-pkg-refs.sh 
# $
#
# Watch for regression. prc bombed when repo-eval resulted in the same
# package being presented to the compiler more than once.

. atest/test_lib.sh

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
    <component>apache.xml</component>
  </contents>
</component>
EOF

# Install all the packages into the local cache
pdk package add apache.xml \
    packages/apache2-common_2.0.53-5_i386.deb \
    packages/apache2_2.0.53-5.dsc \

cat >apache.xml <<EOF
<?xml version="1.0" encoding="utf-8"?>
<component>
  <!-- note the same packages are mentioned repeatedly -->

  <contents>
    <deb ref="sha-1:b7d31cf9a160c3aadaf5f1cd86cdc8762b3d4b1b">
      <name>apache2-common</name>
      <version>2.0.53-5</version>
    </deb>
    <dsc ref="sha-1:9d26152e78ca33a3d435433c67644b52ae4c670c">
      <name>apache2</name>
      <version>2.0.53-5</version>
    </dsc>

    <deb ref="sha-1:b7d31cf9a160c3aadaf5f1cd86cdc8762b3d4b1b">
      <name>apache2-common</name>
      <version>2.0.53-5</version>
    </deb>
    <dsc ref="sha-1:9d26152e78ca33a3d435433c67644b52ae4c670c">
      <name>apache2</name>
      <version>2.0.53-5</version>
    </dsc>

    <deb ref="sha-1:b7d31cf9a160c3aadaf5f1cd86cdc8762b3d4b1b">
      <name>apache2-common</name>
      <version>2.0.53-5</version>
    </deb>
    <dsc ref="sha-1:9d26152e78ca33a3d435433c67644b52ae4c670c">
      <name>apache2</name>
      <version>2.0.53-5</version>
    </dsc>

    <deb ref="sha-1:b7d31cf9a160c3aadaf5f1cd86cdc8762b3d4b1b">
      <name>apache2-common</name>
      <version>2.0.53-5</version>
    </deb>
    <dsc ref="sha-1:9d26152e78ca33a3d435433c67644b52ae4c670c">
      <name>apache2</name>
      <version>2.0.53-5</version>
    </dsc>
  </contents>
</component>
EOF

pdk repogen product.xml

[ -d './repo' ] || fail "mising repo directory"


check_file "b7d31cf9a160c3aadaf5f1cd86cdc8762b3d4b1b" \
    "./repo/pool/main/a/apache2/apache2-common_2.0.53-5_i386.deb"
check_file "9d26152e78ca33a3d435433c67644b52ae4c670c" \
    "./repo/pool/main/a/apache2/apache2_2.0.53-5.dsc"
check_file "9f4be3925441f006f8ee2054d96303cdcdac9b0a" \
    "./repo/pool/main/a/apache2/apache2_2.0.53-5.diff.gz"
check_file "214867c073d2bd43ed8374c9f34fa5532a9d7de0" \
    "./repo/pool/main/a/apache2/apache2_2.0.53.orig.tar.gz"

assert_exists repo/dists/stable/main/binary-i386/Packages.gz
assert_exists repo/dists/stable/main/source/Sources.gz

assert_exists repo/dists/stable/Release
assert_exists repo/dists/stable/main/binary-i386/Release
assert_exists repo/dists/stable/main/source/Release

grep apache repo/dists/stable/main/binary-i386/Packages
grep apache repo/dists/stable/main/source/Sources

