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

# pdk-framework.sh
#
# Check the general soundness of the pdk command framework

#None of these help calls should result in a crash
#(meaningful help is another question altogether)
pdk help
echo "help" |pdk
pdk help clone
echo "help clone" |pdk
pdk help clone foo
echo "help clone foo" |pdk
pdk help workspace
echo "help workspace" |pdk
pdk help workspace foo
echo "help workspace foo" |pdk
pdk help workspace foo fighters
echo "help workspace foo fighters" |pdk
pdk help workspace create
echo "help workspace create" |pdk
pdk help workspace create foo
echo "help workspace create foo" |pdk

#   setup:
#   execute:
pdk workspace create
#   evaluation:
#   cleanup:

#   setup:
#   execute:
pdk workspace create foo
#   evaluation:
ls foo/work

#   cleanup:
rm -rf foo

#   setup:
#   execute:
echo "workspace create" |pdk
#   evaluation:
#   cleanup:

#   setup:
#   execute:
echo "workspace create foo" |pdk
#   evaluation:
ls foo/work
#   cleanup:
rm -rf foo

