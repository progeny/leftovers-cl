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

# cache-push.sh
# $Progeny$
#
# Test the basic svk cycle.

# get Utility functions
. atest/test_lib.sh

# -------------------
# Setup
# -------------------

#First, create the workspace that we actually work in...
pdk workspace create sim-source
#Then, create the workspace that we will "cachepush" to...
pdk workspace create sim-dest
#Put the client in the place to do the descriptor work
#in the source workspace
cd sim-source/work

# Install all the packages into the local cache
#This needs to be replaced with the creation of
#a component with an abstract package,
#followed by "pdk resolve (descr.)
pdk package add progeny.com/apache.xml \
    $tmp_dir/packages/apache2-common_2.0.53-5_i386.deb \
    $tmp_dir/packages/apache2_2.0.53-5.dsc \

# add a whole product component
cat >progeny.com/sim-product.xml <<"EOF"
<?xml version="1.0"?>
<component>
  <component>progeny.com/apache.xml</component>
</component>
EOF
pdk add progeny.com/
pdk commit master foo
cd ..
# -------------------
# Client work sequence
# -------------------
pdk cachepush ../sim-dest/cache

# -------------------
# Post-condition evaluation
# -------------------

cd $tmp_dir

(cd sim-source; find cache) | grep -v .header$ | sort >expected
(cd sim-dest; find cache) | grep -v .header$ | sort >actual

diff -u expected actual
