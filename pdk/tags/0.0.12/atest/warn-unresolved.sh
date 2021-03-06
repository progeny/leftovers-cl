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

# warn-unresolve.sh
# $Progeny$
#
# resolve should warn the user if unresolved references remain.

. atest/test_lib.sh

mkdir channel
cp ${PACKAGES}/apache2*_2.0.53* channel

pdk workspace create workspace

cat >workspace/etc/channels.xml <<EOF
<?xml version="1.0"?>
<channels>
  <local>
    <type>dir</type>
    <path>$(pwd)/channel</path>
  </local>
</channels>
EOF

cd workspace
pdk channel update

# Try requesting existing packages some which aren't present
cat >apache.xml <<EOF
<?xml version="1.0" encoding="utf-8"?>
<component>
  <contents>
    <dsc>apache2</dsc>
    <deb>apache2-common</deb>
    <dsc>ida</dsc>
    <deb>snorklewink2</deb>
    <!-- this one is a binary with meta info -->
    <deb>
      <name>snorklewink3</name>
      <meta>
        <test>data</test>
      </meta>
    </deb>
  </contents>
</component>
EOF

pdk resolve apache.xml 2>&1 | cut -d ' ' -f 3- >errors
diff -u - errors <<EOF
WARNING Unresolved references remain in apache.xml
WARNING No dsc where [name] is 'ida' AND [type] is 'dsc'
WARNING No deb where [name] is 'snorklewink2' AND [type] is 'deb'
WARNING No deb where [name] is 'snorklewink3' AND [type] is 'deb' returning [('test', 'data')]
EOF

# try again with all references resolvable.
cat >apache.xml <<EOF
<?xml version="1.0" encoding="utf-8"?>
<component>
  <contents>
    <dsc>apache2</dsc>
    <deb>apache2-common</deb>
  </contents>
</component>
EOF

pdk resolve apache.xml 2>errors
egrep "WARNING.*unresolved" errors && bail 'no warning expected'
