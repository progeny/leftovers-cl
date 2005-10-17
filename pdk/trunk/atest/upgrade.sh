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

# The upgrade command should upgrade concrete references. It should
# leave abstract references alone.

pdk workspace create multi-version
pushd multi-version
    mkdir channel1
    cp \
        $PACKAGES/ethereal-dev_0.9.4-1woody5_i386.deb \
        $PACKAGES/ethereal-dev_0.9.4-1woody5_ia64.deb \
        $PACKAGES/ethereal-common_0.9.4-1woody5_i386.deb \
        $PACKAGES/ethereal-common_0.9.4-1woody5_ia64.deb \
        $PACKAGES/ethereal_0.9.4-1woody5.dsc \
        $PACKAGES/ethereal_0.9.4-1woody5.diff.gz \
        $PACKAGES/ethereal_0.9.4-1woody5_i386.deb \
        $PACKAGES/ethereal_0.9.4-1woody5_ia64.deb \
        $PACKAGES/ethereal_0.9.4.orig.tar.gz \
        $PACKAGES/tethereal_0.9.4-1woody5_i386.deb \
        $PACKAGES/tethereal_0.9.4-1woody5_ia64.deb \
        channel1

    mkdir channel2
    cp \
        $PACKAGES/ethereal-dev_0.9.4-1woody6_i386.deb \
        $PACKAGES/ethereal-dev_0.9.4-1woody6_ia64.deb \
        $PACKAGES/ethereal-common_0.9.4-1woody6_i386.deb \
        $PACKAGES/ethereal-common_0.9.4-1woody6_ia64.deb \
        $PACKAGES/ethereal_0.9.4-1woody6.diff.gz \
        $PACKAGES/ethereal_0.9.4-1woody6.dsc \
        $PACKAGES/ethereal_0.9.4-1woody6_i386.deb \
        $PACKAGES/ethereal_0.9.4-1woody6_ia64.deb \
        $PACKAGES/ethereal_0.9.4.orig.tar.gz \
        $PACKAGES/tethereal_0.9.4-1woody6_i386.deb \
        $PACKAGES/tethereal_0.9.4-1woody6_ia64.deb \
        $PACKAGES/abook_0.5.3-2.diff.gz \
        $PACKAGES/abook_0.5.3-2.dsc \
        $PACKAGES/abook_0.5.3-2_s390.deb \
        $PACKAGES/abook_0.5.3.orig.tar.gz \
        channel2

    cat >etc/channels.xml <<EOF
<?xml version="1.0"?>
<channels>
  <channel1>
    <type>dir</type>
    <path>channel1</path>
  </channel1>
  <channel2>
    <type>dir</type>
    <path>channel2</path>
  </channel2>
</channels>
EOF

    pdk channel update

    cat >ethereal.xml <<EOF
<?xml version="1.0"?>
<component>
  <contents>
    <dsc>abook</dsc>
    <dsc>ethereal</dsc>
  </contents>
</component>
EOF

    pdk resolve ethereal.xml channel1

    diff -u - ethereal.xml <<EOF
<?xml version="1.0" encoding="utf-8"?>
<component>
  <contents>
    <dsc>
      <name>abook</name>
    </dsc>
    <dsc>
      <name>ethereal</name>
      <deb ref="md5:5c1107c1016a8025e5b1d56eeccf84df">
        <name>ethereal</name>
        <version>0.9.4-1woody5</version>
        <arch>i386</arch>
      </deb>
      <deb ref="md5:c68b86189746723e62bf08368bce227b">
        <name>ethereal</name>
        <version>0.9.4-1woody5</version>
        <arch>ia64</arch>
      </deb>
      <deb ref="md5:9c979f57424b5d55c5de6621098e96d2">
        <name>ethereal-common</name>
        <version>0.9.4-1woody5</version>
        <arch>i386</arch>
      </deb>
      <deb ref="md5:9247b82b07d2eb11446fdce5f88983dc">
        <name>ethereal-common</name>
        <version>0.9.4-1woody5</version>
        <arch>ia64</arch>
      </deb>
      <deb ref="md5:c49c94d9dc7312668c9b48a550df6a1c">
        <name>ethereal-dev</name>
        <version>0.9.4-1woody5</version>
        <arch>i386</arch>
      </deb>
      <deb ref="md5:c030461e088a87758a4ba9935f0733e1">
        <name>ethereal-dev</name>
        <version>0.9.4-1woody5</version>
        <arch>ia64</arch>
      </deb>
      <deb ref="md5:9aeb2ffbc5277b3196b83e6d38b53621">
        <name>tethereal</name>
        <version>0.9.4-1woody5</version>
        <arch>i386</arch>
      </deb>
      <deb ref="md5:ab7f2190f094c3b8e67d56ff49045b9a">
        <name>tethereal</name>
        <version>0.9.4-1woody5</version>
        <arch>ia64</arch>
      </deb>
      <dsc ref="md5:fb98a4629ed5c2a09188264978e235cb">
        <name>ethereal</name>
        <version>0.9.4-1woody5</version>
      </dsc>
    </dsc>
  </contents>
</component>
EOF

    pdk upgrade ethereal.xml channel2

    diff -u - ethereal.xml <<EOF
<?xml version="1.0" encoding="utf-8"?>
<component>
  <contents>
    <dsc>
      <name>abook</name>
    </dsc>
    <dsc>
      <name>ethereal</name>
      <deb ref="md5:b9efde468cca1ddd6b731a3b343bd51d">
        <name>ethereal</name>
        <version>0.9.4-1woody6</version>
        <arch>i386</arch>
      </deb>
      <deb ref="md5:e2aba915304534ac4fbb060a2552d9c6">
        <name>ethereal</name>
        <version>0.9.4-1woody6</version>
        <arch>ia64</arch>
      </deb>
      <deb ref="md5:c618774e3718d11d94347b0d66f72af4">
        <name>ethereal-common</name>
        <version>0.9.4-1woody6</version>
        <arch>i386</arch>
      </deb>
      <deb ref="md5:f06169aeefd918e4e5b809393edb8dc2">
        <name>ethereal-common</name>
        <version>0.9.4-1woody6</version>
        <arch>ia64</arch>
      </deb>
      <deb ref="md5:a7c01d2560880e783e899cd623a27e7a">
        <name>ethereal-dev</name>
        <version>0.9.4-1woody6</version>
        <arch>i386</arch>
      </deb>
      <deb ref="md5:e7f788d020319a8147beb4172cdc736f">
        <name>ethereal-dev</name>
        <version>0.9.4-1woody6</version>
        <arch>ia64</arch>
      </deb>
      <deb ref="md5:a7706f7f82b44a30d4a99b299c58b4ca">
        <name>tethereal</name>
        <version>0.9.4-1woody6</version>
        <arch>i386</arch>
      </deb>
      <deb ref="md5:6c8ef685b4e61f34a0146eb6fc666fdb">
        <name>tethereal</name>
        <version>0.9.4-1woody6</version>
        <arch>ia64</arch>
      </deb>
      <dsc ref="md5:6c3d2beab693578b827bc0c2ecc13eb2">
        <name>ethereal</name>
        <version>0.9.4-1woody6</version>
      </dsc>
    </dsc>
  </contents>
</component>
EOF
popd
