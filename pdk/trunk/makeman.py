import sys
import optparse
from pdk.pdk_commands import commands

print r'''.\"Automatically generated
.\"Copyright \(co 2005 Progeny Linux Systems, Inc.
.
.\"PDK is free software; you can redistribute it and/or modify it
.\"under the terms of the GNU General Public License as published by
.\"the Free Software Foundation; either version 2 of the License, or
.\"(at your option) any later version.
.
.\"PDK is distributed in the hope that it will be useful, but WITHOUT
.\"ANY WARRANTY; without even the implied warranty of MERCHANTABILITY
.\"or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public
.\"License for more details.
.\"You should have received a copy of the GNU General Public License
.\"along with PDK; if not, write to the Free Software Foundation,
.\"Inc., 51 Franklin St, Fifth Floor, Boston, MA 02110-1301 USA
.
.de URL
\\$2 \(laURL: \\$1 \(ra\\$3
..
.if \n[.g] .mso www.tmac
.TH pdk "1" "2006" "pdk"
.SH "NAME"
pdk \- Componentized Linux Platform Development Kit (PDK)
.SH "SYNOPSIS"
.PP
.B "pdk"
.I "subcommand"
[
.I "subcommand" ...
] [
.I options
]
.I arguments
.SH "DESCRIPTION"
.PP
Simply put,
Componentized Linux is a platform
for building specialized Linux distributions.
Componentized Linux provides developers
with a set of reusable building blocks,
called components,
which can be easily assembled into a wide variety
of configurations and customized as necessary.
It combines this componentized platform
with a set of technologies
(covering installation, software management,
and hardware detection, with more on the way)
that span traditional distribution boundaries
and transform the assembled components
into a complete distribution.
.PP
This package contains
the Componentized Linux Platform Development Kit (PDK).
Essentially, you can think of the PDK as \(lqversion control
for distributions\(rq\(emit's intended to be
a full suite of tools
for building and maintaining a CL-based distribution,
from assembling a full distro
from a set of pre-built components
to managing the evolution of the distro over time
to incorporate upstream changes
to building your own custom components
to specifying global configuration like branding
to integrating distro-specific patches
and managing the changes over time.
.PP
.SH "COMMAND LIST"'''
def iter_help_lines(help_string):
    help_lines = iter(help_string.splitlines())
    for help_line in help_lines:
        yield help_line.strip()
        if help_line.strip() == 'options:':
            break
    for help_line in help_lines:
        yield help_line.rstrip()

for command_segments, command in commands:
    print '.SS'
    print '.B'
    print ' '.join(command_segments)
    spec = command.get_spec()
    spec.set_command_name(command_segments)
    print spec.format_help()

print r'''.SH "EXAMPLES"
Here is how you set up a new pdk workspace and pull a purchased product
from Progeny.
.RS
.PP
.BI "pdk workspace create " directory
.br
.BI "cd " directory
.PP
.B cat >etc/channels.xml <<EOF
.br
.B <channels>
.br
.I See documenation included with your
.I Componentized Linux product
.I for contents of \\fBetc/channels.xml\\fP.
.br
.B </channels>
.br
.B EOF
.PP
.BI "pdk pull " "Componenized Linux product"
.RE
.SH "AUTHOR"
Written by the friendly neighborhood engineers at Progeny.
.PP
.URL "http://www.progeny.com/" "Progeny"
.SH "REPORTING BUGS"
Report bugs to cl-workers@lists.progeny.com.
.PP
.ad l
See the
.URL "http://lists.progeny.com/listinfo/cl-workers" "CL Workers Mailing List"
for more information.
.ad b'''
