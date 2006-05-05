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

format=deb
export=1

args=$(getopt -o rdE -- "$@")
eval set -- "$args"
while true; do
    case "$1" in
        -r) shift; format=rpm;;
        -d) shift; format=deb;;
        -E) shift; unset export;;
        --) shift; break;;
    esac
done

clean() {
    if [ -n "$tmp_dir" ]; then
        rm -r $tmp_dir
    fi
    if [ -n "$export_dir" -a -d "$export_dir" ]; then
        rm -r $export_dir
    fi
}

trap clean 0 1 2 3 15

dev_dir=$(pwd)

if [ "$format" = deb ]; then
    expr='s/.*(\([^-]*\)\(-.*\)\?).*/\1/'
    version=$(sed -e "$expr" -e '1 q' <debian/changelog)
elif [ "$format" = rpm ]; then
    version=$(rpm -q --qf "%{version}" --specfile pdk.spec)
fi

export_dir=$(pwd)/pdk-$version
if [ -n "$export" ]; then
    svn export . $export_dir
else
    mkdir $export_dir
    tar --exclude=.svn --exclude=.git --exclude=ide \
        --exclude=atest/packages --exclude=tags --exclude=pdk-$version \
        --exclude=pdk_* --exclude=pdk-* \
        -cv -O . | tar xC pdk-$version
fi

if [ "$format" = deb ]; then
    cd $export_dir
    sh clean.sh
    debuild -us -uc -I.svn
    debc
    sudo debi
elif [ "$format" = rpm ]; then
    cd $dev_dir
    sh clean.sh
    tar zcvf $dev_dir/pdk_$version.tar.gz pdk-$version

    rpm_val() {
        rpm -q --specfile $export_dir/pdk.spec --qf "$(rpm -E %{$1})"
    }

    rpm_source_dir="$(rpm_val _sourcedir)"
    rpms_dir="$(rpm_val _rpmdir)"
    srpms_dir="$(rpm_val _srcrpmdir)"
    rpm_tmp_dir="$(rpm_val _tmppath)"
    rpm_build_dir="$(rpm_val _builddir)"
    mkdir -p $rpm_source_dir $rpms_dir $srpms_dir $rpm_tmp_dir \
        $rpm_build_dir
    cp $dev_dir/pdk_$version.tar.gz $rpm_source_dir
    rpmbuild -ba $export_dir/pdk.spec
    rm -r $export_dir
    mv $rpms_dir/* $srpms_dir/* $dev_dir
    sudo rpm -e pdk || true
    sudo rpm -Uvh pdk-$version-1.i386.rpm
fi

tmp_dir=$(mktemp -dt release.XXXXXX)

cd $tmp_dir
if [ "$format" = deb ]; then
    tar zxvf /usr/share/doc/pdk/atest.tar.gz
elif [ "$format" = rpm ]; then
    tar xvf /usr/share/doc/pdk-$version/atest.tar
fi
ln -s $dev_dir/atest/packages atest/
python utest.py
sh run_atest -I
cd -

