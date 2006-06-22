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

# plug-in.sh
#
# Check the loading and use of plug-in commands

#########################################
# Ensure that plugins work at all
# (native to util.py)
#########################################
#   setup:
cat > localfile.py <<EOF
import pdk.util
from pdk.pdk_commands import commands

commands.map_direct(['moo'], pdk.util.moo)
EOF
cat > .pdk_plugins <<EOF
localfile
EOF

# command line
#   execute:
pdk moo > cowstuff.txt
#   evaluation:
grep -q batcow cowstuff.txt && cat cowstuff.txt
#   cleanup:
pdk help moo >cowhelp.txt
grep -q easter cowhelp.txt || fail "Plugin help broken."
rm .pdk_plugins cowstuff.txt cowhelp.txt

#########################################
# Ensure that plugins work with comments
# (native to util.py)
#########################################
#   setup:
cat > .pdk_plugins <<EOF
# Add batcow powers to pdk 
#
# Record is:
#    module to import
#    name of function to call (module.fn)
#    desired command name
#------------------------------------
localfile
# -----------------------------------
# I am the cow that moos in the night.
# I am batcow
#
EOF
# command line
#   execute:
pdk moo > cowstuff.txt
#   evaluation:
grep -q batcow cowstuff.txt && cat cowstuff.txt

# command line with args
#   execute:
pdk moo testing >cowstuff.txt
#   evaluation:
grep -q batcow cowstuff.txt && cat cowstuff.txt
grep -q testing cowstuff.txt && cat cowstuff.txt
#   cleanup:
rm .pdk_plugins cowstuff.txt

# vim:ai:et:sts=4:sw=4:tw=0:
