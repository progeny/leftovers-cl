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

# compile-missing-source.sh 
# $Progeny$
#
# Watch for regression. prc bombed when a binary was presented without it's
# source.

. atest/test_lib.sh

ls packages/apache2-*.deb | xargs pdk add apache.xml || fail

pdk repogen apache.xml

[ -d './repo' ] || fail "mising repo directory"

check_file "b7d31cf9a160c3aadaf5f1cd86cdc8762b3d4b1b" \
    "./repo/pool/main/a/apache2/apache2-common_2.0.53-5_i386.deb"

# XXX: Lists are not appropriate for acceptance tests.
#grep apache tmp/repo/dists/stable/list-main-i386

assert_exists repo/dists/apache/main/binary-i386/Packages.gz
assert_not_exists repo/dists/apache/main/source/Sources.gz

assert_exists repo/dists/apache/Release
assert_exists repo/dists/apache/main/binary-i386/Release
assert_not_exists repo/dists/apache/main/source/Release

grep apache repo/dists/apache/main/binary-i386/Packages

