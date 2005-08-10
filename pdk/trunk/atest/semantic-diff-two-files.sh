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

# semantic-diff-two-files.sh
# $Progeny$
#
# Test pdk semdiff in compare two files mode.

# get Utility functions
. atest/test_lib.sh

pdk workspace create 'workspace'
cd workspace/work

# Install old version of adjtimex
pdk package add time.xml \
    ${PACKAGES}/adjtimex-1.13-12.src.rpm \
    ${PACKAGES}/adjtimex-1.13-12.i386.rpm

cp time.xml time-before.xml

# nothing has changed yet
pdk semdiff -m time-before.xml time.xml | LANG=C sort >semdiff.txt
diff -u - semdiff.txt <<EOF
unchanged|rpm|adjtimex|/1.13/12|/1.13/12|i386|time.xml
unchanged|srpm|adjtimex|/1.13/12|/1.13/12|x86_64|time.xml
EOF

cp time.xml time-before.xml

# Install new version of adjtimex
pdk package add -r time.xml \
    ${PACKAGES}/adjtimex-1.13-13.src.rpm \
    ${PACKAGES}/adjtimex-1.13-13.i386.rpm

pdk semdiff -m time-before.xml time.xml | LANG=C sort >semdiff.txt
diff -u - semdiff.txt <<EOF
upgrade|rpm|adjtimex|/1.13/12|/1.13/13|i386|time.xml
upgrade|srpm|adjtimex|/1.13/12|/1.13/13|x86_64|time.xml
EOF

cp time.xml time-before.xml

# Downgrade back to the older version
pdk package add -r time.xml \
    ${PACKAGES}/adjtimex-1.13-12.src.rpm \
    ${PACKAGES}/adjtimex-1.13-12.i386.rpm

pdk semdiff -m time-before.xml time.xml | LANG=C sort >semdiff.txt
diff -u - semdiff.txt <<EOF
downgrade|rpm|adjtimex|/1.13/13|/1.13/12|i386|time.xml
downgrade|srpm|adjtimex|/1.13/13|/1.13/12|x86_64|time.xml
EOF

cp time.xml time-before.xml

# Drop a package
pdk package add -r time.xml \
    ${PACKAGES}/adjtimex-1.13-12.i386.rpm

pdk semdiff -m time-before.xml time.xml | grep -v ^unchanged \
    | LANG=C sort >semdiff.txt
diff -u - semdiff.txt <<EOF
drop|srpm|adjtimex|/1.13/12|x86_64|time.xml
EOF

cp time.xml time-before.xml

# Add it back
pdk package add -r time.xml \
    ${PACKAGES}/adjtimex-1.13-12.src.rpm \
    ${PACKAGES}/adjtimex-1.13-12.i386.rpm

pdk semdiff -m time-before.xml time.xml | grep -v ^unchanged \
    | LANG=C sort >semdiff.txt
diff -u - semdiff.txt <<EOF
add|srpm|adjtimex|/1.13/12|x86_64|time.xml
EOF

# -----------------------------------------------------
# Do it all with debs.
# -----------------------------------------------------

# Install old version of ethereal.
pdk package add ethereal.xml \
    ${PACKAGES}/ethereal_0.9.13-1.0progeny1.dsc \
    ${PACKAGES}/ethereal_0.9.13-1.0progeny1_ia64.deb \
    ${PACKAGES}/ethereal-common_0.9.13-1.0progeny1_ia64.deb \
    ${PACKAGES}/ethereal-dev_0.9.13-1.0progeny1_ia64.deb \
    ${PACKAGES}/tethereal_0.9.13-1.0progeny1_ia64.deb

cp ethereal.xml ethereal-before.xml

# nothing has changed yet
pdk semdiff -m ethereal-before.xml ethereal.xml | LANG=C sort >semdiff.txt
diff -u - semdiff.txt <<EOF
unchanged|deb|ethereal-common|0.9.13-1.0progeny1|0.9.13-1.0progeny1|ia64|ethereal.xml
unchanged|deb|ethereal-dev|0.9.13-1.0progeny1|0.9.13-1.0progeny1|ia64|ethereal.xml
unchanged|deb|ethereal|0.9.13-1.0progeny1|0.9.13-1.0progeny1|ia64|ethereal.xml
unchanged|deb|tethereal|0.9.13-1.0progeny1|0.9.13-1.0progeny1|ia64|ethereal.xml
unchanged|dsc|ethereal|0.9.13-1.0progeny1|0.9.13-1.0progeny1|any|ethereal.xml
EOF

