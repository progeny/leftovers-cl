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

# semantic-diff-channel.sh
# $Progeny$
#
# Test pdk semdiff vs. a channel

mkdir channel-1
cp packages/ethereal_0.9.13-1.0progeny1_ia64.deb channel-1/

mkdir channel-2
cp packages/ethereal_0.9.13-1.0progeny2_ia64.deb channel-2/

cat >channels.xml <<EOF
<?xml version="1.0"?>
<channel>
  <channel-1>
    <type>dir</type>
    <path>channel-1</path>
  </channel-1>
  <channel-2>
    <type>dir</type>
    <path>channel-2</path>
  </channel-2>
</channel>
EOF

cat >ethereal.xml <<EOF
<?xml version="1.0"?>
<component>
  <contents>
    <deb/>
  </contents>
</component>
EOF

pdk updatechannels
pdk resolve ethereal.xml channel-1
pdk download ethereal.xml
pdk semdiff -c channel-2 ethereal.xml | LANG=C sort >semdiff.txt

diff -u - semdiff.txt <<EOF
upgrade|deb|ethereal|0.9.13-1.0progeny1|0.9.13-1.0progeny2|ia64|ethereal.xml
EOF