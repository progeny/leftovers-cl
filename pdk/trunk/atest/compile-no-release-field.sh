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
# poke -> prc works. Make sure the resulting repo looks sane. Packages
# in the repo should be hard linked to the cache.

# get Utility functions
. atest/test_lib.sh

pdk workspace create workspace
cd workspace/work

# Create a component descriptor
# XXX: This is done often enough in testing, it it worth a script or shell
# function? 
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
    <component>progeny.com/emacs.xml</component>
  </contents>
</component>
EOF

# Add the emacs packagexs
pdk package add progeny.com/emacs.xml \
    ${PACKAGES}/emacs-defaults_1.1_all.deb \
    ${PACKAGES}/emacs-defaults_1.1.dsc

# Add an apache package
# XXX: This is necessary because pdk gets confused when only arch:all
# packages are present.

pdk package add progeny.com/emacs.xml \
    ${PACKAGES}/apache2-common_2.0.53-5_i386.deb

pdk repogen product.xml

[ -d './repo' ] || fail "mising repo directory"


# Watch for regression where version contains "-None"
check_file "95155bda2cb225f94401e6f82ec3261f094111f0" \
    "./repo/pool/main/e/emacs-defaults/emacs-defaults_1.1_all.deb"
check_file "9f4468e5a0f9a99df82083ba856483ba66f007a8" \
    "./repo/pool/main/e/emacs-defaults/emacs-defaults_1.1.dsc"
check_file "9ec95718a49fd7f1a8a745c3673b5386349f3f77" \
    "./repo/pool/main/e/emacs-defaults/emacs-defaults_1.1.tar.gz"

repo_path=repo/pool/main/e/emacs-defaults

# Check all the binarie files (heh, all one of them -- for now)
pkgname=emacs-defaults_1.1_all.deb
grep ${pkgname} repo/dists/stable/main/binary-i386/Packages
assert_exists ${repo_path}/${pkgname}

# Check all the source files
for pkgname in emacs-defaults_1.1.dsc emacs-defaults_1.1.tar.gz; do
    grep ${pkgname} repo/dists/stable/main/source/Sources
    assert_exists ${repo_path}/${pkgname}
done

# Watch for regression in 
