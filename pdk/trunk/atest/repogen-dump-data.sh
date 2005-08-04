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

# resolve.sh
# $Progeny$
#
# The resolve command should transform abstract references to concrete
# references.

. atest/test_lib.sh

mkdir channel
cp packages/apache2-common_2.0.53-5_i386.deb channel
cp packages/passwd-0.68-10.i386.rpm channel

# Add some concrete and abstract package references to a new component.
cat >apache.xml <<EOF
<?xml version="1.0"?>
<component>
  <contents>
    <deb>
      <name>apache2-common</name>
      <meta>
        <predicate>object</predicate>
        <one-more>thing</one-more>
      </meta>
    </deb>
    <rpm>passwd</rpm>
  </contents>
</component>
EOF

cat >separate-report.xml <<EOF
<?xml version="1.0"?>
<component>
  <meta>
    <repo-type>report</repo-type>
    <package-format>%(name)s %(epoch)s %(version)s %(release)s %(filename)s %(cache_location)s %(blob_id)s</package-format>
    <meta-format>%(subject)s %(predicate)s %(target)s</meta-format>
  </meta>
  <contents>
    <component>apache.xml</component>
  </contents>
</component>
EOF

cat >joined-report.xml <<EOF
<?xml version="1.0"?>
<component>
  <meta>
    <repo-type>report</repo-type>
    <combined-format>%(name)s %(epoch)s %(version)s %(release)s %(filename)s %(cache_location)s %(blob_id)s %(predicate)s %(target)s</combined-format>
  </meta>
  <contents>
    <component>apache.xml</component>
  </contents>
</component>
EOF

# Add a channel for the package directory
cat >channels.xml <<EOF
<?xml version="1.0"?>
<channels>
  <local>
    <type>dir</type>
    <path>channel</path>
  </local>
</channels>
EOF

pdk channel update
[ -f channels.xml.cache ] \
    || fail 'channel cache file should have been created'

pdk resolve apache.xml local

pdk download apache.xml

pdk repogen separate-report.xml >report.txt
diff -u - report.txt <<EOF
apache2-common  2.0.53 5 apache2-common_2.0.53-5_i386.deb $tmp_dir/cache/md5/5a/md5:5acd04d4cc6e9d1530aad04accdc8eb5 md5:5acd04d4cc6e9d1530aad04accdc8eb5
passwd  0.68 10 passwd-0.68-10.i386.rpm $tmp_dir/cache/md5/d0/md5:d02b15b9e0f4e861c3fe82aed11801eb md5:d02b15b9e0f4e861c3fe82aed11801eb

md5:5acd04d4cc6e9d1530aad04accdc8eb5 one-more thing
md5:5acd04d4cc6e9d1530aad04accdc8eb5 predicate object

EOF

pdk repogen joined-report.xml >report.txt
diff -u - report.txt <<EOF
apache2-common  2.0.53 5 apache2-common_2.0.53-5_i386.deb $tmp_dir/cache/md5/5a/md5:5acd04d4cc6e9d1530aad04accdc8eb5 md5:5acd04d4cc6e9d1530aad04accdc8eb5 one-more thing
apache2-common  2.0.53 5 apache2-common_2.0.53-5_i386.deb $tmp_dir/cache/md5/5a/md5:5acd04d4cc6e9d1530aad04accdc8eb5 md5:5acd04d4cc6e9d1530aad04accdc8eb5 predicate object
passwd  0.68 10 passwd-0.68-10.i386.rpm $tmp_dir/cache/md5/d0/md5:d02b15b9e0f4e861c3fe82aed11801eb md5:d02b15b9e0f4e861c3fe82aed11801eb  

EOF
