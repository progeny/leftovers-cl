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

# cat should show the version of a given file from HEAD

pdk workspace create vc
pushd vc
    echo 1 >>a
    pdk commit -m 'initial' a

    pdk cat a >a.cat
    diff -u - a.cat <<EOF
1
EOF

    echo 2 >>a
    pdk cat a >a.cat
    diff -u - a.cat <<EOF
1
EOF
    pdk commit -m 'add 2'
    pdk cat a >a.cat
    diff -u - a.cat <<EOF
1
2
EOF

    # watch for regression where cat only looks at the git index.
    echo 3 >>a
    git-update-index a
    pdk cat a >a.cat
    diff -u - a.cat <<EOF
1
2
EOF
    pdk commit -m 'add 3'
    pdk cat a >a.cat
    diff -u - a.cat <<EOF
1
2
3
EOF

    pdk cat b 2>errors.txt || status=$?
    [ "$status" = 4 ] || fail "cat unknown file should fail"
    grep -i 'no file' errors.txt

popd

rm -rf vc

pdk workspace create vc
pushd vc
    pdk cat a 2>errors.txt || status=$?
    [ "$status" = 4 ] || fail "cat before a commit should fail"
    grep -i 'commit' errors.txt
popd

rm -rf vc

pdk workspace create vc
pushd vc
    pdk cat a b 2>errors.txt || status=$?
    [ "$status" = 2 ] || fail "cat with too many arguments should fail"
    grep -i 'single filename' errors.txt
popd

# vim:ai:et:sts=4:sw=4:tw=0:
