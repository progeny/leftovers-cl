#!/bin/sh
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

# This script builds, installs, and runs acceptance tests for a package
# build.

set -e

clean() {
    if [ -n "$tmp_dir" ]; then
        rm -r $tmp_dir
    fi
}

trap clean 0 1 2 3 15

sh clean.sh
debuild -us -uc -I.svn
debc
sudo debi

tmp_dir=$(mktemp -dt release.XXXXXX)
dev_dir=$(pwd)

cd $tmp_dir
tar zxvf /usr/share/doc/pdk/atest.tar.gz
ln -s $dev_dir/atest/packages atest/
python utest.py
sh run_atest -I
cd -
