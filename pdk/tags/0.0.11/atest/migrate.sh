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

# migrate.sh
#
# test the workspace migration tool

# manually set up a workspace in schema 1 layout
mkdir -p schema1/work/.git
mkdir -p schema1/cache/md5
ln -s $tmp_dir/schema1/work/.git schema1/VC
touch schema1/work/somefile
touch schema1/channels.xml
GIT_DIR=schema1/work/.git git-init-db
mkdir schema1/work/.git/remotes
touch schema1/work/.git/remotes/some-source

pushd schema1/work
    pdk migrate && fail 'pdk migrate should fail when in a schema1 work dir'
    touch somefile
    pdk add somefile 2>errors || true
    cat errors
    grep -q 'pdk migrate' errors \
        || fail 'pdk commands should complain about migrating when in schema1.'
popd

pushd schema1
    pdk migrate
    # stuff that should be gone.
    [ -e work ] && fail 'work directory should no longer exist'
    [ -e VC ] && fail 'VC symlink should no longer exist'
    [ -e channels.xml ] && fail 'channels.xml should not be in base dir.'
    [ -e sources ] && fail 'sources should not be in base dir.'

    # stuff that should be present
    [ -d etc/cache/md5 ] || fail 'cache was not migrated properly'
    [ -e etc/channels.xml ] || fail 'channels.xml was not migrated.'
    [ -d etc/channels ] || fail 'channels dir not created.'
    [ -e somefile ] || fail 'work dir content should be in base dir.'
    [ -L etc/git  ] && fail 'etc/git should not be a symlink'
    [ -d etc/git/objects ] || fail 'etc/git should contain git info'
    [ -L .git ] || fail '.git should be a symlink'
    [ 'etc/git' = "$(readlink .git)" ] || '.git should point to etc/git'
    [ 4 = "$(cat etc/schema)" ] || fail 'schema number incorrect'
popd

mkdir -p schema2/etc
pushd schema2
    echo 2 >etc/schema
    touch etc/outside_world.cache
    pdk migrate
    [ -d etc/channels ] || fail 'channels dir not created.'
    [ -e etc/outside_world.cache ] \
        && fail 'outside_world.cache not removed.'
    [ 4 = "$(cat etc/schema)" ] || fail 'schema number incorrect'
popd

mkdir -p schema3/etc/git/remotes
pushd schema3
    echo 3 >etc/schema
    ln -s $(pwd)/etc/git/remotes etc/sources
    pdk migrate
    [ -e etc/sources ] && fail 'sources should be removed from etc/'
    [ 4 = "$(cat etc/schema)" ] || fail 'schema number incorrect'
popd