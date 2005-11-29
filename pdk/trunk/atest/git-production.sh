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

. atest/utils/repogen-fixture.sh

set_up_repogen_fixture integration

SERVER_PORT=$(unused_port 8110 8111 8112 8113 8114 8115 8116 8117 13847)

create_apache_conf $SERVER_PORT

pdk_bin=$(which pdk)
cat >etc/svn.apache2.conf <<EOF
ScriptAlias /telco/upload $pdk_bin
Alias /telco/ $tmp_dir/production/
PassEnv PATH PYTHONPATH
# Tell the cgi where its cache is.
SetEnv PDK_CACHE_PATH $tmp_dir/production/etc/cache
EOF

$apache2_bin -t -f etc/apache2/apache2.conf
$apache2_bin -X -f etc/apache2/apache2.conf &

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
    <path>$tmp_dir/production</path>
  </production>
  <oops>
    <type>source</type>
    <path>$tmp_dir/ooooooops</path>
  </oops>
</channels>
EOF
    pdk add progeny.com/apache.xml
    pdk commit -m "git-production commit"

    pdk repogen progeny.com/apache.xml

# -----------------------------------------------------------
# Populate production environment with initial production data
# -----------------------------------------------------------

    pdk push production

    # make sure that we can't push to repositories that don't exist.
    pdk push oops && fail 'push to non-workspace should fail'
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
    <path>$tmp_dir/production</path>
  </progeny.com>
</channels>
EOF
    pdk pull progeny.com
    pdk download progeny.com/apache.xml
    for file in $(find etc/cache -type f | grep -v .header$); do
        compare_timestamps $file ../integration/$file
        compare_timestamps $file ../production/$file
    done
    pdk repogen progeny.com/apache.xml

# -----------------------------------------------------------
# Customer makes a local change.
# -----------------------------------------------------------

    echo GARBAGE >>progeny.com/apache.xml

    pdk commit -m "git-production testing"

    # Send change from customer to integration.
    git-diff-tree -p HEAD^ HEAD >patch.txt

    # really this file would be sent by email.
    cp patch.txt $tmp_dir/integration/patch.txt

popd

# -----------------------------------------------------------
# Apply change from customer to integration
# -----------------------------------------------------------

pushd integration
    # No direct pdk support for this. This case is an outlier.
    git-apply patch.txt
    pdk commit -m "Required commit remark"

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
