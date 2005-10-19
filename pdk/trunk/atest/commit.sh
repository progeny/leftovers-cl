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

# log should show an ordered list of commit logs

assert_status() {
    set +x
    local message="$1"
    local expected=$tmp_dir/expected_status
    local actual=$tmp_dir/actual_status
    shift

    echo $* '' >$expected
    cat >>$expected

    echo -n >$actual
    for file in a b c d; do
        echo -n $(tail -n 1 $file) '' >>$actual
    done
    echo >>$actual
    pdk status >>$actual

    diff -u $expected $actual \
        || fail "status mismatch: $message"
    set -x
}

pdk workspace create vc
pushd vc
    echo 1 >>a
    echo 1 >>b
    echo 1 >>c
    echo 1 >>d
    pdk add a
    echo "Initial Commit" | pdk commit -f -
    assert_status "after add + raw" 1 1 1 1 <<EOF
unknown: b
unknown: c
unknown: d
EOF

    echo 2 >>a
    echo "Add comment." | pdk commit -f -
    assert_status "after change + raw" 2 1 1 1 <<EOF
unknown: b
unknown: c
unknown: d
EOF

    echo 2 >>b
    echo "Add file b" | pdk commit -f - b
    assert_status "after commit + file, not added" 2 2 1 1 <<EOF
unknown: c
unknown: d
EOF

    echo 2 >>c
    pdk add c
    echo "Add file c" | pdk commit -f - c
    assert_status "after commit + file, already added" 2 2 2 1 <<EOF
unknown: d
EOF

    echo 2 >>a
    echo 3 >>d
    pdk add d
    echo "Modify a" | pdk commit -f - a
    assert_status "after commit + file, another file added then changed" \
        2 2 2 3 <<EOF
new file: d
EOF

    echo 4 >>d
    echo "Add d" | pdk commit -f -
    assert_status "after commit raw, added file changed" 2 2 2 4 <<EOF
EOF


    cat >$tmp_dir/bin/fake_editor <<EOF
cat >\$1 <<MSG
message produced by fake editor
MSG
EOF
    chmod +x $tmp_dir/bin/fake_editor
    EDITOR=fake_editor
    export EDITOR
    echo 3 >>a
    pdk commit
    unset EDITOR
    assert_status "after commit with EDITOR" 3 2 2 4 <<EOF
EOF
    git-cat-file commit HEAD | grep fake

    echo 4 >>a
    pdk commit -m 'Message from command line.'
    assert_status "after commit with EDITOR" 4 2 2 4 <<EOF
EOF
    git-cat-file commit HEAD | grep "command line"

popd

# vim:ai:et:sts=4:sw=4:tw=0:
