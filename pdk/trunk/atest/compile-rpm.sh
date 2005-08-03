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

# compile-rpm.sh
# $Progeny$
#
# check that we can import and then do a basic compile using rpms.

# get Utility functions
. atest/test_lib.sh

# Install all the packages into the local cache
pdk package add progeny.com/time.xml \
    packages/adjtimex-1.13-13.i386.rpm \
    packages/adjtimex-1.13-13.src.rpm

pdk repogen progeny.com/time.xml

[ -d './repo' ] || fail "mising repo directory"

check_file "519da15c87652669b707ab49e2a6294d7aea1c1f" \
    "./repo/adjtimex-1.13-13.i386.rpm"
check_file "5f5e2555c8294e68d06bf61aad10daa05dca2516" \
    "./repo/adjtimex-1.13-13.src.rpm"
