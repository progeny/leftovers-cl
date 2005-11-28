# picax.modload - code for loading modules
# 
# Copyright 2003, 2004, 2005 Progeny Linux Systems.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

import sys

def load_module(name, module_dir = None):
    if module_dir:
        sys.path.append(module_dir)

    inst_toplevel = None
    for parent_module in ("picax_modules", "picax.modules"):
        try:
            full_name = parent_module + "." + name
            inst_toplevel = __import__(full_name)
            break
        except:
            pass

    return inst_toplevel
