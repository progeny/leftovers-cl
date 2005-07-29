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

# cachepull.sh
# $Progeny$
#
# Test pulling from a remote-cache.

# get Utility functions
. atest/test_lib.sh


# -------------------
# Setup
# -------------------

#First, create the workspaces that we actually work in...
pdk create remote1
pdk create remote2
#Then, create the workspace that we will "cachepull" to...
pdk create local
#Put the client in the place to do the descriptor work
pushd remote1/work

#add a descriptor to one remote workspace
#This needs to be replaced with the creation of
#a component with an abstract package,
#followed by "pdk resolve (descr.)
pdk add apache.xml \
    $tmp_dir/packages/apache2-common_2.0.53-5_i386.deb \
    $tmp_dir/packages/apache2_2.0.53-5.dsc \
    
popd
pushd remote2/work

#add a different descriptor to another remote workspace
#This needs to be replaced with the creation of
#a component with an abstract package,
#followed by "pdk resolve (descr.)
pdk add python.xml \
    $tmp_dir/packages/python_2.3.3-6_all.deb \
    $tmp_dir/packages/python_2.3.5-2_all.deb \
    $tmp_dir/packages/python-defaults_2.3.3-6.dsc \
    $tmp_dir/packages/python-defaults_2.3.5-2.dsc

popd
#copy just the descriptor files from the remotes
#to the local workspace
cp remote1/work/apache.xml local/work
cp remote2/work/python.xml local/work

# start apache
SERVER_PORT=$(unused_port 8200 8201 8202 8203 8204 8205 8206 8207 13847)
create_apache_conf $SERVER_PORT
cat >etc/svn.apache2.conf <<EOF
DocumentRoot $tmp_dir
EOF
$apache2_bin -t -f etc/apache2/apache2.conf
$apache2_bin -X -f etc/apache2/apache2.conf &

cd local/work

cat >cache-sources.conf.xml <<EOF
<?xml version="1.0"?>
<cache-sources>
  <_>file://$tmp_dir/remote1/cache</_>
  <_>http://localhost:$SERVER_PORT/nonesuch/</_>
  <_>http://localhost:$SERVER_PORT/remote2/cache</_>
</cache-sources>
EOF

cat >main.xml <<EOF
<?xml version="1.0"?>
<component>
  <contents>
    <component>apache.xml</component>
    <component>python.xml</component>
  </contents>
</component>
EOF

cat >whole-product.xml <<EOF
<?xml version="1.0"?>
<component>
  <contents>
    <component>main.xml</component>
  </contents>
</component>
EOF

# -------------------
# Client work sequence
# -------------------
pdk cachepull apache.xml python.xml

# -------------------
# Post-condition evaluation
# -------------------

pdk repogen whole-product.xml
