#!/usr/bin/python

import sys
import os
import string
import picax.config

# Standard parameters for CDs.  We could allow some of these to be
# controlled by module parameters at some point.

cd_size_multiplier = 1048576
mkisofs_std_args = "-R -J -T -joliet-long"

options = { "media-image-size": {"config-key": "image_size",
                                 "parameter": True,
                                 "parameter-type": "number",
                                 "parameter-default": 650,
                                 "parameter-desc": "megabytes",
                                 "doc": ("Image size in megabytes",)},
            "media-label": {"config-key": "label",
                            "parameter": True,
                            "parameter-desc": "label",
                            "doc": ("CD label to assign",)} }

def get_options():
    return options

def get_part_size():
    return picax.config.get_config()["media_options"]["image_size"] \
           * cd_size_multiplier

def create_image(index, boot_image_path):
    conf = picax.config.get_config()
    data_path = "%s/bin%d" % (conf["dest_path"], index)
    if not os.path.isdir(data_path):
        raise RuntimeError, "couldn't locate CD image source path"

    # If an image is provided, identify its type.

    boot_args = ""
    if boot_image_path is not None:
        if not os.path.exists(data_path + "/" + boot_image_path):
            raise RuntimeError, "could not find boot image"
        boot_args = "-b " + boot_image_path
        if boot_image_path[-12:] == "isolinux.bin" or \
           boot_image_path[-18:] == "isolinux-debug.bin":
            isolinux_path = os.path.dirname(boot_image_path)
            boot_args = boot_args + " -no-emul-boot -boot-load-size 4 -boot-info-table"
            boot_args = boot_args + " -c %s/boot.cat" % (isolinux_path,)
        elif boot_image_path[-8:] == "boot.img":
            boot_path = os.path.dirname(boot_image_path)
            boot_args = boot_args + " -no-emul-boot -c %s/boot.catalog" \
                        % (boot_path,)
        else:
            image_size = os.stat(data_path + "/" + boot_image_path).st_size
            if image_size not in (1228800, 1474560, 2949120):
                raise RuntimeError, "improper boot image specified"
            boot_args = boot_args + " -c boot.cat"

    # Write the apt label, if there is one.

    if conf.has_key("cd_label"):
        if not os.path.isdir(data_path + "/.disk"):
            os.mkdir("%s/.disk" % (data_path,))
        info_file = open("%s/.disk/info" % (data_path,), "w")
        info_file.write("%s (%d)\n" % (conf["cd_label"], index))
        info_file.close()

    # Handle CD label.

    label_options = ""
    if conf["media_options"].has_key("label"):
        label_options = "-V '%s %d'" % (conf["media_options"]["label"], index)

    if os.system("mkisofs -o %s/img-bin%d.iso %s %s %s %s" \
                 % (conf["dest_path"], index, mkisofs_std_args, label_options,
                    boot_args, data_path)):
        raise RuntimeError, "CD image generation failed"
