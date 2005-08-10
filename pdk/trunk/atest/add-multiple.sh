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
# test having git and pdk package add multiple files at once

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

pdk workspace create integration
cd integration/work

#This needs to be resolved with the creation of
#a component with an abstract package,
#followed by "pdk resolve (descr.)
pdk package add progeny.com/apache.xml \
    $tmp_dir/packages/apache2_2.0.53-5.dsc \
    $tmp_dir/packages/apache2-common_2.0.53-5_i386.deb

pdk package add progeny.com/ethereal.xml \
    $tmp_dir/packages/ethereal_0.9.13-1.0progeny2.dsc \
    $tmp_dir/packages/ethereal_0.9.13-1.0progeny2_ia64.deb \
    $tmp_dir/packages/ethereal-common_0.9.13-1.0progeny2_ia64.deb \
    $tmp_dir/packages/ethereal-dev_0.9.13-1.0progeny2_ia64.deb \
    $tmp_dir/packages/tethereal_0.9.13-1.0progeny2_ia64.deb


pdk add progeny.com/apache.xml progeny.com/ethereal.xml
pdk commit master "this is a remark"

