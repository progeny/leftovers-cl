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

# resolve-two-channels.sh
#
# Catch regression of problem where resolving with two channels could result
# in a type constraint being ignored.

cat >xsok.xml <<EOF
<?xml version="1.0"?>
<component>
  <contents>
    <dsc>xsok</dsc>
  </contents>
</component>
EOF

mkdir channel-1
cp atest/packages/xsok_1.02-9woody2.dsc channel-1/
cp atest/packages/xsok_1.02-9woody2.diff.gz channel-1/
cp atest/packages/xsok_1.02.orig.tar.gz channel-1/

mkdir channel-2
cp atest/packages/xsok_1.02-9woody2_i386.deb channel-2

cat >channels.xml <<EOF
<?xml version="1.0"?>
<channels>
  <channel-1>
    <type>dir</type>
    <path>channel-1</path>
  </channel-1>
  <channel-2>
    <type>dir</type>
    <path>channel-2</path>
  </channel-2>
</channels>
EOF

pdk updatechannels

pdk resolve xsok.xml channel-1 channel-2

diff -u - xsok.xml <<EOF
<?xml version="1.0" encoding="utf-8"?>
<component>
  <contents>
    <dsc ref="md5:5e3f7f8513b7fb3e8fa1ebfa56a2b4bc">
      <name>xsok</name>
      <version>1.02-9woody2</version>
    </dsc>
  </contents>
</component>
EOF
