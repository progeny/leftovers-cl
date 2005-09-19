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

# Utility functions
#
# XXX - Move methods?
# Common enough to require movement up into the base test, or maybe
# to be dotted-in from a common file? It's nice to be able to refactor
# tests, not to mention have a single maintenance point.
# Imagine that!
#

pdk_init() {
    # TEMPORARY -- to be replaced with 'pdk init' when that is ready
    pdk init || {
        mkdir cache
        mkdir wip
    }
}

unused_port() {
    # Given: a list of ports
    # Result: the first unused port
    #
    # To use this, capture the output.
    ports=`netstat -l --numeric-ports | awk '
           { if ( split($4,parts,":") == 2) print parts[2]; }' |
           sort -u `
    while [ "$1" ]
    do
        if echo $ports | grep -q $1 
        then
            shift
            continue
        else
            echo $1
            break
        fi
    done
}



inode_of() {
    # Get the inode number for a given file
    stat --format='%i' $1
}

# This is the only place we should have to maintain the 
# algorithm for cache placement outside of PDK proper.
# Use only this method to find files in cache
cachepath() {
    cache_dir=${cache_base:-"etc/cache"}
    if [ $(echo $1 | grep :) ]; then
        method=$(echo $1 | cut -f1 -d:)
        raw_cksum=$(echo $1 | cut -f2 -d:)
        shortpath=$(echo $raw_cksum | cut -c1-2)
        echo ${cache_dir}/$method/$shortpath/$1
    else
        echo ${cache_dir}/$1
    fi
}

check_file() {
    # XXX - to what can we rename this function?
    local expected_hash="$1"
    local repo_filename="$2"
    [ -e $repo_filename ] || fail "missing package $repo_filename"

    local cache_filename=$(cachepath "sha-1:$expected_hash")

    # Check that the hashes match
    [ $expected_hash = "$(cat $cache_filename | openssl sha1)" ] \
        || fail "incorrect hash: ${cache_filename}, got ${expected_hash}"

    # Check that the file is hard linked
    [ "$(stat --format='%h' $repo_filename)" -gt 1 ] \
        || fail "package not hard linked $repo_filename"

    # Check that the file has the same inode in/out of cache
    [ "$(inode_of $repo_filename)" = "$(inode_of ${cache_filename})" ] \
        || fail "package not hard linked $repo_filename"
}

assert_exists() {
    local file="$1"
    [ -e $file ] || fail "Missing $file"
}

assert_not_exists() {
    local file="$1"
    [ -e $file ] && fail "Including $file" || true
}

bail() {
    msg="$*"
    if [ -n "${DEBUG}" ]; then
        echo $msg
        bash
    fi
    fail "$msg"
}

# Create a sandboxed apache configuration.
# Also sets the variable $apache2_bin.
create_apache_conf() {
    local server_port="$1"

    # caution: debian specific?
    # apache2_bin is NOT local on purpose.
    local apache2_modules_path=/usr/lib/apache2/modules/
    apache2_bin=/usr/sbin/apache2

    mkdir -p etc/apache2
    mkdir -p www

    cat >etc/apache2/apache2.conf <<EOF
AcceptMutex fcntl
ServerRoot "$(pwd)/etc/apache2"
LockFile accept.lock
PidFile $(pwd)/run/apache2.pid
Timeout 300
KeepAlive On
MaxKeepAliveRequests 100
KeepAliveTimeout 15
LogFormat "%h %l %u %t \"%r\" %>s %b \"%{Referer}i\" \"%{User-Agent}i\"" combined
#CustomLog "$(tty)" combined
ErrorLog "$(tty)"
LogLevel error

LoadModule cgi_module ${apache2_modules_path}mod_cgi.so
LoadModule dav_module ${apache2_modules_path}mod_dav.so
LoadModule dav_fs_module ${apache2_modules_path}mod_dav_fs.so
LoadModule dav_svn_module ${apache2_modules_path}mod_dav_svn.so
LoadModule authz_svn_module ${apache2_modules_path}mod_authz_svn.so

Listen ${server_port}

DirectoryIndex index.html index.xhtml
AccessFileName .htaccess
<Files ~ "^\.ht">
    Order allow,deny
    Deny from all
</Files>

TypesConfig /etc/mime.types
DefaultType text/plain

HostnameLookups Off

IndexIgnore .??* *~ *# HEADER* RCS CVS *,t

AddEncoding x-compress Z
AddEncoding x-gzip gz tgz

BrowserMatch "Mozilla/2" nokeepalive
BrowserMatch "MSIE 4\.0b2;" nokeepalive downgrade-1.0 force-response-1.0
BrowserMatch "RealPlayer 4\.0" force-response-1.0
BrowserMatch "Java/1\.0" force-response-1.0
BrowserMatch "JDK/1\.0" force-response-1.0

BrowserMatch "Microsoft Data Access Internet Publishing Provider" redirect-carefully
BrowserMatch "^WebDrive" redirect-carefully
BrowserMatch "^gnome-vfs" redirect-carefully 
BrowserMatch "^WebDAVFS/1.[012]" redirect-carefully

Include "$(pwd)/etc/*.apache2.conf"

EOF
}

# vim:ai:et:sts=4:sw=4:tw=0:
