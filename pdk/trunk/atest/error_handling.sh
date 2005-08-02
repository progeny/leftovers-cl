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

# error_handling.sh
# $Progeny$
#
. atest/test_lib.sh

#-----------------------------------------------------------------------
# Ill-formed command line
pdk semdiff  || status=$?
test "$status" = "2" || { 
    bail "Expected command-line error(2), got ${status}"
}


#-----------------------------------------------------------------------
# Process ill-formed channels file
cat > channels.xml << EOF
<?xml version="1.0"?>
<channels>
  <blow-up-here>
</channels>
EOF
pdk updatechannels || status=$?
test "$status" = "3" || bail "Incorrect/unexpected error return"


#-----------------------------------------------------------------------
# Process even worse ill-formed (non)XML
cat > channels.xml << EOF
not ex emm ell at all
EOF
pdk updatechannels || status=$?
test "$status" = "3" || bail "Incorrect/unexpected error return"

#-----------------------------------------------------------------------
# Process an ill-formed component descriptor

cat > bad_component.xml << EOF
<?xml version="1.0"?>
EOF
pdk semdiff ./bad_component.xml  || status=$?
test "$status" = "3" || bail "Expected InputError(3) got ${status}"


#-----------------------------------------------------------------------
# Process a more reasonable ill-formed component descriptor
# Unclosed tag

cat > ethereal.xml << EOF
<?xml version="1.0" encoding="utf-8"?>
<component>
  <contents>
    <dsc ref="sha-1:726bd9340f8b72a2fbf7e4b70265b56b125e525d">
      <name>ethereal</name>
      <version>0.9.13-1.0progeny2</version>
    </dsc>
  
</component>
EOF
pdk semdiff ethereal.xml  || status=$?
test "$status" = "3" || bail "Expected InputError(3) got ${status}"



