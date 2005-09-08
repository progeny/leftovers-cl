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

# error_handling.sh
# $Progeny$
#
. atest/test_lib.sh

#-----------------------------------------------------------------------
# Ill-formed command line
pdk workspace create foo
pushd foo/work
pdk semdiff  || status=$?
test "$status" = "2" || { 
    bail "Expected command-line error(2), got ${status}"
}
popd ; rm -rf foo

pdk resolve || status=$?
test "$status" = "2" || {
    bail "Expected command-line error(2), got ${status}"
}

pdk channel update z || status=$?
test "$status" = "2" || {
    bail "Expected command-line error(2), got ${status}"
}

pdk download || status=$?
test "$status" = "2" || {
    bail "Expected command-line error(2), got ${status}"
}

#-----------------------------------------------------------------------
# Process ill-formed channels file
pdk workspace create foo
pushd foo/work
cat > ../channels.xml << EOF
<?xml version="1.0"?>
<channels>
  <blow-up-here>
</channels>
EOF
pdk channel update || status=$?
test "$status" = "3" || bail "Incorrect/unexpected error return"
popd ; rm -rf foo

#-----------------------------------------------------------------------
# Missing outside_world.cache
pdk workspace create foo
pushd foo/work
cat >empty.xml <<EOF
<?xml version="1.0"?>
<component/>
EOF
pdk resolve empty.xml || status=$?
test "$status" = "4" || bail "Incorrect/unexpected error return"
popd ; rm -rf foo


#-----------------------------------------------------------------------
# Process even worse ill-formed (non)XML
pdk workspace create foo
pushd foo/work
cat > ../channels.xml << EOF
not ex emm ell at all
EOF
pdk channel update || status=$?
test "$status" = "3" || bail "Incorrect/unexpected error return"
popd ; rm -rf foo

#-----------------------------------------------------------------------
# Bad path in apt-deb channel
pdk workspace create foo
pushd foo/work
cat > ../channels.xml <<EOF
<?xml version="1.0"?>
<channels>
  <foo>
    <type>apt-deb</type>
    <path>http://example.com/bar</path>
    <archs>i386 source</archs>
    <dist>foo</dist>
    <components>main</components>
  </foo>
</channels>
EOF
pdk channel update || status=$?
test "$status" = "3" || bail "Path element w/o trailing slash accepted"
popd ; rm -rf foo

#-----------------------------------------------------------------------
# Process an ill-formed component descriptor

pdk workspace create foo
pushd foo/work
cat > bad_component.xml << EOF
<?xml version="1.0"?>
EOF
pdk semdiff ./bad_component.xml  || status=$?
test "$status" = "3" || bail "Expected InputError(3) got ${status}"
popd
rm -rf foo

#-----------------------------------------------------------------------
# Process a more reasonable ill-formed component descriptor
# Unclosed tag

pdk workspace create foo
pushd foo/work
cat > ethereal.xml << EOF
<?xml version="1.0" encoding="utf-8"?>
<component>
  <contents>
    <dsc ref="sha-1:726bd9340f8b72a2fbf7e4b70265b56b125e525d">
      <name>ethereal</name>
      <version>0.9.13-1.0progeny2</version>
    </dsc>
  
</component>
EOF
pdk semdiff ethereal.xml  || status=$?
test "$status" = "3" || bail "Expected InputError(3) got ${status}"
popd
rm -rf foo

#-----------------------------------------------------------------------
# Cache miss

pdk workspace create foo
pushd foo/work
cat > cache-miss.xml <<EOF
<?xml version="1.0"?>
<component>
  <contents>
    <deb ref="sha-1:cantpossiblyexist"/>
  </contents>
</component>
EOF

pdk semdiff cache-miss.xml empty.xml || status=$?
test "$status" = "4" || bail "Incorrect/unexpected error return"
popd
rm -rf foo

#-----------------------------------------------------------------------
# Download non-existent package from channel
pdk workspace create foo
pushd foo/work
cat > cache-miss.xml <<EOF
<?xml version="1.0"?>
<component>
  <contents>
    <deb ref="sha-1:cantpossiblyexist"/>
  </contents>
</component>
EOF
cat > ../channels.xml <<EOF
<?xml version="1.0"?>
<channels>
  <foo>
    <type>dir</type>
    <path>/tmp</path>
  </foo>
</channels>
EOF
pdk channel update
pdk download cache-miss.xml || status=$?
test "$status" = "4" || bail "Did not handle channel miss correctly"
popd
rm -rf foo

#-----------------------------------------------------------------------
# Don't give necessary arguments -- command line error (2)
pdk repogen  || status=$?
test "${status}" = "2" || bail "Expected error 2, got $status"

#-----------------------------------------------------------------------
# Use non-exsistant channel.
pdk workspace create foo
pushd foo/work
cat > component.xml <<EOF
<?xml version="1.0"?>
<component>
  <contents>
    <deb/>
  </contents>
</component>
EOF

cat > ../channels.xml <<EOF
<?xml version="1.0"?>
<channels>
  <foo>
    <type>dir</type>
    <path>/tmp</path>
  </foo>
</channels>
EOF
pdk channel update
pdk resolve component.xml bar || status=$?
test "$status" = "3" || bail "Did not handle non-existant channel correctly"
popd
rm -rf foo

#-----------------------------------------------------------------------
# repogen an empty component
pdk workspace create foo
pushd foo/work
cat > empty.xml <<EOF
<?xml version="1.0"?>
<component>
  <contents>
  </contents>
</component>
EOF
rm -rf foo

pdk repogen empty.xml || status=$?
test "$status" = "3" || bail "Did not handle repogen empty.xml correctly."
popd
rm -rf foo

#-----------------------------------------------------------------------
# update_from_remote with no upstream name
pdk workspace create foo
pushd foo/work
pdk update_from_remote || status=$?
test "$status" = "2" \
    || bail "Did not handle update_from_remote no argument correctly."
popd
rm -rf foo
