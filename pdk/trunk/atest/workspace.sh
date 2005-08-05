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

# workspace.sh
#
# Unit test the workspace commands

#setup
#execute
pdk workspace
#evaluate
#cleanup


#setup
#execute
pdk workspace create
#evaluate
#cleanup

#setup
#execute
pdk workspace create foo
#evaluate
ls -la foo|grep -q VC
ls -la foo|grep -q work
ls -la foo|grep -q cache
#cleanup
rm -rf foo


#   setup:
#   execute:
echo "workspace create" |pdk
#   evaluate:
#   cleanup:

#   setup:
#   execute:
echo "workspace create foo" |pdk
#   evaluate:
ls -la foo|grep -q VC
ls -la foo|grep -q work
ls -la foo|grep -q cache
#   cleanup:
rm -rf foo

