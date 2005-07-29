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
Alias /telco/ $tmp_dir/progeny-production/http/
PassEnv PATH PYTHONPATH
# Tell the cgi where its cache is.
SetEnv PDK_CACHE_PATH $tmp_dir/progeny-production/http/cache
EOF

$apache2_bin -t -f etc/apache2/apache2.conf
$apache2_bin -X -f etc/apache2/apache2.conf &

# -----------------------------------------------------------
# Common Functions
# -----------------------------------------------------------

do_production_pull() {
    # Does a pull from one git directory to another.
    # Unlike other commands, does not assume work/.git directory
    # layout.
    # Also creates snap.tar. In real production that part of the
    # process could be separated and done infrequently. (cron weekly)

    local remote_path=$1
    local remote_head_name=$2
    local local_path=$3
    local local_head_name=$4

    GIT_DIR=$local_path
    export GIT_DIR

    if [ ! -e $GIT_DIR ]; then
        mkdir -p $GIT_DIR
        git-init-db
    fi
    remote_commit_id=$(cat $remote_path/refs/heads/$remote_head_name)
    git-local-pull -a -l $remote_commit_id $remote_path
    echo $remote_commit_id >$local_path/refs/heads/$local_head_name
    # now update the snapshot
    tar Cc $local_path . > $local_path/../snap.tar.tmp
    mv $local_path/../snap.tar.tmp $local_path/../snap.tar
    cd $tmp_dir
    unset GIT_DIR
}


# -----------------------------------------------------------
# Bootstrap and do some "integration" work in the integration area.
# -----------------------------------------------------------

pdk create integration
cd integration/work

#This needs to be resolved with the creation of
#a component with an abstract package,
#followed by "pdk resolve (descr.)
pdk add progeny.com/apache.xml \
    $tmp_dir/packages/apache2_2.0.53-5.dsc \
    $tmp_dir/packages/apache2-common_2.0.53-5_i386.deb

pdk vcadd progeny.com/apache.xml
pdk commit master "this is a remark"
cd ..

# -----------------------------------------------------------
# Set up production environment with initial production data
# -----------------------------------------------------------
mkdir -p $tmp_dir/progeny-production/http/cache
mkdir -p $tmp_dir/progeny-production/http/docs
mkdir -p $tmp_dir/progeny-production/http/install
do_production_pull \
    $tmp_dir/integration/work/.git \
    master \
    $tmp_dir/progeny-production/http/git \
    master

# -----------------------------------------------------------
# Push packages from integration to production.
# -----------------------------------------------------------
# Now I wish I had a complete cache pull, which does what cachepush does but
# in reverse.

cd integration
pdk cachepush http://localhost:$SERVER_PORT/telco/upload
ls cache/ | grep -v .header$ >$tmp_dir/expected

cd $tmp_dir
ls progeny-production/http/cache >actual
diff -u expected actual

# -----------------------------------------------------------
# Initial customer checkout.
# -----------------------------------------------------------

pdk init http://localhost:$SERVER_PORT/telco/ \
    customer-work-area progeny.com local master

cd customer-work-area

echo >>progeny.com/apache.xml
echo GARBAGE >>progeny.com/apache.xml


git-update-cache progeny.com/*
parent_id=$(cat .git/HEAD)
echo -n | git-commit-tree $(git-write-tree) -p $parent_id >.git/HEAD

# -----------------------------------------------------------
# Send change from customer to integration.
# -----------------------------------------------------------

git-diff-tree -p -r $parent_id $(cat .git/HEAD) >patch.txt

# really this file would be sent by email.
cp patch.txt $tmp_dir/integration/work/patch.txt

cd $tmp_dir
cd integration/work
git-apply patch.txt
git-update-cache progeny.com/apache.xml
pdk commit master "Required commit remark"
# -----------------------------------------------------------
# Pull from integration to production (again)
# -----------------------------------------------------------
cd $tmp_dir
do_production_pull \
    $tmp_dir/integration/work/.git \
    master \
    $tmp_dir/progeny-production/http/git \
    master

# -----------------------------------------------------------
# Pull from production to customer (again)
# -----------------------------------------------------------

cd $tmp_dir
cd customer-work-area
pdk update progeny.com master
grep GARBAGE progeny.com/apache.xml
