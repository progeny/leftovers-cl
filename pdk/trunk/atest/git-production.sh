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

# git-production.sh
# $Progeny$
#
# test having git and pdk cache-pull talk to a real apache2 server.

# get Utility functions
. atest/test_lib.sh

SERVER_PORT=$(unused_port 8110 8111 8112 8113 8114 8115 8116 8117 13847)

create_apache_conf $SERVER_PORT

pdk_bin=$(which pdk)
cat >etc/svn.apache2.conf <<EOF
ScriptAlias /telco/upload $pdk_bin
Alias /telco/ $tmp_dir/production/
PassEnv PATH PYTHONPATH
# Tell the cgi where its cache is.
SetEnv PDK_CACHE_PATH $tmp_dir/production/etc/cache
EOF

$apache2_bin -t -f etc/apache2/apache2.conf
$apache2_bin -X -f etc/apache2/apache2.conf &

# -----------------------------------------------------------
# Bootstrap and do some "integration" work in the integration area.
# -----------------------------------------------------------

pdk workspace create production
pdk workspace create integration
pushd integration
    #This needs to be replaced with the creation of
    #a component with an abstract package,
    #followed by "pdk resolve (descr.)":
    pdk package add progeny.com/apache.xml \
        ${PACKAGES}/apache2_2.0.53-5.dsc \
        ${PACKAGES}/apache2-common_2.0.53-5_i386.deb

    pdk add progeny.com/apache.xml
    pdk commit "git-production commit"

    pdk repogen progeny.com/apache.xml

# -----------------------------------------------------------
# Populate production environment with initial production data
# -----------------------------------------------------------

    pdk publish $tmp_dir/production
popd

(cd integration; find cache | grep -v .header ) >expected
(cd production; find cache | grep -v .header ) >actual
diff -u expected actual || fail 'caches should match'
diff -u integration/etc/git/refs/heads/master \
    production/etc/git/refs/heads/master

# -----------------------------------------------------------
# Initial customer product retrieval.
# -----------------------------------------------------------
pdk workspace create customer-work-area
pushd customer-work-area
    pdk subscribe http://localhost:$SERVER_PORT/telco/ progeny.com
    [ -e $tmp_dir/customer-work-area/etc/sources/progeny.com ] \
        || fail "progeny.com subscription not created"
    pdk download progeny.com/apache.xml
    pdk repogen progeny.com/apache.xml

# -----------------------------------------------------------
# Customer makes a local change.
# -----------------------------------------------------------

    echo GARBAGE >>progeny.com/apache.xml

    pdk commit "git-production testing"

    # Send change from customer to integration.
    git diff HEAD^ >patch.txt

    # really this file would be sent by email.
    cp patch.txt $tmp_dir/integration/patch.txt

popd

# -----------------------------------------------------------
# Apply change from customer to integration
# -----------------------------------------------------------

pushd integration
    # No direct pdk support for this. This case is an outlier.
    git-apply patch.txt
    pdk commit "Required commit remark"

# -----------------------------------------------------------
# Push from integration to production (again)
# -----------------------------------------------------------

    pdk publish $tmp_dir/production
popd

# -----------------------------------------------------------
# Pull from production to customer (again)
# -----------------------------------------------------------

pushd customer-work-area
    pdk update_from_remote progeny.com
    grep GARBAGE progeny.com/apache.xml
popd

# vim:ai:et:sts=4:sw=4:tw=0:
