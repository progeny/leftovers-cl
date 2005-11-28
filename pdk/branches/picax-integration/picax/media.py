#!/usr/bin/python

import sys
import os
import picax.config
import picax.installer
import picax.modload

loaded_module_name = None
inst = None

class MediaError(StandardError):
    "Media exception class."
    pass

class MediaBuilder:
    """This class controls the order in which media are built.  Often,
    it's necessary to build the media out of order; for example, the
    first medium might need to be built last to include information
    about the other media on it.  By default, we just create the media
    in order."""

    def __init__(self):
        pass

    def create_media(self):
        "Create the media."

        index = 1
        while can_create_image(index):
            create_image(index)
            index = index + 1

def is_media():
    "Check if there is a media module loaded."

    return inst != None

def _check_inst():
    "Raise an exception if no media module has been loaded."

    if not is_media():
        raise MediaError, "no media type has been set"

def create_media():
    """Create a MediaBuilder object, and use it to drive the media creation
    process."""

    if not is_media():
        return

    conf = picax.config.get_config()

    if "installer_component" in conf:
        media_builder = picax.installer.get_media_builder()
    else:
        media_builder = MediaBuilder()

    media_builder.create_media()

def set_media(name, module_dir = None):
    "Load the requested media module."

    global loaded_module_name
    global inst

    if inst is not None:
        if name != loaded_module_name:
            raise MediaError, "cannot load two different media modules"
    else:
        inst_toplevel = picax.modload.load_module(name, module_dir)
        if not inst_toplevel:
            raise MediaError, "could not find media module for %s" \
                  % (name,)

        if hasattr(inst_toplevel, name):
            inst = getattr(inst_toplevel, name)
        elif hasattr(inst_toplevel, "modules") and \
             hasattr(inst_toplevel.modules, name):
            inst = getattr(inst_toplevel.modules, name)
        else:
            raise MediaError, "cannot find media modules for %s" \
                  % (name,)

        loaded_module_name = name

def get_options():
    "Retrieve the media module's options."

    _check_inst()

    return inst.get_options()

def get_part_size():
    "Retrieve the media size defined by the module."

    _check_inst()

    return inst.get_part_size()

def can_create_image(index):
    "Check if we're ready to start creating images."

    _check_inst()

    config = picax.config.get_config()
    path = "%s/bin%d" % (config["dest_path"], index)
    if not os.path.isdir(path):
        return False

    return True

def create_image(index, boot_image_path = None):
    "Create the media image associated with the given index."

    _check_inst()

    if not can_create_image(index):
        raise MediaError, "cannot create image for index %d" % (index,)

    return inst.create_image(index, boot_image_path)
