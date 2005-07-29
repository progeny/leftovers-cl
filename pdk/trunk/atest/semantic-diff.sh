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

# semantic-diff.sh
# $Progeny$
#
# Test pdk semdiff

# get Utility functions
. atest/test_lib.sh

# -------------------
# Setup
# -------------------

pdk create sim-progeny
cd sim-progeny/work
# -----------------------------------------------------
# Do it all with rpms.
# -----------------------------------------------------

# Install old version of adjtimex
pdk add progeny.com/time.xml \
    $tmp_dir/packages/adjtimex-1.13-12.src.rpm \
    $tmp_dir/packages/adjtimex-1.13-12.i386.rpm

pdk vcadd progeny.com/time.xml
pdk commit master foo
# nothing has changed yet
pdk semdiff progeny.com/time.xml | LANG=C sort >semdiff.txt
diff -u - semdiff.txt <<EOF
unchanged|rpm|adjtimex|/1.13/12|/1.13/12|i386|progeny.com/time.xml
unchanged|srpm|adjtimex|/1.13/12|/1.13/12|x86_64|progeny.com/time.xml
EOF

# Install new version of adjtimex
pdk add -r progeny.com/time.xml \
    $tmp_dir/packages/adjtimex-1.13-13.src.rpm \
    $tmp_dir/packages/adjtimex-1.13-13.i386.rpm

pdk semdiff progeny.com/time.xml | LANG=C sort >semdiff.txt
diff -u - semdiff.txt <<EOF
upgrade|rpm|adjtimex|/1.13/12|/1.13/13|i386|progeny.com/time.xml
upgrade|srpm|adjtimex|/1.13/12|/1.13/13|x86_64|progeny.com/time.xml
EOF

pdk commit master foo

# Downgrade back to the older version
pdk add -r progeny.com/time.xml \
    $tmp_dir/packages/adjtimex-1.13-12.src.rpm \
    $tmp_dir/packages/adjtimex-1.13-12.i386.rpm

pdk semdiff progeny.com/time.xml | LANG=C sort >semdiff.txt
diff -u - semdiff.txt <<EOF
downgrade|rpm|adjtimex|/1.13/13|/1.13/12|i386|progeny.com/time.xml
downgrade|srpm|adjtimex|/1.13/13|/1.13/12|x86_64|progeny.com/time.xml
EOF

pdk commit master foo

# Drop a package
pdk add -r progeny.com/time.xml \
    $tmp_dir/packages/adjtimex-1.13-12.i386.rpm

pdk semdiff progeny.com/time.xml | grep -v ^unchanged \
    | LANG=C sort >semdiff.txt
diff -u - semdiff.txt <<EOF
drop|srpm|adjtimex|/1.13/12|x86_64|progeny.com/time.xml
EOF

pdk commit master foo

# Add it back
pdk add -r progeny.com/time.xml \
    $tmp_dir/packages/adjtimex-1.13-12.src.rpm \
    $tmp_dir/packages/adjtimex-1.13-12.i386.rpm

pdk semdiff progeny.com/time.xml | grep -v ^unchanged \
    | LANG=C sort >semdiff.txt
diff -u - semdiff.txt <<EOF
add|srpm|adjtimex|/1.13/12|x86_64|progeny.com/time.xml
EOF

pdk commit master foo

# -----------------------------------------------------
# Do it all with debs.
# -----------------------------------------------------

# Install old version of ethereal.
pdk add progeny.com/ethereal.xml \
    $tmp_dir/packages/ethereal_0.9.13-1.0progeny1.dsc \
    $tmp_dir/packages/ethereal_0.9.13-1.0progeny1_ia64.deb \
    $tmp_dir/packages/ethereal-common_0.9.13-1.0progeny1_ia64.deb \
    $tmp_dir/packages/ethereal-dev_0.9.13-1.0progeny1_ia64.deb \
    $tmp_dir/packages/tethereal_0.9.13-1.0progeny1_ia64.deb

pdk vcadd progeny.com/ethereal.xml
pdk commit master foo

# nothing has changed yet
pdk semdiff progeny.com/ethereal.xml | LANG=C sort >semdiff.txt
diff -u - semdiff.txt <<EOF
unchanged|deb|ethereal-common|0.9.13-1.0progeny1|0.9.13-1.0progeny1|ia64|progeny.com/ethereal.xml
unchanged|deb|ethereal-dev|0.9.13-1.0progeny1|0.9.13-1.0progeny1|ia64|progeny.com/ethereal.xml
unchanged|deb|ethereal|0.9.13-1.0progeny1|0.9.13-1.0progeny1|ia64|progeny.com/ethereal.xml
unchanged|deb|tethereal|0.9.13-1.0progeny1|0.9.13-1.0progeny1|ia64|progeny.com/ethereal.xml
unchanged|dsc|ethereal|0.9.13-1.0progeny1|0.9.13-1.0progeny1|any|progeny.com/ethereal.xml
EOF

# Install newer version of ethereal.
pdk add -r progeny.com/ethereal.xml \
    $tmp_dir/packages/ethereal_0.9.13-1.0progeny2.dsc \
    $tmp_dir/packages/ethereal_0.9.13-1.0progeny2_ia64.deb \
    $tmp_dir/packages/ethereal-common_0.9.13-1.0progeny2_ia64.deb \
    $tmp_dir/packages/ethereal-dev_0.9.13-1.0progeny2_ia64.deb \
    $tmp_dir/packages/tethereal_0.9.13-1.0progeny2_ia64.deb

pdk semdiff progeny.com/ethereal.xml | LANG=C sort >semdiff.txt

diff -u - semdiff.txt <<EOF
upgrade|deb|ethereal-common|0.9.13-1.0progeny1|0.9.13-1.0progeny2|ia64|progeny.com/ethereal.xml
upgrade|deb|ethereal-dev|0.9.13-1.0progeny1|0.9.13-1.0progeny2|ia64|progeny.com/ethereal.xml
upgrade|deb|ethereal|0.9.13-1.0progeny1|0.9.13-1.0progeny2|ia64|progeny.com/ethereal.xml
upgrade|deb|tethereal|0.9.13-1.0progeny1|0.9.13-1.0progeny2|ia64|progeny.com/ethereal.xml
upgrade|dsc|ethereal|0.9.13-1.0progeny1|0.9.13-1.0progeny2|any|progeny.com/ethereal.xml
EOF

pdk commit master foo

# Downgrade to older version again.
pdk add -r progeny.com/ethereal.xml \
    $tmp_dir/packages/ethereal_0.9.13-1.0progeny1.dsc \
    $tmp_dir/packages/ethereal_0.9.13-1.0progeny1_ia64.deb \
    $tmp_dir/packages/ethereal-common_0.9.13-1.0progeny1_ia64.deb \
    $tmp_dir/packages/ethereal-dev_0.9.13-1.0progeny1_ia64.deb \
    $tmp_dir/packages/tethereal_0.9.13-1.0progeny1_ia64.deb

pdk semdiff progeny.com/ethereal.xml | LANG=C sort >semdiff.txt
diff -u - semdiff.txt <<EOF
downgrade|deb|ethereal-common|0.9.13-1.0progeny2|0.9.13-1.0progeny1|ia64|progeny.com/ethereal.xml
downgrade|deb|ethereal-dev|0.9.13-1.0progeny2|0.9.13-1.0progeny1|ia64|progeny.com/ethereal.xml
downgrade|deb|ethereal|0.9.13-1.0progeny2|0.9.13-1.0progeny1|ia64|progeny.com/ethereal.xml
downgrade|deb|tethereal|0.9.13-1.0progeny2|0.9.13-1.0progeny1|ia64|progeny.com/ethereal.xml
downgrade|dsc|ethereal|0.9.13-1.0progeny2|0.9.13-1.0progeny1|any|progeny.com/ethereal.xml
EOF

pdk commit master foo

# Drop a package.
pdk add -r progeny.com/ethereal.xml \
    $tmp_dir/packages/ethereal_0.9.13-1.0progeny1.dsc \
    $tmp_dir/packages/ethereal-common_0.9.13-1.0progeny1_ia64.deb \
    $tmp_dir/packages/ethereal-dev_0.9.13-1.0progeny1_ia64.deb \
    $tmp_dir/packages/tethereal_0.9.13-1.0progeny1_ia64.deb

pdk semdiff progeny.com/ethereal.xml | grep -v ^unchanged \
    | LANG=C sort >semdiff.txt
diff -u - semdiff.txt <<EOF
drop|deb|ethereal|0.9.13-1.0progeny1|ia64|progeny.com/ethereal.xml
EOF

pdk commit master foo

# Add it back
pdk add -r progeny.com/ethereal.xml \
    $tmp_dir/packages/ethereal_0.9.13-1.0progeny1.dsc \
    $tmp_dir/packages/ethereal_0.9.13-1.0progeny1_ia64.deb \
    $tmp_dir/packages/ethereal-common_0.9.13-1.0progeny1_ia64.deb \
    $tmp_dir/packages/ethereal-dev_0.9.13-1.0progeny1_ia64.deb \
    $tmp_dir/packages/tethereal_0.9.13-1.0progeny1_ia64.deb

pdk semdiff progeny.com/ethereal.xml | grep -v ^unchanged \
    | LANG=C sort >semdiff.txt
diff -u - semdiff.txt <<EOF
add|deb|ethereal|0.9.13-1.0progeny1|ia64|progeny.com/ethereal.xml
EOF

pdk commit master foo
