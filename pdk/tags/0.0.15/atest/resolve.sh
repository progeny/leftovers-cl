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
# references. It should leave concrete references alone.

. atest/test_lib.sh
. atest/utils/test_channel.sh

# Set umask now in preparation for later permissions checking.
umask 002

pdk workspace create resolve

testroot=$(pwd)
cachedir=${testroot}/resolve/etc/cache
channels=${testroot}/resolve/etc/channels.xml
project=${testroot}/resolve
etc=${testroot}/etc

mkdir ${etc}
cd $project

# -----------------------------------------------------------
# Resolve from a pile of packages on the local filesystem.
# -----------------------------------------------------------

cat >empty.xml <<EOF
<?xml version="1.0"?>
<component/>
EOF

# Add some concrete and abstract package references to a new component.
cat >apache.xml <<EOF
<?xml version="1.0"?>
<component>
  <id>resolveme</id>
  <name>Resolve Me</name>
  <description>
    I need to be resolved
  </description>
  <requires>a</requires>
  <requires>b</requires>
  <provides>c</provides>
  <provides>d</provides>
  <contents>
    <!-- Ian's funny whitespace -->
    <dsc>
      <name>
        ida
      </name>
      <version>2.01-1.2</version>
      <meta>
        <predicate>object</predicate>
      </meta>
    </dsc>
    <component>empty.xml</component>
    <!-- funny whitespace -->
    <deb>
      apache2-common
    </deb>
    <!-- binary with metadata. watch for regression -->
    <deb>
      <name>ethereal-common</name>
      <meta>
        <test>data</test>
      </meta>
    </deb>
    <!-- this should be left alone -->
    <deb>
      <name>tethereal</name>
      <meta>
        <comment>this whole section should be left alone</comment>
      </meta>
      <deb ref="md5:904fce57cb39662e9560f0143d326bb8">
        <name>tethereal</name>
        <version>0.9.4-1woody4</version>
        <arch>ia64</arch>
      </deb>
      <dsc ref="md5:a6456b3e20f44a3f53256bf722c010cd">
        <name>ethereal</name>
        <version>0.9.4-1woody4</version>
      </dsc>
    </deb>
  </contents>
</component>
EOF

make_channel channel-1 ida_2.01-1.2_arm.deb ida_2.01-1.2.diff.gz \
    ida_2.01-1.2.dsc ida_2.01.orig.tar.gz

make_channel channel-2 apache2_2.0.53-5.diff.gz apache2_2.0.53-5.dsc \
    apache2_2.0.53.orig.tar.gz apache2-common_2.0.53-5_i386.deb \
    ethereal-common_0.9.4-1woody2_i386.deb \
    ethereal-common_0.9.4-1woody2_ia64.deb \
    ethereal_0.9.4-1woody2.dsc \
    ethereal_0.9.4-1woody2.diff.gz \
    ethereal_0.9.4.orig.tar.gz \
    ethereal_0.9.4-1woody5.dsc \
    ethereal_0.9.4-1woody5.diff.gz \
    tethereal_0.9.4-1woody5_ia64.deb

make_channel channel-3 \
    ethereal_0.9.4-1woody4.dsc \
    ethereal_0.9.4-1woody4.diff.gz \
    ethereal_0.9.4.orig.tar.gz \
    tethereal_0.9.4-1woody4_ia64.deb

# Add a channel for the package directory
cat >${channels} <<EOF
<?xml version="1.0"?>
<channels>
  <channel-1>
    <type>dir</type>
    <path>$(pwd)/channel-1</path>
  </channel-1>
  <channel-2>
    <type>dir</type>
    <path>$(pwd)/channel-2</path>
  </channel-2>
  <channel-3>
    <type>dir</type>
    <path>$(pwd)/channel-3</path>
  </channel-3>
</channels>
EOF

pdk channel update

# Make sure dry run creates a report but doesn't change anything.
cp apache.xml old-apache.xml
pdk resolve apache.xml channel-1 -m >test-report.txt -n
diff -u old-apache.xml apache.xml

