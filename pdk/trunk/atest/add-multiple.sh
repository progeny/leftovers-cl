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

# add-multiple.sh
# $Progeny$
#
# test having pdk package add multiple files at once

# get Utility functions
. atest/test_lib.sh
. atest/utils/test_channel.sh

SERVER_PORT=$(unused_port 8120 8121 8122 8123 8124 8125 8126 8127 13847)

create_apache_conf $SERVER_PORT

pdk_bin=$(which pdk)
cat >etc/svn.apache2.conf <<EOF
ScriptAlias /telco/upload $pdk_bin
Alias /telco/ $tmp_dir/progeny-production/http/
PassEnv PATH PYTHONPATH
# Tell the cgi where its cache is.
SetEnv PDK_CACHE_PATH $tmp_dir/progeny-production/http/cache
EOF

$apache2_bin -t -f etc/apache2/apache2.conf
$apache2_bin -X -f etc/apache2/apache2.conf &

# -----------------------------------------------------------
# Bootstrap and do some "integration" work in the integration area.
# -----------------------------------------------------------

#First, create the workspace that we actually work in...
pdk workspace create integration

#Make the local channel
make_channel channel \
    apache2-common_2.0.53-5_i386.deb apache2_2.0.53-5.dsc \
    apache2_2.0.53-5.dsc \
    apache2-common_2.0.53-5_i386.deb \
    ethereal_0.9.13-1.0progeny2.dsc \
    ethereal_0.9.13-1.0progeny2_ia64.deb \
    ethereal-common_0.9.13-1.0progeny2_ia64.deb \
    ethereal-dev_0.9.13-1.0progeny2_ia64.deb \
    tethereal_0.9.13-1.0progeny2_ia64.deb

#Move to the ws root
cd integration

# Add a channel for the package directory
# note: this will migrate to a proper pdk command, like:
# pdk channel add --dir $PACKAGES progeny.com
cat >channels.xml <<EOF
<?xml version="1.0"?>
<channels>
  <channel>
    <type>dir</type>
    <path>${PACKAGES}</path>
  </channel>
</channels>
EOF

pdk channel update

[ -f channels.xml.cache ] \
    || fail 'channel cache file should have been created'

cd work
#note: this will become an effect of the pdk channel command above,
# pdk channel add --dir $PACKAGES progeny.com
mkdir progeny.com
cp ${tmp_dir}/atest/abstract_comps/*.xml progeny.com

pdk resolve progeny.com/apache.xml
pdk resolve progeny.com/ethereal.xml

pdk add progeny.com/apache.xml progeny.com/ethereal.xml
pdk commit master "this is a remark"

grep "md5:c14c96a4046f4fdaee13d915db38f882" progeny.com/ethereal.xml
grep "md5:48c9b3d4b22b22e72ac5a992054e31ff" progeny.com/ethereal.xml
grep "md5:fe1b75646c8fd7e769b4f16958efe75a" progeny.com/ethereal.xml
grep "md5:495db2b093364a55c5954eb6b89a13df" progeny.com/ethereal.xml
grep "md5:18bede30ec19d03770440903b157d16d" progeny.com/ethereal.xml
grep "md5:495db2b093364a55c5954eb6b89a13df" progeny.com/ethereal.xml
grep "md5:48c9b3d4b22b22e72ac5a992054e31ff" progeny.com/ethereal.xml
grep "md5:c14c96a4046f4fdaee13d915db38f882" progeny.com/ethereal.xml
grep "md5:fe1b75646c8fd7e769b4f16958efe75a" progeny.com/ethereal.xml
grep "md5:18bede30ec19d03770440903b157d16d" progeny.com/ethereal.xml
grep "md5:5acd04d4cc6e9d1530aad04accdc8eb5" progeny.com/apache.xml
grep "md5:d94c995bde2f13e04cdd0c21417a7ca5" progeny.com/apache.xml
grep "md5:d94c995bde2f13e04cdd0c21417a7ca5" progeny.com/apache.xml
grep "md5:5acd04d4cc6e9d1530aad04accdc8eb5" progeny.com/apache.xml

# vim:ai:et:sts=4:sw=4:tw=0:
