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
# Test the cache push cycle.

# get Utility functions
. atest/test_lib.sh
. atest/utils/test_channel.sh

# -------------------
# Setup
# -------------------

#First, create the workspace that we actually work in...
pdk workspace create sim-source
#Then, create the workspace that we will "cachepush" to...
pdk workspace create sim-dest

#from test_channel.sh
make_channel channel apache2*.deb apache2*.dsc ethereal*.dsc

cd sim-source

#from test_channel.sh
config_channel

pdk channel update
[ -f outside_world.cache ] \
    || fail 'channel cache file should have been created'

cd work

#note: this will become an effect of the pdk channel command above,
# pdk channel add --dir $PACKAGES progeny.com
mkdir progeny.com
cp ${tmp_dir}/atest/abstract_comps/apache.xml progeny.com
cp ${tmp_dir}/atest/abstract_comps/sim-product.xml progeny.com

pdk resolve progeny.com/apache.xml
pdk download progeny.com/apache.xml

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