pdk resolve apache.xml channel-1 -m >report.txt
# Here's where we test the dry run report
diff -u test-report.txt report.txt
pdk resolve apache.xml channel-2 -m >>report.txt
LANG=C sort report.txt >sorted-report.txt

# Check that the semdiff report comes out as expected.
# The downgrade line is an artifact: two different source packages in
# the same file with the same name.
diff -u - sorted-report.txt <<EOF
add|deb|apache2-common|2.0.53-5|i386|apache.xml
add|deb|ethereal-common|0.9.4-1woody2|i386|apache.xml
add|deb|ethereal-common|0.9.4-1woody2|ia64|apache.xml
add|deb|ida|2.01-1.2|arm|apache.xml
add|dsc|apache2|2.0.53-5|any|apache.xml
add|dsc|ida|2.01-1.2|any|apache.xml
downgrade|dsc|ethereal|0.9.4-1woody4|0.9.4-1woody2|any|apache.xml
meta-add|deb|ethereal-common|i386|test|data
meta-add|deb|ethereal-common|ia64|test|data
meta-add|deb|tethereal|ia64|comment|this whole section should be left alone
unchanged|deb|ida|2.01-1.2|2.01-1.2|arm|apache.xml
unchanged|deb|tethereal|0.9.4-1woody4|0.9.4-1woody4|ia64|apache.xml
unchanged|deb|tethereal|0.9.4-1woody4|0.9.4-1woody4|ia64|apache.xml
unchanged|dsc|ethereal|0.9.4-1woody4|0.9.4-1woody4|any|apache.xml
unchanged|dsc|ethereal|0.9.4-1woody4|0.9.4-1woody4|any|apache.xml
unchanged|dsc|ida|2.01-1.2|2.01-1.2|any|apache.xml
EOF

# Check that the result is what we expect
# Note, xml comments are not preseved.
diff -u - apache.xml <<EOF || bail 'apache.xml differs'
<?xml version="1.0" encoding="utf-8"?>
<component>
  <id>resolveme</id>
  <name>Resolve Me</name>
  <description>
    I need to be resolved
  </description>
  <requires>a</requires>
  <requires>b</requires>
  <provides>c</provides>
  <provides>d</provides>
  <contents>
    <dsc>
      <name>ida</name>
      <version>2.01-1.2</version>
      <meta>
        <predicate>object</predicate>
      </meta>
      <deb ref="md5:fe2f5a4e8d4e7ae422e71b5bdfaa1e9c">
        <name>ida</name>
        <version>2.01-1.2</version>
        <arch>arm</arch>
      </deb>
      <dsc ref="md5:64863d0fde185cc7e572556729fa6f33">
        <name>ida</name>
        <version>2.01-1.2</version>
      </dsc>
    </dsc>
    <component>empty.xml</component>
    <deb>
      <name>apache2-common</name>
      <deb ref="md5:5acd04d4cc6e9d1530aad04accdc8eb5">
        <name>apache2-common</name>
        <version>2.0.53-5</version>
        <arch>i386</arch>
      </deb>
      <dsc ref="md5:d94c995bde2f13e04cdd0c21417a7ca5">
        <name>apache2</name>
        <version>2.0.53-5</version>
      </dsc>
    </deb>
    <deb>
      <name>ethereal-common</name>
      <meta>
        <test>data</test>
      </meta>
      <deb ref="md5:fead37813e0a8b27b2d198ed96a09e72">
        <name>ethereal-common</name>
        <version>0.9.4-1woody2</version>
        <arch>i386</arch>
      </deb>
      <deb ref="md5:d71f6a54b81e9a02fa90fe9d9f655fac">
        <name>ethereal-common</name>
        <version>0.9.4-1woody2</version>
        <arch>ia64</arch>
      </deb>
      <dsc ref="md5:3422eaafcc0c6790921c2fadcfb45c21">
        <name>ethereal</name>
        <version>0.9.4-1woody2</version>
      </dsc>
    </deb>
    <deb>
      <name>tethereal</name>
      <meta>
        <comment>this whole section should be left alone</comment>
      </meta>
      <deb ref="md5:904fce57cb39662e9560f0143d326bb8">
        <name>tethereal</name>
        <version>0.9.4-1woody4</version>
        <arch>ia64</arch>
      </deb>
      <dsc ref="md5:a6456b3e20f44a3f53256bf722c010cd">
        <name>ethereal</name>
        <version>0.9.4-1woody4</version>
      </dsc>
    </deb>
  </contents>
