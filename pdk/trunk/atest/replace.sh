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

# replace.sh
# $Progeny$
#
# pdk replace cleans out a component and replacess all of it's existing
# packages with the given packages.

. atest/test_lib.sh

assert_quiet() {
    set +x
    local status=""
    "$@" >output-log 2>&1 || { status=$?; true; }
    if [ -s output-log -o -s error-log ]; then
        cat output-log
        bail "output and error log should be empty. (exit '$status')"
    fi
    set -x
    return $status
}

assert_quiet \
    pdk add progeny.com/ethereal.xml \
    packages/ethereal_0.9.13-1.0progeny1.dsc \
    packages/ethereal_0.9.13-1.0progeny1_ia64.deb \
    packages/ethereal-common_0.9.13-1.0progeny1_ia64.deb \
    packages/ethereal-dev_0.9.13-1.0progeny1_ia64.deb \
    packages/tethereal_0.9.13-1.0progeny1_ia64.deb

assert_quiet \
    pdk add -r progeny.com/ethereal.xml \
    packages/ethereal_0.9.13-1.0progeny2.dsc \
    packages/ethereal_0.9.13-1.0progeny2_ia64.deb \
    packages/ethereal-common_0.9.13-1.0progeny2_ia64.deb \
    packages/ethereal-dev_0.9.13-1.0progeny2_ia64.deb \
    packages/tethereal_0.9.13-1.0progeny2_ia64.deb


diff -u - progeny.com/ethereal.xml <<EOF || bail 'apache.xml differs'
<?xml version="1.0" encoding="utf-8"?>
<component>
  <contents>
    <dsc ref="sha-1:726bd9340f8b72a2fbf7e4b70265b56b125e525d">
      <name>ethereal</name>
      <version>0.9.13-1.0progeny2</version>
    </dsc>
    <deb ref="sha-1:9a264269606ea451c762eeb91f3f0e68db447887">
      <name>ethereal</name>
      <version>0.9.13-1.0progeny2</version>
      <arch>ia64</arch>
    </deb>
    <deb ref="sha-1:9ca2ad70d846b739ee43532f6727ee2b341d23b9">
      <name>ethereal-common</name>
      <version>0.9.13-1.0progeny2</version>
      <arch>ia64</arch>
    </deb>
    <deb ref="sha-1:9fca9287fa2d59fe7e723ec81892194e621999ab">
      <name>ethereal-dev</name>
      <version>0.9.13-1.0progeny2</version>
      <arch>ia64</arch>
    </deb>
    <deb ref="sha-1:67920db12b0097c88619f80d9de2ce07fd7d1558">
      <name>tethereal</name>
      <version>0.9.13-1.0progeny2</version>
      <arch>ia64</arch>
    </deb>
  </contents>
</component>
EOF

[ -d $cache_dir ] || {
    echo "here it comes................"
    bash
    echo ".................That was it?"
    bail "missing cache directory"
}

check_hash() {
    local expected_hash="$1"
    local message="$2"

    cache_filename=$(cachepath "sha-1:$expected_hash")
    [ -e $cache_filename ] || bail "missing cache file -- $message"

    [ $expected_hash = "$(openssl sha1 <$cache_filename)" ] \
        || bail "incorrect hash: $cache_filename -- $message"
}

check_hash "9683e93170a1c7459147d86605e72346b212c791" "ethereal,0.9.13-1.0progeny1"
check_hash "9a264269606ea451c762eeb91f3f0e68db447887" "ethereal,0.9.13-1.0progeny2"
check_hash "be25deecace20fc2a0dfc46af08e366e8b1e4ad9" "ethereal-common,0.9.13-1.0progeny1"
check_hash "9ca2ad70d846b739ee43532f6727ee2b341d23b9" "ethereal-common,0.9.13-1.0progeny2"
check_hash "3e331cba9cd69417e174dbf2c7313845794f9cdb" "ethereal-dev,0.9.13-1.0progeny1"
check_hash "9fca9287fa2d59fe7e723ec81892194e621999ab" "ethereal-dev,0.9.13-1.0progeny2"
check_hash "0de6b9634732b7c44e5bae0afb6667425c1d271c" "tethereal,0.9.13-1.0progeny1"
check_hash "67920db12b0097c88619f80d9de2ce07fd7d1558" "tethereal,0.9.13-1.0progeny2"
check_hash "5d6449397b815b214b7f40c4ba138368be7069c9" "ethereal,0.9.13-1.0progeny1"
check_hash "726bd9340f8b72a2fbf7e4b70265b56b125e525d" "ethereal,0.9.13-1.0progeny2"
