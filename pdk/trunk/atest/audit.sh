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

# audit.sh 
# $Progeny$
#
# Make sure that pdk audit catches problems.

# get Utility functions
. atest/test_lib.sh


# Install all the packages into the local cache
pdk add progeny.com/apache.xml \
    packages/apache2-common_2.0.53-5_i386.deb \
    packages/apache2_2.0.53-5.dsc \

pdk add progeny.com/emacs.xml \
    packages/emacs-defaults_1.1.dsc \
    packages/emacs-defaults_1.1_all.deb

pdk audit progeny.com/apache.xml progeny.com/emacs.xml \
    >pdk_audit.txt || {
    cat pdk_audit.txt
    bail "Audit did not pass"
}

diff -u - pdk_audit.txt <<EOF
EOF

# Start fresh.
rm -r cache/ progeny.com/

# Reinstall emacs-defaults without it's source.
pdk add progeny.com/emacs.xml \
    packages/emacs-defaults_1.1_all.deb

pdk add progeny.com/apache.xml \
    packages/apache2-common_2.0.53-5_i386.deb \
    packages/apache2_2.0.53-5.dsc \

# Make one file go AWOL.
rm $(cachepath 'md5:0d060d66b3a1e6ec0b9c58e995f7b9f7')

# Corrupt a file.
echo asdfasdfadsf >> $(cachepath 'sha-1:b7d31cf9a160c3aadaf5f1cd86cdc8762b3d4b1b')

# Add an unknown file.
echo asdf >cache/duh

pdk audit progeny.com/apache.xml progeny.com/emacs.xml \
    >pdk_audit.raw.txt && fail 'pdk audit should fail' || status=$?
test "$status" = "1" || fail 'pdk audit should return exit code 1.'
LANG=C sort <pdk_audit.raw.txt >pdk_audit.txt
echo ""

cat > expected.txt <<EOF
deb,emacs-defaults,1.1,||missing source
duh|('md5:', 'sha-1:')|unknown prefix
duh||checksum mismatch
md5:0d060d66b3a1e6ec0b9c58e995f7b9f7|progeny.com/apache.xml|missing from cache
md5:5acd04d4cc6e9d1530aad04accdc8eb5|md5:3d9189fb30f41480dec2d513dc800a70|checksum mismatch
sha-1:b7d31cf9a160c3aadaf5f1cd86cdc8762b3d4b1b|sha-1:bbf4c316da08357663c706ecd0eec65e7c73a97a|checksum mismatch
EOF

cat pdk_audit.raw.txt
cat pdk_audit.txt

diff -u expected.txt pdk_audit.txt 

