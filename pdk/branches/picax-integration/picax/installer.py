#!/usr/bin/python

"""This module provides a public interface to an installer add-on module
requested in the configuration, as well as providing the mechanism for
loading that module."""

import os
import picax.config
import picax.media
import picax.modload

loaded_module_name = None
inst = None

class InstallerError(StandardError):
    "Exception to indicate problems with the installer."
    pass

def _check_inst():
    if inst is None:
        raise InstallerError, "no installer has been set"

def set_installer(name, module_dir = None):
    "Set the installer module."

    global loaded_module_name
    global inst

    if inst is not None:
        if name != loaded_module_name:
            raise InstallerError, \
                  "cannot load two different installer modules"
    else:
        try:
            inst = picax.modload.load_module(name, module_dir)
        except ImportError:
            raise InstallerError, "cannot find install modules for %s" \
                  % (name,)

        loaded_module_name = name

def get_options():
    "Retrieve the installer module's options."

    _check_inst()

    return inst.get_options()

def get_package_requests():
    "Retrieve the installer module's package requests."

    _check_inst()

    return inst.get_package_requests()

def install():
    "Write the installer to the first part."

    try:
        _check_inst()
    except InstallerError:
        return 0

    first_part_space = 0
    conf = picax.config.get_config()

    first_part_loc = "%s/bin1" % (conf["dest_path"],)
    os.makedirs(first_part_loc)

    inst.install(first_part_loc)

    for (root, dummy, files) in os.walk(first_part_loc):
        path_space = sum([os.path.getsize(os.path.join(root, name))
                          for name in files])
        first_part_space = first_part_space + path_space

    return first_part_space

def post_install():
    """Perform any actions needed after the packages are written to the
    parts."""

    try:
        _check_inst()
    except InstallerError:
        return

    conf = picax.config.get_config()
    cd_path = "%s/bin1" % (conf["dest_path"],)
    inst.post_install(cd_path)

def get_media_builder():
    """Retrieve the installer module's media builder object, or a generic
    one if the installer module doesn't define one."""

    try:
        _check_inst()
        return inst.get_media_builder()
    except:
        return picax.media.MediaBuilder()
