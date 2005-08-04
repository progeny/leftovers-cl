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
cat > .pdk_plugins <<EOF
pdk.util moo do_moo
EOF
# pdk shell
#   execute:
echo moo | pdk > cowstuff.txt
#   evaluation:
grep -q batcow cowstuff.txt && cat cowstuff.txt

# command line
#   execute:
pdk moo > cowstuff.txt
#   evaluation:
grep -q batcow cowstuff.txt && cat cowstuff.txt
#   cleanup:
rm .pdk_plugins cowstuff.txt

#########################################
# Ensure that plugins work with comments
# (native to util.py)
#########################################
#   setup:
cat > .pdk_plugins <<EOF
#
# Add batcow powers to our fun pdk toy
pdk.util moo do_moo # This makes us moo
# I am the cow that moos in the night.
# I am batcow
EOF
# command line
#   execute:
pdk moo > cowstuff.txt
#   evaluation:
grep -q batcow cowstuff.txt && cat cowstuff.txt

# pdk shell
#   execute:
echo "moo" | pdk > cowstuff.txt
#   evaluation:
grep -q batcow cowstuff.txt && cat cowstuff.txt

# pdk shell with args
#   execute:
echo "moo testing" | pdk > cowstuff.txt
#   evaluation:
grep -q batcow cowstuff.txt && cat cowstuff.txt
grep -q testing cowstuff.txt && cat cowstuff.txt

# command line with args
#   execute:
pdk moo testing >cowstuff.txt
#   evaluation:
grep -q batcow cowstuff.txt && cat cowstuff.txt
grep -q testing cowstuff.txt && cat cowstuff.txt
#   cleanup:
rm .pdk_plugins cowstuff.txt


#########################################
# Ensure that plugins work with comments
# (created in a file on-the-fly)
#########################################
#   setup:
cat > localfile.py <<EOF
def moo(args):
    print "I can moo like batcow, too"
EOF
cat > .pdk_plugins <<EOF
#
# Add batcow powers to our fun pdk toy
localfile moo do_moo # This makes us moo
# I am the cow that moos in the night.
# I am batcow
EOF
#   execute:
echo "moo" | pdk >cowstuff.txt
#   evaluation:
#   cleanup:
rm .pdk_plugins localfile.py cowstuff.txt

