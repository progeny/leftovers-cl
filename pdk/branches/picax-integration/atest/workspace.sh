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

# workspace.sh
#
# Unit test the workspace commands

. atest/test_lib.sh

pdk workspace

verify_new_workspace() {
    dir="$1"
    (cd $dir; find -not -type d) | LANG=C sort | grep -v git/hooks >actual.txt
    diff -u - actual.txt <<EOF
./.git
./etc/git/HEAD
./etc/git/description
./etc/git/info/exclude
./etc/schema
EOF
    [ "$(readlink $dir/.git)" = etc/git ]
    [ -e $dir/.git/description ]
    [ 4 = "$(cat $dir/etc/schema)" ]
}

pdk workspace create || status=$?
test "$status" == 2 || bail "Expected command line error"

pdk workspace create foo
verify_new_workspace foo
rm -rf foo

(echo "workspace create" |pdk ) || status=$?
test "${status}" == "0" && bail "cmd shell should have returned non-zero?"

echo "workspace create foo" |pdk
verify_new_workspace foo
rm -rf foo
