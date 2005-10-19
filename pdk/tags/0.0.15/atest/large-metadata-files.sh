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

# $Progeny$
#
# Test that pdk can operate on large metadata files in resonable time.
# This isn't asserted in any particular way, but a long run should annoy
# us into keeping the test reasonably fast.

pdk workspace create large-meta

pushd large-meta
    cat >etc/channels.xml <<EOF
<?xml version="1.0"?>
<channels>
   <sarge>
     <type>apt-deb</type>
     <path>file://$PACKAGES/large-metadata-files/</path>
     <archs>amd64 i386 ia64 source</archs>
     <dist>sarge</dist>
     <components>main</components>
   </sarge>
</channels>
EOF

    pdk channel update
    mkdir progeny.com
    cat >progeny.com/hello.xml <<EOF
<?xml version="1.0" encoding="utf-8"?>
<component>
   <id>hello</id>
   <name>Hello, world!</name>
   <description>
     The hello component produces a familiar, friendly greeting.
   </description>
   <contents>
     <deb>
       <name>hello</name>
       <deb ref="md5:7dee5a121dd08ac8e8c85cf87fa0bbf8">
         <name>hello</name>
         <version>2.1.1-4</version>
         <arch>amd64</arch>
       </deb>
       <deb ref="md5:b9967c4a0491e2567b0d16a8e0b42208">
         <name>hello</name>
         <version>2.1.1-4</version>
         <arch>i386</arch>
       </deb>
       <deb ref="md5:1a1b8df0cbf62d5571d8a0af1628077f">
         <name>hello</name>
         <version>2.1.1-4</version>
         <arch>ia64</arch>
       </deb>
       <dsc ref="md5:6d92a81b5e72c1f178c1285313a328df">
         <name>hello</name>
         <version>2.1.1-4</version>
       </dsc>
     </deb>
   </contents>
</component>
EOF
    pdk download progeny.com/hello.xml
popd