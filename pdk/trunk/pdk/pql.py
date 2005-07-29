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

"""
pql

Perform pql operation
Part of the PDK suite
"""
__revision__ = '$Progeny$'


import sys
import optparse
import apsw
from pdk.cache import Cache
from pdk.component import ComponentDescriptor
from pdk.log import get_file_logger

make_tables_sql = ['''
create table packages (
    blob_id primary key,
    type,
    format,
    role,
    name,
    epoch,
    version,
    release,
    arch
)
''', '''
create table components (
    pkg_blob_id,
    blob_id,
    primary key (pkg_blob_id, blob_id)
)
''']

insert_package_sql = '''
insert into packages values (:blob_id, :type, :format, :role,
    :name, :epoch, :version, :release, :arch)
'''

insert_component_sql = '''
insert into components values (:pkg_blob_id, :blob_id)
'''

logger = get_file_logger()


def add_my_options(parser):
    """
    Set up the parser options for the pql command.
    """
    parser.add_option( 
                         "-i"
                         , "--import"
                         , action="store"
                         , dest="components"
                         , type="string"
                         , help="Input components, or `-` for stdin"
                     )


def import_component(cache, connection, component_name):
    """Import given components into an sqlite3 database for querying."""
    cursor = connection.cursor()
    cursor.execute('begin')

    for statement in make_tables_sql:
        cursor.execute(statement)

    added_pkgs = []
    added_assoc = []
    # in the future, expand to allow multiple components.
    component_names = [ component_name ]
    for component_name in component_names:
        top_component = ComponentDescriptor(component_name).load(cache)
        all_components = [top_component] + top_component.components
        for component in all_components:
            for package in component.direct_packages:
                bindings = package.get_bindings_dict()
                if bindings["blob_id"] in added_pkgs:
                    logger.warn("package %s added multiple times"
                                % (bindings["name"],))
                else:
                    cursor.execute(insert_package_sql, bindings)
                    added_pkgs.append(bindings["blob_id"])
                assoc = "%s:%s" % (bindings["blob_id"], component.ref)
                if assoc in added_assoc:
                    logger.warn("%s:%s association added multiple times"
                                % (bindings["name"], component.ref))
                else:
                    cursor.execute(insert_component_sql,
                                   { "pkg_blob_id": bindings["blob_id"],
                                     "blob_id": component.ref })
                    added_assoc.append(assoc)

    cursor.execute('commit')

def str_row(row):
    """Return a tuple of strings representing the contents of a row."""
    normalized_row = []
    for value in row:
        if not value:
            new_value = ''
        else:
            new_value = str(value)
        normalized_row.append(new_value)
    return tuple(normalized_row)

def run_query(dummy, connection):
    """Grab an sqlite3 query from stdin and run it."""
    sql = sys.stdin.read()
    logger.debug("sql is " + str(sql) )
    cursor = connection.cursor()
    for row in cursor.execute(sql):
        print '|'.join(str_row(row))

def pql(argv):
    """Do something, perhaps of use"""

    my_parser = optparse.OptionParser()
    add_my_options(my_parser)
    opts = my_parser.parse_args(args=argv)[0]

    cache = Cache()
    connection = apsw.Connection('comps.sql3')

    if opts.components:
        import_component(
            cache
            , connection
            , opts.components
        )
    else:
        run_query(cache, connection)

# vim:ai:et:sts=4:sw=4:tw=0:
