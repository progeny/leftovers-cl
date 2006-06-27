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
set -x

export=1

args=$(getopt -o E -- "$@")
eval set -- "$args"
while true; do
    case "$1" in
        -E) shift; unset export;;
        --) shift; break;;
    esac
done

version="$1"
if [ -z "$version" ]; then
    echo >&2 "Version required"
    exit 1
fi

clean() {
    if [ -n "$export_dir" -a -d "$export_dir" ]; then
        rm -r $export_dir
    fi
}

trap clean 0 1 2 3 15

export_dir=$(pwd)/pdk-$version
if [ -n "$export" ]; then
    svn export . $export_dir
else
    sh clean.sh
    mkdir $export_dir
    tar --exclude=.svn --exclude=.git --exclude=ide \
        --exclude=atest/packages --exclude=tags --exclude=pdk-$version \
        --exclude=./pdk_* --exclude=pdk-* \
        -cv -O . | tar xC pdk-$version
fi

tar zcvf pdk_$version.tar.gz pdk-$version
