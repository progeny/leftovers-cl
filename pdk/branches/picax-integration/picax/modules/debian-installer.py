import os
import string
import shutil
import tarfile
import urllib2
import apt_pkg
import picax.config
import picax.media
import picax.log

options = { "inst-base-url": { "config-key": "base-url",
                               "parameter": True },
            "inst-cdrom-path": { "config-key": "cdrom_path",
                                 "parameter": True },
            "inst-floppy-path": { "config-key": "floppy_path",
                                  "parameter": True },
            "inst-template-path": { "config-key": "template_path",
                                    "parameter": True,
                                    "parameter-desc": "path",
                                    "doc": ("Directory tree for first CD files",) },
            "inst-udeb-include-list": { "config-key": "udeb_include_list",
                                        "parameter": True },
            "inst-udeb-exclude-list": { "config-key": "udeb_exclude_list",
                                        "parameter": True },
            "inst-exclude-task": {"config-key": "exclude-task",
                                  "parameter": True } }

boot_image_map = { "i386": "isolinux/isolinux.bin",
                   "amd64": "isolinux/isolinux.bin",
                   "ia64": "boot/boot.img" }

di_required_packages = [ "eject", "grub" ]

def _configure():
    global conf
    global inst_conf
    global log

    conf = picax.config.get_config()
    inst_conf = conf["installer_options"]
    log = picax.log.get_logger()

def get_options():
    return options

def _get_boot_image_path():
    global conf
    global boot_image_map

    if boot_image_map.has_key(conf["arch"]):
        return boot_image_map[conf["arch"]]
    else:
        return None

class DIMediaBuilder(picax.media.MediaBuilder):
    def create_media(self):
        picax.media.create_image(1, _get_boot_image_path())
        index = 2
        while picax.media.can_create_image(index):
            picax.media.create_image(index)
            index = index + 1

def get_media_builder():
    return DIMediaBuilder()

def _read_task_info():
    global conf

    task_info = {}

    (distro, component) = conf["repository_list"][0]
    packages_path = "%s/dists/%s/%s/binary-%s/Packages" \
                    % (conf["base_path"], distro, component, conf["arch"])
    packages_file = open(packages_path)
    packages = apt_pkg.ParseTagFile(packages_file)

    while packages.Step() == 1:
        if packages.Section.has_key("Task"):
            pkg = packages.Section["Package"]
            task = packages.Section["Task"]
            if not task_info.has_key(task):
                task_info[task] = []
            task_info[task].append(pkg)

    packages_file.close()
    return task_info

def get_package_requests():
    global conf

    task_info = _read_task_info()

    pkgs = []
    pkgs.extend(di_required_packages)
    for task in task_info.keys():
        if not inst_conf.has_key("exclude-task") or \
           task not in inst_conf["exclude-task"].split(","):
            pkgs.extend(task_info[task])

    return pkgs

def _dos_tr(unixstr):
    return string.replace(unixstr, "\n", "\r\n")

def _copy_template(cd_path):
    global inst_conf

    if inst_conf.has_key("template_path") and \
       os.path.isdir(inst_conf["template_path"]):
        for template_fn in os.listdir(inst_conf["template_path"]):
            if template_fn[0] == ".":
                continue
            template_path = "%s/%s" % (inst_conf["template_path"],
                                       template_fn)
            if os.path.isdir(template_path):
                shutil.copytree(template_path,
                                "%s/%s" % (cd_path, template_fn))
            else:
                shutil.copy2(template_path, cd_path)

def _download_di_base(base_uri, dest_path, file_list):
    if not os.path.isdir(dest_path):
        os.makedirs(dest_path)

    for image in file_list:
        input_file = urllib2.urlopen("%s/%s" % (base_uri, image))
        output_file = open(dest_path + "/" + image, "w")
        output_file.write(input_file.read())
        input_file.close()
        output_file.close()

def _install_common(cd_path):
    global conf
    global inst_conf

    log.info("Installing debian-installer common files")

    (distro, component) = conf["repository_list"][0]

    for isodir in (".disk",):
        if not os.path.isdir(cd_path + "/" + isodir):
            os.mkdir(cd_path + "/" + isodir)

    compfile = open(cd_path + "/.disk/base_components", "w")
    compfile.write(component + "\n")
    compfile.close()

    compfile = open(cd_path + "/.disk/base_installable", "w")
    compfile.close()

    for (key, fn) in (("udeb_include_list", "udeb_include"),
                      ("udeb_exclude_list", "udeb_exclude")):
        if inst_conf.has_key(key) and os.path.exists(inst_conf[key]):
            shutil.copyfile(inst_conf[key], "%s/.disk/%s" % (cd_path, fn))

