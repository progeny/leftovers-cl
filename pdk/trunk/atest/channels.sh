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

# channels.sh
# $Progeny$
#
# Try to update from channels of various types.

. atest/test_lib.sh

SERVER_PORT=$(unused_port 8103 8104 8105 8106 8107 13847)
create_apache_conf $SERVER_PORT

cat >etc/remote.apache2.conf <<EOF
DocumentRoot $tmp_dir
Alias /repo/ $tmp_dir/test-repogen/repo/
Alias /repo-nodists/ $tmp_dir/repo-nodists/
EOF

$apache2_bin -t -f etc/apache2/apache2.conf
$apache2_bin -X -f etc/apache2/apache2.conf &

. atest/utils/repogen-fixture.sh

mkdir repo-nodists
cp \
    $PACKAGES/apache2_2.0.53-5.diff.gz \
    $PACKAGES/apache2_2.0.53-5.dsc \
    $PACKAGES/apache2_2.0.53.orig.tar.gz \
    $PACKAGES/apache2-common_2.0.53-5_i386.deb \
    repo-nodists
pushd repo-nodists;
    apt-ftparchive packages . >Packages.gz
    apt-ftparchive sources . >Sources.gz
popd

set_up_repogen_fixture test-repogen
cd test-repogen

pdk repogen product.xml

cat >etc/channels.xml <<EOF
<?xml version="1.0"?>
<channels>
  <local>
    <type>dir</type>
    <path>repo/pool</path>
  </local>
  <apt-deb>
    <type>apt-deb</type>
    <path>http://localhost:$SERVER_PORT/repo/</path>
    <dist>stable</dist>
    <components>main</components>
    <archs>source i386</archs>
  </apt-deb>
  <nodists>
    <type>apt-deb</type>
    <path>http://localhost:$SERVER_PORT/repo-nodists/</path>
    <dist>./</dist>
    <archs>source binary</archs>
  </nodists>
</channels>
EOF

pdk channel update

compare_files() {
    diff -u $1 $2
    compare_timestamps $1 $2
}

prefix=http_localhost_${SERVER_PORT}_repo_dists
compare_files \
    repo/dists/stable/main/binary-i386/Packages.gz \
    etc/channels/${prefix}_stable_main_binary-i386_Packages.gz

compare_files \
    repo/dists/stable/main/source/Sources.gz \
    etc/channels/${prefix}_stable_main_source_Sources.gz

prefix=http_localhost_${SERVER_PORT}_repo-nodists_.
compare_files \
    $tmp_dir/repo-nodists/Packages.gz \
    etc/channels/${prefix}_Packages.gz

compare_files \
    $tmp_dir/repo-nodists/Sources.gz \
    etc/channels/${prefix}_Sources.gz

# this tests the "already downloaded" code.
pdk channel update

prefix=http_localhost_${SERVER_PORT}_repo_dists
compare_files \
    repo/dists/stable/main/binary-i386/Packages.gz \
    etc/channels/${prefix}_stable_main_binary-i386_Packages.gz

compare_files \
    repo/dists/stable/main/source/Sources.gz \
    etc/channels/${prefix}_stable_main_source_Sources.gz

prefix=http_localhost_${SERVER_PORT}_repo-nodists_.
compare_files \
    $tmp_dir/repo-nodists/Packages.gz \
    etc/channels/${prefix}_Packages.gz

compare_files \
    $tmp_dir/repo-nodists/Sources.gz \
    etc/channels/${prefix}_Sources.gz
