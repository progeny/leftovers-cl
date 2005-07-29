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

# download-abstract.sh
#
# Check for regression of problem where download would barf on components
# containing abstract references.

mkdir channel/
cp packages/apache2-common_2.0.53-5_i386.deb channel/

cat >channels.xml <<EOF
<?xml version="1.0"?>
<channels>
  <channel>
    <type>dir</type>
    <path>channel</path>
  </channel>
</channels>
EOF

pdk updatechannels

cat >a.xml <<EOF
<?xml version="1.0"?>
<component>
  <contents>
    <deb>some-name</deb>
  </contents>
</component>
EOF

pdk download a.xml