def _install_i386(cd_path):
    global conf
    global inst_conf

    boot_image_list = ["initrd.gz", "vmlinuz",
                       "debian-cd_info.tar.gz"]
    disk_image_list = ["cd-drivers.img", "boot.img",
                       "root.img", "net-drivers.img"]

    base_url = inst_conf["base-url"]
    (distro, component) = conf["repository_list"][0]

    log.info("Installing debian-installer for %s" % (conf["arch"],))

    for isodir in ("isolinux", "install"):
        if not os.path.isdir(cd_path + "/" + isodir):
            os.mkdir(cd_path + "/" + isodir)

    dl_path = conf["temp_dir"] + "/di-download"
    os.mkdir(dl_path)

    image_path = dl_path + "/" + inst_conf["cdrom_path"]

    try:
        _download_di_base("%s/%s" % (base_url, inst_conf["cdrom_path"]),
                          image_path, boot_image_list)

        if not os.path.exists("/usr/lib/syslinux/isolinux.bin"):
            raise RuntimeError, "you must have syslinux installed"
        shutil.copyfile("/usr/lib/syslinux/isolinux.bin",
                        cd_path + "/isolinux/isolinux.bin")

        shutil.copyfile(image_path + "/vmlinuz",
                        cd_path + "/install/vmlinuz")
        shutil.copyfile(image_path + "/initrd.gz",
                        cd_path + "/install/initrd.gz")

        isohelp = tarfile.open(image_path + "/debian-cd_info.tar.gz")
        for tarmember in isohelp.getmembers():
            if not os.path.exists("%s/isolinux/%s" % (cd_path,
                                                      tarmember.name)):
                isohelp.extract(tarmember, cd_path + "/isolinux")
        isohelp.close()

        if not os.path.exists(cd_path + "/isolinux/isolinux.cfg"):
            isocfg = open(cd_path + "/isolinux/isolinux.cfg", "w")
            isocfg.write("""DEFAULT /install/vmlinuz
APPEND vga=normal initrd=/install/initrd.gz ramdisk_size=10240 root=/dev/rd/0 init=/linuxrc devfs=mount,dall rw
LABEL linux
  kernel /install/vmlinuz
LABEL cdrom
  kernel /install/vmlinuz
LABEL expert
  kernel /install/vmlinuz
  append DEBCONF_PRIORITY=low vga=normal initrd=/install/initrd.gz ramdisk_size=10240 root=/dev/rd/0 init=/linuxrc devfs=mount,dall rw
DISPLAY boot.txt
TIMEOUT 0
PROMPT 1
F1 f1.txt
F2 f2.txt
F3 f3.txt
F4 f4.txt
F5 f5.txt
F6 f6.txt
F7 f7.txt
F8 f8.txt
F9 f9.txt
F0 f10.txt
""")
            isocfg.close()

    finally:
        shutil.rmtree(dl_path)

_install_amd64 = _install_i386

def _install_ia64(cd_path):
    global conf
    global inst_conf

    print "Installing debian-installer for %s..." % (conf["arch"],)

    for isodir in ("boot",):
        if not os.path.isdir(cd_path + "/" + isodir):
            os.mkdir(cd_path + "/" + isodir)

    _download_di_base("%s/%s" % (inst_conf["base-url"],
                                 inst_conf["cdrom_path"]),
                      cd_path + "/boot", ("boot.img",))

def install(cd_path):
    global conf

    _configure()

    arch_specific_install = globals()["_install_" + conf["arch"]]

    _copy_template(cd_path)
    _install_common(cd_path)
    arch_specific_install(cd_path)

def post_install(cd_path):
    global conf
    global inst_conf

    dist_path = cd_path + "/dists/"
    distro = conf["repository_list"][0][0]

    for link in ("frozen", "testing", "stable", "unstable"):
        if not os.path.exists(dist_path + link):
            os.symlink(distro, dist_path + link)
