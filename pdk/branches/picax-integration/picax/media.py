#!/usr/bin/python

import sys
import os
import picax.config
import picax.installer

loaded_module_name = None
inst = None

class MediaError(StandardError):
    pass

class MediaBuilder:
    def create_media(self):
        index = 1
        while can_create_image(index):
            create_image(index)
            index = index + 1

def is_media():
    return inst != None

def _check_inst():
    if not is_media():
        raise MediaError, "no media type has been set"

def create_media():
    if not is_media():
        return

    conf = picax.config.get_config()

    if "installer_component" in conf:
        media_builder = picax.installer.get_media_builder()
    else:
        media_builder = MediaBuilder()

    media_builder.create_media()

def set_media(name, module_dir = None):
    global loaded_module_name
    global inst

    if inst is not None:
        if name != loaded_module_name:
            raise MediaError, "cannot load two different media modules"
    else:
        if module_dir:
            sys.path.append(module_dir)

        inst_toplevel = None
        namespace = None
        for parent_module in ("picax_modules", "picax.modules"):
            try:
                full_name = parent_module + "." + name
                inst_toplevel = __import__(full_name)
                namespace = parent_module
                break
            except:
                pass

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
    _check_inst()

    return inst.get_options()

def get_part_size():
    _check_inst()

    return inst.get_part_size()

def can_create_image(index):
    _check_inst()

    config = picax.config.get_config()
    path = "%s/bin%d" % (config["dest_path"], index)
    if not os.path.isdir(path):
        return False

    return True

def create_image(index, boot_image_path = None):
    _check_inst()

    if not can_create_image(index):
        raise MediaError, "cannot create image for index %d" % (index,)

    return inst.create_image(index, boot_image_path)
