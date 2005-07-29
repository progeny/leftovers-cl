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

# Set umask now in preparation for later permissions checking.
umask 002

# Load the cache with the ida package so we don't get errors later
pdk add dummy.xml atest/packages/ida_2.01-1.2.dsc

# -----------------------------------------------------------
# Resolve from a pile of packages on the local filesystem.
# -----------------------------------------------------------

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
    <!-- make sure this is left alone -->
    <dsc ref="sha-1:5758b8cd6b604e872d60a257777cc9d3018c84c8">
      <name>ida</name>
      <version>2.01-1.2</version>
    </dsc>
    <!-- make sure this is also left alone -->
    <component>empty.xml</component>
    <!-- funny whitespace -->
    <deb>
      apache2-common
    </deb>
    <!-- Ian's funny whitespace -->
    <dsc>
      <name>
        apache2
      </name>
      <meta>
        <predicate>object</predicate>
      </meta>
    </dsc>
  </contents>
</component>
EOF

# Add a channel for the package directory
cat >channels.xml <<EOF
<?xml version="1.0"?>
<channels>
  <local>
    <type>dir</type>
    <path>atest/packages</path>
  </local>
</channels>
EOF

# update the channels
pdk updatechannels
[ -f channels.xml.cache ] \
    || fail 'channel cache file should have been created'

# Run the resolve command.
pdk resolve apache.xml

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
    <dsc ref="sha-1:5758b8cd6b604e872d60a257777cc9d3018c84c8">
      <name>ida</name>
      <version>2.01-1.2</version>
    </dsc>
    <component>empty.xml</component>
    <deb ref="md5:5acd04d4cc6e9d1530aad04accdc8eb5">
      <name>apache2-common</name>
      <version>2.0.53-5</version>
      <arch>i386</arch>
    </deb>
    <dsc ref="md5:d94c995bde2f13e04cdd0c21417a7ca5">
      <name>apache2</name>
      <version>2.0.53-5</version>
      <meta>
        <predicate>object</predicate>
      </meta>
    </dsc>
  </contents>
</component>
EOF

# "Download" missing packages.
pdk download apache.xml

compare_timestamps() {
    file1="$1"
    file2="$2"

    time1=$(stat -c '%Y' $file1)
    time2=$(stat -c '%Y' $file2)

    if [ "$time1" != "$time2" ]; then
        difference=$(($time2 - $time1))
        fail "timestamp mismatch $file1 $time1 -- $file2 $time2 -- $difference"
    fi
}

for file in $(find cache -type f); do
    perms=$(stat -c '%a' $file)
    [ 664 = "$perms" ] || fail "wrong permissions $perms for $file"
done

# Make sure the timestamps match the original files.
compare_timestamps \
    packages/apache2-common_2.0.53-5_i386.deb \
    cache/md5/5a/md5:5acd04d4cc6e9d1530aad04accdc8eb5
compare_timestamps \
    packages/apache2_2.0.53-5.dsc \
    cache/md5/d9/md5:d94c995bde2f13e04cdd0c21417a7ca5
compare_timestamps \
    packages/apache2_2.0.53-5.diff.gz \
    cache/md5/0d/md5:0d060d66b3a1e6ec0b9c58e995f7b9f7
compare_timestamps \
    packages/apache2_2.0.53.orig.tar.gz \
    cache/md5/40/md5:40507bf19919334f07355eda2df017e5

# -----------------------------------------------------------
# Resolve from an apt-able repository via http.
# -----------------------------------------------------------

pdk repogen apache.xml

# set up apache.
SERVER_PORT=$(unused_port 8100 8101 8102 8103 8104 8105 8106 8107 13847)

create_apache_conf $SERVER_PORT

cat >etc/svn.apache2.conf <<EOF
DocumentRoot $tmp_dir/repo/
EOF

$apache2_bin -t -f etc/apache2/apache2.conf
$apache2_bin -X -f etc/apache2/apache2.conf &

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
    <!-- make sure this is left alone -->
    <dsc ref="sha-1:5758b8cd6b604e872d60a257777cc9d3018c84c8">
      <name>ida</name>
      <version>2.01-1.2</version>
    </dsc>
    <!-- make sure this is also left alone -->
    <component>empty.xml</component>
    <deb>
      <name>apache2-common</name>
    </deb>
    <dsc>
      <name>apache2</name>
      <meta>
        <predicate>object</predicate>
      </meta>
    </dsc>
  </contents>
</component>
EOF

# start with a new channels file
cat >channels.xml <<EOF
<?xml version="1.0"?>
<channels>
  <local>
    <type>apt-deb</type>
    <path>http://localhost:$SERVER_PORT/</path>
    <archs>i386 source</archs>
    <dist>apache</dist>
    <components>main</components>
  </local>
</channels>
EOF

pdk updatechannels

# Resolve the component against the apt-deb repo.
pdk resolve apache.xml

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
    <dsc ref="sha-1:5758b8cd6b604e872d60a257777cc9d3018c84c8">
      <name>ida</name>
      <version>2.01-1.2</version>
    </dsc>
    <component>empty.xml</component>
    <deb ref="md5:5acd04d4cc6e9d1530aad04accdc8eb5">
      <name>apache2-common</name>
      <version>2.0.53-5</version>
      <arch>i386</arch>
    </deb>
    <dsc ref="md5:d94c995bde2f13e04cdd0c21417a7ca5">
      <name>apache2</name>
      <version>2.0.53-5</version>
      <meta>
        <predicate>object</predicate>
      </meta>
    </dsc>
  </contents>
</component>
EOF

# Clear all md5 packages. Leave the sha-1 one for now.
rm -r cache/md5/*

# "Download" missing packages.
pdk download apache.xml

for file in $(find cache -type f); do
    perms=$(stat -c '%a' $file)
    [ 664 = "$perms" ] || fail "wrong permissions $perms for $file"
done

# Make sure the timestamps match the original files.
compare_timestamps \
    packages/apache2-common_2.0.53-5_i386.deb \
    cache/md5/5a/md5:5acd04d4cc6e9d1530aad04accdc8eb5
compare_timestamps \
    packages/apache2_2.0.53-5.dsc \
    cache/md5/d9/md5:d94c995bde2f13e04cdd0c21417a7ca5
compare_timestamps \
    packages/apache2_2.0.53-5.diff.gz \
    cache/md5/0d/md5:0d060d66b3a1e6ec0b9c58e995f7b9f7
compare_timestamps \
    packages/apache2_2.0.53.orig.tar.gz \
    cache/md5/40/md5:40507bf19919334f07355eda2df017e5
