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

# status should show files and their version control status

. atest/utils/repogen-fixture.sh

set_up_repogen_fixture a

pdk workspace create b
pushd a
    cat >etc/channels.xml <<EOF
<?xml version="1.0"?>
<channels>
  <b>
    <type>source</type>
    <path>$tmp_dir/b</path>
  </b>
</channels>
EOF
    pdk add progeny.com/apache.xml
    pdk commit "git-production commit"

    pdk repogen progeny.com/apache.xml

    pdk push b
popd

pushd b
    pdk status >etc/output.txt
    diff -u - etc/output.txt <<EOF
EOF
    touch a
    echo '<!-- comment -->' >>progeny.com/apache.xml
    pdk status >etc/output.txt
    diff -u - etc/output.txt <<EOF
modified: progeny.com/apache.xml
unknown: a
EOF
    pdk commit 'a local change'
    pdk status >etc/output.txt
    diff -u - etc/output.txt <<EOF
unknown: a
EOF
popd

# vim:ai:et:sts=4:sw=4:tw=0:
