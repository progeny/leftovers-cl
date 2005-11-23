# picax.order - set the proper order to pack packages
# 
# Copyright 2005 Progeny Linux Systems.
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

import os

import picax.package
import picax.apt
import picax.config
import picax.log

def _order_udebs(packages, current_order):
    """Put udebs first in the order, since they have to be present
    to be usable by the debian-installer architecture."""

    new_order = current_order[:]
    for pkg in packages:
        if isinstance(pkg, picax.package.UBinaryPackage):
            if pkg in new_order:
                new_order.remove(pkg)
            new_order.insert(0, pkg["Package"])

    return new_order

def _order_explicit(packages, current_order):
    """If an order list is given in the configuration, add those
    packages to the order."""

    conf = picax.config.get_config()
    if conf.has_key("order_pkgs"):
        new_order = current_order[:]
        new_order.extend(conf["order_pkgs"])
        return new_order
    else:
        return current_order

def _order_debootstrap(packages, current_order):
    """Add the packages needed by debootstrap unless otherwise asked
    not to."""

    conf = picax.config.get_config()
    if not conf["no_debootstrap"]:
        new_order = current_order[:]
        bootstrap_dist = conf["repository_list"][0][0]
        pkg_names = []
        try:
            debootstrap_pipe = os.popen(
                "/usr/sbin/debootstrap --print-debs %s"
                % (bootstrap_dist,))
            for line in debootstrap_pipe:
                pkg_names.extend(line.strip().split())
            debootstrap_pipe.close()
        except:
            pass

        if len(pkg_names) == 0:
            picax.log.get_logger().warning(
                "Debootstrap could not report packages")
        else:
            new_order.extend(pkg_names)

        return new_order

    else:
        return current_order

def _order_installer(packages, current_order):
    """Add packages requested by the installer to the order."""

    conf = picax.config.get_config()
    if conf.has_key("installer_component"):
        new_order = current_order[:]
        new_order.extend(picax.installer.get_package_requests())
        return new_order
    else:
        return current_order

def _order_rest(packages, current_order):
    """Add the rest of the packages to the order unless otherwise
    asked not to."""

    conf = picax.config.get_config()
    if not conf["short_package_list"]:
        new_order = current_order[:]
        for pkg in packages:
            if pkg["Package"] not in new_order:
                new_order.append(pkg["Package"])
        return new_order
    else:
        return current_order

def _order_apt(packages, current_order):
    """Call apt to resolve the package order, so that a package's
    dependencies show up earlier in the order than the package."""

    base_media_pkgs = picax.package.get_base_media_packages()
    base_media_list = map(lambda x: (x["Package"], x["Version"]),
                          base_media_pkgs)
    new_order = picax.apt.resolve_package_list(current_order,
                                               base_media_list)
    return new_order

default_order_funcs = [ _order_udebs, _order_explicit, _order_debootstrap,
                        _order_installer, _order_rest, _order_apt ]

def order(packages):
    """Apply order functions and return the resulting order."""

    pkg_order = []
    for order_func in default_order_funcs:
        pkg_order = order_func(packages, pkg_order)
    return pkg_order
