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

# mediagen-basic-media.sh
# $Progeny$
#
# Create simple media from a component descriptor.

. atest/utils/repogen-fixture.sh

set_up_repogen_fixture test-mediagen
cd test-mediagen

cat >distro.xml <<EOF
<?xml version="1.0"?>
<component>
  <meta>
    <media>cd</media>
  </meta>
  <contents>
    <component>progeny.com/apache.xml</component>
  </contents>
</component>
EOF

pdk repogen distro.xml
pdk mediagen distro.xml

EXPECTED_MD5="No MD5 expected yet."
GEN_MD5=`isoinfo -i images/img-bin1.iso -f -J | sort | md5sum`
test ${GEN_MD5} = ${EXPECTED_MD5} || fail "Image contents different than expected"
