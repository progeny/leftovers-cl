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
compare.py
"""

# compare: compare a PDK project to one or more external apt repositories,
#          given in priority order.

# Copyright 2005 Progeny Linux Systems, Inc.  All rights reserved.

import sys
import tempfile
import gzip
import urllib2
import apt_pkg
from pdk import workspace
from pdk.component import ComponentDescriptor
import pdk.log

__revision__ = "$Progeny$"

logger = pdk.log.get_logger()

# Auth class for urllib2.

class NoRealmPasswordMgr(urllib2.HTTPPasswordMgr):
    """The urllib2 password manager requires that the realm and URI
    passed to the auth handler be just right, a very difficult task.
    So, this password manager acts as a stand-in, and effectively
    removes the realm and URI checks.  This means that the password
    manager can only store a single user/password pair, but this
    should be sufficient for our purposes.
    """
    def add_password(self, realm, uri, user, passwd):
        """Add authentication info to the manager.  The realm and
        uri parameters are required by the API, but are ignored.
        """
        urllib2.HTTPPasswordMgr.add_password(self, "norealm",
                                             "http://example.com/",
                                             user, passwd)

    def find_user_password(self, realm, authuri):
        """Get the username and password.  The realm and authuri
        parameters are required by the API, but are ignored for
        our purposes.
        """
        return \
urllib2.HTTPPasswordMgr.find_user_password(self, "norealm",
                                           "http://example.com/")

# Load data from an external apt repository.

class ExternalRepo(object):
    """This class handles loading external apt repositories, parsing
    the index files, and storing the appropriate data for later use.
    'Appropriate' means the header fields listed in _interesting_keys
    plus the 'Source' header field, which has to be parsed
    separately.
    """

    _interesting_keys = ("Package", "Version")

    def __init__(self, tag, base_uri, distro, component, arch = "i386"):
        self.tag = tag
        self.base_uri = base_uri
        if base_uri[-1] != "/":
            self.base_uri = self.base_uri + "/"
        self.distro = distro
        self.component = component
        self.arch = arch

        self.packages = {}
        self.loaded = False

    def has_package(self, package_name):
        """Does a package with the given name exist in the repo?
        """
        if not self.loaded:
            self.load()
        return self.packages.has_key(package_name)

    def has_newer_package(self, package_name, package_version):
        """Does a package with the given name and newer than the given
        version exist in the repo?
        """
        if not self.loaded:
            self.load()

        if self.has_package(package_name):
            if \
apt_pkg.VersionCompare(self.packages[package_name]["Version"],
                       package_version) > 0:
                return True

        return False

    def get_package(self, package_name):
        """Return the named package's information.
        """
        if not self.loaded:
            self.load()
        return self.packages[package_name]

    def load(self):
        """Actually do the work of downloading and parsing the package
        indexes.  This can be called explicitly, or will be called
        implicitly when necessary.
        """
        packages_uri = "%sdists/%s/%s/binary-%s/Packages" % \
                       (self.base_uri, self.distro, self.component,
                        self.arch)
        compressed = False

        try:
            dl = urllib2.urlopen(packages_uri)
        except urllib2.HTTPError:
            packages_uri = packages_uri + ".gz"
            dl = urllib2.urlopen(packages_uri)
            compressed = True

        tf = tempfile.TemporaryFile()
        tf.write(dl.read())
        dl.close()
        tf.seek(0)

        if compressed:
            tf2 = gzip.GzipFile(fileobj = tf)
        else:
            tf2 = tf

        t = apt_pkg.ParseTagFile(tf2)
        while t.Step():
            if self.packages.has_key(t.Section["Package"]):
                sys.stderr.write("W: multiple entries for %s found in %s\n"
                                 % (t.Section["Package"], self.tag))
                continue

            info = {}
            for key in self._interesting_keys:
                info[key] = t.Section[key]
            if t.Section.has_key("Source"):
                if t.Section["Source"].find("(") == -1:
                    info["Source"] = "%s (%s)" \
                                     % (t.Section["Source"],
                                        info["Version"])
                else:
                    info["Source"] = t.Section["Source"]
            else:
                info["Source"] = "%s (%s)" % (info["Package"],
                                              info["Version"])

            self.packages[info["Package"]] = info

        tf2.close()
        tf.close()

        self.loaded = True

def compare_to_debian_repo(product, repositories):
    """Take a product or component descriptor, and compare it to one
    or more apt repositories.  The product should be a product
    descriptor filename or component reference, and the repositories
    should be a list of strings that describe apt repositories.  Each
    string should contain 'base_uri,distro,component' where base_uri,
    distro, and component have the same meaning as in sources.list.
    """

    password_mgr = NoRealmPasswordMgr()
    password_mgr.add_password(None, None, "a", "a")
    urllib2.install_opener(\
        urllib2.build_opener(\
        urllib2.HTTPBasicAuthHandler(password_mgr)))

    apt_pkg.init()

    # Identify and load all the repositories we have to query.

    repo_list = []
    for repo_str in repositories:
        (base_uri, dist, comp) = repo_str.split(",")
        tag = dist + "-" + comp
        repo = ExternalRepo(tag, base_uri, dist, comp)
        logger.info("loading %s" % (tag,))
        repo.load()
        repo_list.append(repo)

    # Load the packages.

    pdk_package_list = {}
    cache = workspace.current_workspace().cache()

    descriptor = ComponentDescriptor(product)
    component = descriptor.load(cache)
    pdk_package_list[component] = component.packages

    # Go through the component list and compare packages.

    changes_list = []
    for component in pdk_package_list.keys():
        for pdk_pkg in pdk_package_list[component]:
            if pdk_pkg.type == "source":
                continue

            pdk_pkg_version = pdk_pkg.version.original_header

            for repo in repo_list:
                if repo.has_package(pdk_pkg.name):
                    repo_pkg = repo.get_package(pdk_pkg.name)
                    for real_comp in [component] + component.components:
                        if pdk_pkg in real_comp.direct_packages:
                            changes_list.append((real_comp.ref,
                                                 pdk_pkg.name,
                                                 repo.tag,
                                                 pdk_pkg_version,
                                                 repo_pkg["Version"]))
                    break

    # All done.

    return changes_list
