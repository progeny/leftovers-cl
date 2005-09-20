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

# dump-meta.sh
# $Progeny$
#
# pdk repogen with dumpmeta comp should dump the metadata found in the
# component.

. atest/utils/repogen-fixture.sh

set_up_repogen_fixture test-repogen
cd test-repogen

pdk dumpmeta python.xml | diff -u /dev/null -

# rewrite component descriptor but with metadata.
cat >python.xml <<EOF
<?xml version="1.0" encoding="utf-8"?>
<component>
  <meta>
    <other>value</other>
  </meta>
  <contents>
    <deb ref="sha-1:6d7cf6eeaa67da461a35ebfba9351a7c1a7720eb">
      <name>python</name>
      <version>2.3.3-6</version>
    </deb>
    <dsc ref="sha-1:ff9e54736ff8bb385c053a006c3a550c8f20674c">
      <name>python-defaults</name>
      <version>2.3.3-6</version>
    </dsc>
    <deb>
      <name>python</name>
      <meta>
        <key>value</key>
      </meta>
    </deb>
  </contents>
</component>
EOF

pdk dumpmeta python.xml >metadump.txt

diff -u - metadump.txt <<EOF
sha-1:6d7cf6eeaa67da461a35ebfba9351a7c1a7720eb|deb|python|key|value
python.xml|component||other|value
EOF