cp ethereal.xml ethereal-before.xml

# Install newer version of ethereal.
pdk package add -r ethereal.xml \
    ${PACKAGES}/ethereal_0.9.13-1.0progeny2.dsc \
    ${PACKAGES}/ethereal_0.9.13-1.0progeny2_ia64.deb \
    ${PACKAGES}/ethereal-common_0.9.13-1.0progeny2_ia64.deb \
    ${PACKAGES}/ethereal-dev_0.9.13-1.0progeny2_ia64.deb \
    ${PACKAGES}/tethereal_0.9.13-1.0progeny2_ia64.deb

pdk semdiff -m ethereal-before.xml ethereal.xml | LANG=C sort >semdiff.txt

diff -u - semdiff.txt <<EOF
upgrade|deb|ethereal-common|0.9.13-1.0progeny1|0.9.13-1.0progeny2|ia64|ethereal.xml
upgrade|deb|ethereal-dev|0.9.13-1.0progeny1|0.9.13-1.0progeny2|ia64|ethereal.xml
upgrade|deb|ethereal|0.9.13-1.0progeny1|0.9.13-1.0progeny2|ia64|ethereal.xml
upgrade|deb|tethereal|0.9.13-1.0progeny1|0.9.13-1.0progeny2|ia64|ethereal.xml
upgrade|dsc|ethereal|0.9.13-1.0progeny1|0.9.13-1.0progeny2|any|ethereal.xml
EOF

cp ethereal.xml ethereal-before.xml

# Downgrade to older version again.
pdk package add -r ethereal.xml \
    ${PACKAGES}/ethereal_0.9.13-1.0progeny1.dsc \
    ${PACKAGES}/ethereal_0.9.13-1.0progeny1_ia64.deb \
    ${PACKAGES}/ethereal-common_0.9.13-1.0progeny1_ia64.deb \
    ${PACKAGES}/ethereal-dev_0.9.13-1.0progeny1_ia64.deb \
    ${PACKAGES}/tethereal_0.9.13-1.0progeny1_ia64.deb

pdk semdiff -m ethereal-before.xml ethereal.xml | LANG=C sort >semdiff.txt
diff -u - semdiff.txt <<EOF
downgrade|deb|ethereal-common|0.9.13-1.0progeny2|0.9.13-1.0progeny1|ia64|ethereal.xml
downgrade|deb|ethereal-dev|0.9.13-1.0progeny2|0.9.13-1.0progeny1|ia64|ethereal.xml
downgrade|deb|ethereal|0.9.13-1.0progeny2|0.9.13-1.0progeny1|ia64|ethereal.xml
downgrade|deb|tethereal|0.9.13-1.0progeny2|0.9.13-1.0progeny1|ia64|ethereal.xml
downgrade|dsc|ethereal|0.9.13-1.0progeny2|0.9.13-1.0progeny1|any|ethereal.xml
EOF

cp ethereal.xml ethereal-before.xml

# Drop a package.
pdk package add -r ethereal.xml \
    ${PACKAGES}/ethereal_0.9.13-1.0progeny1.dsc \
    ${PACKAGES}/ethereal-common_0.9.13-1.0progeny1_ia64.deb \
    ${PACKAGES}/ethereal-dev_0.9.13-1.0progeny1_ia64.deb \
    ${PACKAGES}/tethereal_0.9.13-1.0progeny1_ia64.deb

pdk semdiff -m ethereal-before.xml ethereal.xml | grep -v ^unchanged \
    | LANG=C sort >semdiff.txt
diff -u - semdiff.txt <<EOF
drop|deb|ethereal|0.9.13-1.0progeny1|ia64|ethereal.xml
EOF

cp ethereal.xml ethereal-before.xml

# Add it back
pdk package add -r ethereal.xml \
    ${PACKAGES}/ethereal_0.9.13-1.0progeny1.dsc \
    ${PACKAGES}/ethereal_0.9.13-1.0progeny1_ia64.deb \
    ${PACKAGES}/ethereal-common_0.9.13-1.0progeny1_ia64.deb \
    ${PACKAGES}/ethereal-dev_0.9.13-1.0progeny1_ia64.deb \
    ${PACKAGES}/tethereal_0.9.13-1.0progeny1_ia64.deb

pdk semdiff -m ethereal-before.xml ethereal.xml | grep -v ^unchanged \
    | LANG=C sort >semdiff.txt
diff -u - semdiff.txt <<EOF
add|deb|ethereal|0.9.13-1.0progeny1|ia64|ethereal.xml
EOF
