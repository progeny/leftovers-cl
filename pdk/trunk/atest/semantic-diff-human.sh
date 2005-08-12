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

# semantic-diff-human.sh
# $Progeny$
#
# Test pdk semdiff human readable format.

# get Utility functions
. atest/test_lib.sh

assert_empty() {
    if [ "$(stat -c '%s' $1)" != 0 ]; then
        cat "$1"
        fail "$1 should be empty"
    fi
}

semdiff_report () {
    pdk semdiff "$@" | ul 2>errors.txt
    assert_empty errors.txt
    rm errors.txt
}

pdk workspace create workspace
cd workspace/work

cat >../channels.xml <<EOF
<?xml version="1.0"?>
<channels>
  <local>
    <type>dir</type>
    <path>channel</path>
  </local>
</channels>
EOF

channel_dir=${tmp_dir}/channel
mkdir ${channel_dir}
cp $PACKAGES/ethereal_0.9.4-1woody2_i386.deb ${channel_dir}

cat >ethereal.xml <<EOF
<?xml version="1.0"?>
<component>
  <contents>
    <component>meta-info.xml</component>
    <deb>ethereal</deb>
  </contents>
</component>
EOF

cat >meta-info.xml <<EOF
<?xml version="1.0"?>
<component>
  <contents>
    <deb>
      <name>ethereal</name>
      <version>0.9.4-1woody2</version>
      <meta>
        <predicate>test-stage-1</predicate>
      </meta>
    </deb>
  </contents>
</component>
EOF

pdk channel update
pdk resolve ethereal.xml
pdk download ethereal.xml

pdk add ethereal.xml
pdk add meta-info.xml
pdk commit 'Starting point for diff.'

# Nothing should have changed yet.
semdiff_report ethereal.xml

rm -r ${channel_dir}
mkdir ${channel_dir}
cp $PACKAGES/ethereal_0.9.4-1woody3_i386.deb ${channel_dir}

cat >ethereal.xml <<EOF
<?xml version="1.0"?>
<component>
  <contents>
    <component>meta-info.xml</component>
    <deb>ethereal</deb>
  </contents>
</component>
EOF

pdk channel update
pdk resolve ethereal.xml
pdk download ethereal.xml

semdiff_report ethereal.xml

pdk commit ''

rm -r ${channel_dir}
mkdir ${channel_dir}
cp $PACKAGES/ethereal_0.9.4-1woody2_i386.deb ${channel_dir}

cat >ethereal.xml <<EOF
<?xml version="1.0"?>
<component>
  <contents>
    <component>meta-info.xml</component>
    <deb>ethereal</deb>
  </contents>
</component>
EOF

pdk channel update
pdk resolve ethereal.xml
pdk download ethereal.xml

semdiff_report ethereal.xml


# Install old version of adjtimex
pdk package add time.xml \
    $PACKAGES/adjtimex-1.13-12.src.rpm \
    $PACKAGES/adjtimex-1.13-12.i386.rpm

cp time.xml time-before.xml

# nothing has changed yet
semdiff_report time-before.xml time.xml

cp time.xml time-before.xml

# Install new version of adjtimex
pdk package add -r time.xml \
    $PACKAGES/adjtimex-1.13-13.src.rpm \
    $PACKAGES/adjtimex-1.13-13.i386.rpm

semdiff_report time-before.xml time.xml

cp time.xml time-before.xml

# Downgrade back to the older version
pdk package add -r time.xml \
    $PACKAGES/adjtimex-1.13-12.src.rpm \
    $PACKAGES/adjtimex-1.13-12.i386.rpm

semdiff_report time-before.xml time.xml

cp time.xml time-before.xml

# Drop a package
pdk package add -r time.xml \
    $PACKAGES/adjtimex-1.13-12.i386.rpm

semdiff_report time-before.xml time.xml

cp time.xml time-before.xml

# Add it back
pdk package add -r time.xml \
    $PACKAGES/adjtimex-1.13-12.src.rpm \
    $PACKAGES/adjtimex-1.13-12.i386.rpm

semdiff_report time-before.xml time.xml
