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

# pql.sh 
# $Progeny$
#
# pql "all" should dump the whole cached data set in turtle.
# pql "query" should dump the resuls of a SPARQL query in turtle.

pdk add python.xml packages/python-defaults*.dsc packages/python_*.deb
pdk mark

pdk pql -i python.xml

# This one is unchecked.
pdk pql >output.txt <<EOF
select * from packages
order by name, epoch, version, release, arch
EOF

diff -u - output.txt <<EOF || fail 'diff output should match'
sha-1:6d7cf6eeaa67da461a35ebfba9351a7c1a7720eb|deb|deb|binary|python||2.3.3|6|all
sha-1:73ff2f8176e703be1946b6081386193afb25c620|deb|deb|binary|python||2.3.5|2|all
sha-1:ff9e54736ff8bb385c053a006c3a550c8f20674c|dsc|deb|source|python-defaults||2.3.3|6|all
sha-1:baf7a3b88f2a542205c8c03643651873da1f8ca3|dsc|deb|source|python-defaults||2.3.5|2|all
EOF

pdk pql >output.txt <<EOF
select * from components
order by blob_id
EOF

diff -u - output.txt <<EOF
sha-1:73ff2f8176e703be1946b6081386193afb25c620|python.xml
sha-1:6d7cf6eeaa67da461a35ebfba9351a7c1a7720eb|python.xml
sha-1:baf7a3b88f2a542205c8c03643651873da1f8ca3|python.xml
sha-1:ff9e54736ff8bb385c053a006c3a550c8f20674c|python.xml
EOF
