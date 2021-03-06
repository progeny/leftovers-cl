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

cat >bin/ssh <<EOF
#!/bin/sh
# A mock ssh.
# this script tested with rsync
host="\$1"
PS4='-- ssh \$host: '
shift
if [ -z "\$1" ]; then
    echo >&2 "No ssh command given. Login not available."
    exit 1
fi
if [ "\$host" != "localhost" ]; then
    echo >&2 "Only localhost allowed!"
    exit 1
fi
set -e
set -x
cd $tmp_dir
"\$@"
EOF
chmod +x bin/ssh

. atest/utils/repogen-fixture.sh

set_up_repogen_fixture integration

# -----------------------------------------------------------
# Bootstrap and do some "integration" work in the integration area.
# -----------------------------------------------------------

pdk workspace create production
pushd integration
    cat >etc/channels.xml <<EOF
<?xml version="1.0"?>
<channels>
  <production>
    <type>source</type>
    <path>file://localhost/$tmp_dir/production</path>
  </production>
</channels>
EOF
    pdk add progeny.com/apache.xml
    pdk commit "git-production commit"

    pdk repogen progeny.com/apache.xml

# -----------------------------------------------------------
# Populate production environment with initial production data
# -----------------------------------------------------------

    pdk push production
popd

diff -u integration/etc/git/refs/heads/master \
    production/etc/git/refs/heads/master
(cd integration; find etc/cache | grep -v .header ) >expected
(cd production; find etc/cache | grep -v .header ) >actual
diff -u expected actual || fail 'caches should match'

# -----------------------------------------------------------
# Initial customer product retrieval.
# -----------------------------------------------------------
pdk workspace create customer-work-area
pushd customer-work-area
    cat >etc/channels.xml <<EOF
<?xml version="1.0"?>
<channels>
  <progeny.com>
    <type>source</type>
    <path>file://localhost/$tmp_dir/production</path>
  </progeny.com>
</channels>
EOF
    pdk pull progeny.com
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

    pdk push production
popd

# -----------------------------------------------------------
# Pull from production to customer (again)
# -----------------------------------------------------------

pushd customer-work-area
    pdk pull progeny.com
    grep GARBAGE progeny.com/apache.xml
popd

# vim:ai:et:sts=4:sw=4:tw=0:
