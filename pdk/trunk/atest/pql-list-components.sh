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

# pql-list-components.sh
# $Progeny$
#
# Make sure pql can return the right component info.

pdk add progeny.com/apache.xml packages/apache2-common_2.0.53-5_i386.deb
cat >test-component.xml <<EOF
<?xml version="1.0"?>
<component>
  <contents>
    <component>progeny.com/apache.xml</component>
  </contents>
</component>  
EOF

pdk pql -i test-component.xml 

pdk pql > test.output <<EOF
select packages.name, components.blob_id from packages, components
where components.pkg_blob_id = packages.blob_id
EOF

echo 'apache2-common|progeny.com/apache.xml' | diff -u - test.output \
    || fail 'component query results differed'
