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

SERVER_PORT=$(unused_port 8100 8101 8102 8103 8104 8105 8106 8107 13847)

create_apache_conf $SERVER_PORT

pdk_bin=$(which pdk)
cat >etc/svn.apache2.conf <<EOF
ScriptAlias /telco/upload $pdk_bin
Alias /telco/ $tmp_dir/production/
PassEnv PATH PYTHONPATH
# Tell the cgi where its cache is.
SetEnv PDK_CACHE_PATH $tmp_dir/production/cache
EOF

$apache2_bin -t -f etc/apache2/apache2.conf
$apache2_bin -X -f etc/apache2/apache2.conf &

# -----------------------------------------------------------
# Common Functions
# -----------------------------------------------------------

create_snapshot() {
    # Creates snap.tar. In real production that part of the
    # process could be separated and done infrequently. (cron weekly)
    local local_path=$1
    local local_vc_path=$local_path/VC

    tar Cc $local_vc_path . > $local_vc_path/../snap.tar.tmp
    mv $local_vc_path/../snap.tar.tmp $local_vc_path/../snap.tar
}


# -----------------------------------------------------------
# Bootstrap and do some "integration" work in the integration area.
# -----------------------------------------------------------

pdk workspace create integration
pushd integration/work
    #This needs to be replaced with the creation of
    #a component with an abstract package,
    #followed by "pdk resolve (descr.)":
    pdk package add progeny.com/apache.xml \
        ${PACKAGES}/apache2_2.0.53-5.dsc \
        ${PACKAGES}/apache2-common_2.0.53-5_i386.deb

    pdk add progeny.com/apache.xml
    pdk commit master "git-production commit"

    pdk repogen progeny.com/apache.xml
popd

# -----------------------------------------------------------
# Set up production environment with initial production data
# -----------------------------------------------------------

pdk workspace create production
pushd production/work
    pdk production_pull $tmp_dir/integration $tmp_dir/production master || bail "Pull failed"
    create_snapshot $tmp_dir/production
popd

echo "Where should this take place?"
pdk production_pull $tmp_dir/integration $tmp_dir/production master 

create_snapshot $tmp_dir/production

# -----------------------------------------------------------
# Push packages from integration to production.
# -----------------------------------------------------------

pushd integration
    pdk cachepush http://localhost:$SERVER_PORT/telco/upload
    ls cache/ | grep -v .header$ >$tmp_dir/expected
popd

ls production/cache >actual
diff -u expected actual

# -----------------------------------------------------------
# Initial customer product retrieval.
# -----------------------------------------------------------
pdk clone http://localhost:$SERVER_PORT/telco/ \
    customer-work-area progeny.com local 

# -----------------------------------------------------------
# Customer moves to work area and makes a local change.
# -----------------------------------------------------------

pushd customer-work-area/work

    echo >>progeny.com/apache.xml
    echo GARBAGE >>progeny.com/apache.xml

    parent_id=$(cat .git/HEAD)
    pdk commit master "git-production testing"

    # Send change from customer to integration.
    git-diff-tree -p -r $parent_id $(cat .git/HEAD) >patch.txt

    # really this file would be sent by email.
    cp patch.txt $tmp_dir/integration/work/patch.txt

popd

# -----------------------------------------------------------
# Apply change from customer to integration
# -----------------------------------------------------------

pushd integration/work
    git-apply patch.txt
    pdk commit master "Required commit remark"
popd
# -----------------------------------------------------------
# Pull from integration to production (again)
# -----------------------------------------------------------

pdk production_pull $tmp_dir/integration $tmp_dir/production master || bail "Pulling from int->prod"

# -----------------------------------------------------------
# Pull from production to customer (again)
# -----------------------------------------------------------

cd customer-work-area
pdk update progeny.com 
grep GARBAGE work/progeny.com/apache.xml
