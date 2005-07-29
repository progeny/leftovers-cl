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

# compile-error.sh 
# $Progeny$
#
# Make sure that an error is raised if the user tries to put a package
# directly in a component marked with split-apt-components.

# get Utility functions
. atest/test_lib.sh

# Create a component descriptor
# XXX: This is done often enough in testing, it it worth a script or shell
# function? 
cat >product.xml <<"EOF"
<?xml version="1.0"?>
<component>
  <meta>
    <origin>community</origin>
    <label>distro</label>
    <version>1.0</version>
    <codename>zip</codename>
    <suite>stable</suite>
    <date>Tue, 22 Mar 2005 21:20:00 +0000</date>
    <description>Hello World!</description>
    <split-apt-components>yes</split-apt-components>
  </meta>
  <component>main.xml</component>
  <component>contrib.xml</component>
</component>
EOF

cat >contrib.xml <<"EOF"
<?xml version="1.0"?>
<component>
  <component>progeny.com/ida.xml</component>
</component>
EOF

cat >main.xml <<"EOF"
<?xml version="1.0"?>
<component>
  <component>progeny.com/apache.xml</component>
</component>
EOF

# Install all the packages into the local cache
pdk add progeny.com/apache.xml \
    packages/apache2-common_2.0.53-5_i386.deb \
    packages/apache2_2.0.53-5.dsc \

pdk add progeny.com/ida.xml \
    packages/ida_2.01-1.2_arm.deb \
    packages/ida_2.01-1.2.dsc

# This is what will trigger the error.
pdk add product.xml \
    packages/ida_2.01-1.2_arm.deb

pdk repogen product.xml && fail 'repogen should have failed'