</component>
EOF

# Note -- one should be able to do this from any directory
mkdir junk
pushd junk
pdk download ../apache.xml 
popd

# "Download" missing packages.
pdk download apache.xml

for file in $(find ${cachedir} -type f); do
    perms=$(stat -c '%a' $file)
    [ 664 = "$perms" ] || bail "wrong permissions $perms for $file"
done

# Make sure the timestamps match the original files.
compare_timestamps \
    ${PACKAGES}/apache2-common_2.0.53-5_i386.deb \
    ${cachedir}/md5/5a/md5:5acd04d4cc6e9d1530aad04accdc8eb5
compare_timestamps \
    ${PACKAGES}/apache2_2.0.53-5.dsc \
    ${cachedir}/md5/d9/md5:d94c995bde2f13e04cdd0c21417a7ca5
compare_timestamps \
    ${PACKAGES}/apache2_2.0.53-5.diff.gz \
    ${cachedir}/md5/0d/md5:0d060d66b3a1e6ec0b9c58e995f7b9f7
compare_timestamps \
    ${PACKAGES}/apache2_2.0.53.orig.tar.gz \
    ${cachedir}/md5/40/md5:40507bf19919334f07355eda2df017e5

# -----------------------------------------------------------
# Resolve from an apt-able repository via http.
# -----------------------------------------------------------

pdk repogen apache.xml


# set up apache.
cd ${testroot}
SERVER_PORT=$(unused_port 8103 8104 8105 8106 8107 13847)
create_apache_conf $SERVER_PORT

cat >${etc}/svn.apache2.conf <<EOF
DocumentRoot ${project}/repo/
EOF

$apache2_bin -t -f ${etc}/apache2/apache2.conf
$apache2_bin -X -f ${etc}/apache2/apache2.conf &

# Add some concrete and abstract package references to a new component.
cd ${project}
cat >apache.xml <<EOF
<?xml version="1.0"?>
<component>
  <id>resolveme</id>
  <name>Resolve Me</name>
  <description>
    I need to be resolved
  </description>
  <requires>a</requires>
  <requires>b</requires>
  <provides>c</provides>
  <provides>d</provides>
  <contents>
    <!-- Ian's funny whitespace -->
    <dsc>
      <name>
        ida
      </name>
      <version>2.01-1.2</version>
      <meta>
        <predicate>object</predicate>
      </meta>
    </dsc>
    <component>empty.xml</component>
    <!-- funny whitespace -->
    <deb>
      apache2-common
    </deb>
    <deb>
      <name>ethereal-common</name>
      <meta>
        <test>data</test>
      </meta>
    </deb>
    <!-- this should be left alone -->
    <deb>
      <name>tethereal</name>
      <meta>
        <comment>this whole section should be left alone</comment>
      </meta>
      <deb ref="md5:904fce57cb39662e9560f0143d326bb8">
        <name>tethereal</name>
        <version>0.9.4-1woody4</version>
        <arch>ia64</arch>
      </deb>
      <dsc ref="md5:a6456b3e20f44a3f53256bf722c010cd">
        <name>ethereal</name>
        <version>0.9.4-1woody4</version>
      </dsc>
    </deb>
  </contents>
</component>
EOF

# start with a new channels file
cat >${channels} <<EOF
<?xml version="1.0"?>
<channels>
  <local>
    <type>apt-deb</type>
    <path>http://localhost:$SERVER_PORT/</path>
    <archs>arm i386 ia64 source</archs>
    <dist>apache</dist>
    <components>main</components>
  </local>
</channels>
EOF

pdk channel update

# Resolve the component against the apt-deb repo.
pdk resolve apache.xml

# Should also be able to resolve apache.xml from 
# a different directory
cd junk
pdk resolve ../apache.xml

test -f apache.xml && bail "Rewritten file in wrong dir"
cd -

# Check that the result is what we expect
diff -u - apache.xml <<EOF || bail 'apache.xml differs'
<?xml version="1.0" encoding="utf-8"?>
<component>
  <id>resolveme</id>
  <name>Resolve Me</name>
  <description>
    I need to be resolved
  </description>
  <requires>a</requires>
  <requires>b</requires>
  <provides>c</provides>
  <provides>d</provides>
  <contents>
    <dsc>
      <name>ida</name>
      <version>2.01-1.2</version>
      <meta>
        <predicate>object</predicate>
      </meta>
      <deb ref="md5:fe2f5a4e8d4e7ae422e71b5bdfaa1e9c">
        <name>ida</name>
        <version>2.01-1.2</version>
        <arch>arm</arch>
      </deb>
      <dsc ref="md5:64863d0fde185cc7e572556729fa6f33">
        <name>ida</name>
        <version>2.01-1.2</version>
      </dsc>
    </dsc>
    <component>empty.xml</component>
    <deb>
      <name>apache2-common</name>
      <deb ref="md5:5acd04d4cc6e9d1530aad04accdc8eb5">
        <name>apache2-common</name>
        <version>2.0.53-5</version>
        <arch>i386</arch>
      </deb>
      <dsc ref="md5:d94c995bde2f13e04cdd0c21417a7ca5">
        <name>apache2</name>
        <version>2.0.53-5</version>
      </dsc>
    </deb>
    <deb>
      <name>ethereal-common</name>
      <meta>
        <test>data</test>
      </meta>
      <deb ref="md5:fead37813e0a8b27b2d198ed96a09e72">
        <name>ethereal-common</name>
        <version>0.9.4-1woody2</version>
        <arch>i386</arch>
      </deb>
      <deb ref="md5:d71f6a54b81e9a02fa90fe9d9f655fac">
        <name>ethereal-common</name>
        <version>0.9.4-1woody2</version>
        <arch>ia64</arch>
      </deb>
      <dsc ref="md5:3422eaafcc0c6790921c2fadcfb45c21">
        <name>ethereal</name>
        <version>0.9.4-1woody2</version>
      </dsc>
    </deb>
    <deb>
      <name>tethereal</name>
      <meta>
        <comment>this whole section should be left alone</comment>
      </meta>
      <deb ref="md5:904fce57cb39662e9560f0143d326bb8">
        <name>tethereal</name>
        <version>0.9.4-1woody4</version>
        <arch>ia64</arch>
      </deb>
      <dsc ref="md5:a6456b3e20f44a3f53256bf722c010cd">
        <name>ethereal</name>
        <version>0.9.4-1woody4</version>
      </dsc>
    </deb>
  </contents>
</component>
EOF

# Clear all md5 packages. Leave the sha-1 one for now.
rm -r ${cachedir}/md5/*

# "Download" missing packages.
pdk download apache.xml

# Download a second time.
pdk download apache.xml 2>stderr.txt

# Stderr should be empty. In particular, there should be no progress bars.
diff -u stderr.txt - <<EOF
EOF

for file in $(find ${cachedir} -type f); do
    perms=$(stat -c '%a' $file)
    [ 664 = "$perms" ] || bail "wrong permissions $perms for $file"
done

# Make sure the timestamps match the original files.
compare_timestamps \
    ${PACKAGES}/apache2-common_2.0.53-5_i386.deb \
    ${cachedir}/md5/5a/md5:5acd04d4cc6e9d1530aad04accdc8eb5
compare_timestamps \
    ${PACKAGES}/apache2_2.0.53-5.dsc \
    ${cachedir}/md5/d9/md5:d94c995bde2f13e04cdd0c21417a7ca5
compare_timestamps \
    ${PACKAGES}/apache2_2.0.53-5.diff.gz \
    ${cachedir}/md5/0d/md5:0d060d66b3a1e6ec0b9c58e995f7b9f7
compare_timestamps \
    ${PACKAGES}/apache2_2.0.53.orig.tar.gz \
    ${cachedir}/md5/40/md5:40507bf19919334f07355eda2df017e5
