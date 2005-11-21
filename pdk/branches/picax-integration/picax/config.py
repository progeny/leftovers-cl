import sys
import os
import types
import string
import getopt
import xml.dom
import xml.dom.minidom

import picax.installer
import picax.media
import picax.log

config = None

main_options = { "help": { "config-key": "help",
                           "parameter": False,
                           "doc": ("Show brief usage help",) },
                 "debug": { "config-key": "debug",
                            "parameter": False,
                            "doc": ("Turn debugging output on",) },
                 "quiet": { "config-key": "quiet",
                            "parameter": False,
                            "doc": ("Suppress unneeded output",) },
                 "version": { "config-key": "version",
                              "parameter": False,
                              "doc": ("Show the software version",) },
                 "order": { "config-key": "order_file",
                            "parameter": True,
                            "parameter-desc": "file",
                            "doc": ("Set package order from file",) },
                 "arch": { "config-key": "arch",
                           "parameter": True,
                           "parameter-desc": "architecture",
                           "doc": ("Target architecture",) },
                 "num-parts": { "config-key": "num_parts",
                                "parameter": True,
                                "parameter-type": "number",
                                "parameter-default": 0,
                                "parameter-desc": "num",
                                "doc": ("Number of parts to split the repo into",) },
                 "part-size": { "config-key": "part_size",
                                "parameter": True,
                                "parameter-type": "number",
                                "parameter-default": 0,
                                "parameter-desc": "bytes",
                                "doc": ("Size in bytes for each part",) },
                 "cd-label": { "config-key": "cd_label",
                               "parameter": True,
                               "parameter-desc": "label",
                               "doc": ("Apt label for destination CD",) },
                 "dest-path": { "config-key": "dest_path",
                                "parameter": True,
                                "parameter-desc": "path",
                                "doc": ("Destination for dirs/images",) },
                 "media": { "config-key": "media_component",
                            "parameter": True,
                            "parameter-desc": "type",
                            "doc": ("Use the named media type",) },
                 "installer": { "config-key": "installer_component",
                                "parameter": True,
                                "parameter-desc": "installer",
                                "doc": ("Use the named installer",) },
                 "source": { "config-key": "source",
                             "parameter": True,
                             "parameter-default": "separate",
                             "parameter-constraints": [ "none", "separate",
                                                        "immediate", "mixed" ],
                             "parameter-desc": "type",
                             "doc": ("Set type of source media to create",) },
                 "apt-repo-path": { "config-key": "correction_apt_repo",
                                    "parameter": True },
                 "short-package-list": { "config-key": "short_package_list",
                                         "parameter": False,
                                         "doc": ("Don't include all packages in the distribution",) },
                 "no-debootstrap": { "config-key": "no_debootstrap",
                                     "parameter": False,
                                     "doc": ("Don't automatically include debootstrap packages",) },
                 "base-media": { "config-key": "base_media",
                                 "parameter": True,
                                 "parameter-type": "multistring",
                                 "parameter-desc": "path[:path...]",
                                 "doc": ("Paths to mounted media to use as base",) },
                 "read-config": { "config-key": "input_config_path",
                                  "parameter": True,
                                  "parameter-desc": "filename",
                                  "doc": ("Read configuration from file",) },
                 "write-config": { "config-key": "output_config_path",
                                   "parameter": True,
                                   "parameter-desc": "filename",
                                   "doc": ("Write configuration to file",) } }

module_prefixes = (("inst", "installer", "installer_options",
                    picax.installer.get_options),
                   ("media", "media", "media_options",
                    picax.media.get_options))

class ConfigError(StandardError):
    pass

def _parse_value(option_dict, value, err_template):
    new_value = string.strip(value)

    if option_dict.has_key("parameter-type"):
        if option_dict["parameter-type"] == "number":
            new_value = int(new_value)
        elif option_dict["parameter-type"] == "multistring":
            new_value = string.split(new_value, ":")
        else:
            raise ConfigError, "invalid parameter type '%s'" % (options[option]["parameter-type"],)

    if option_dict.has_key("parameter-constraints") and \
       new_value not in option_dict["parameter-constraints"]:
        raise ConfigError, err_template % (value,)

    return new_value

def _set_defaults(config, options):
    for option in options.keys():
        value = None
        if options[option]["parameter"]:
            if options[option].has_key("parameter-default"):
                value = options[option]["parameter-default"]
            elif options[option].has_key("parameter-type"):
                if options[option]["parameter-type"] == "multistring":
                    value = []
        else:
            value = False
        if value is not None:
            config[options[option]["config-key"]] = value

def _get_module_options(prefix):
    for (mprefix, mname, mkey, mfunc) in module_prefixes:
        if mprefix == prefix:
            return mfunc()

    raise ValueError, "invalid prefix"

def _init():
    global config
    global main_options

    if config:
        return

    config = { "repository_list": [],
               "debug": False }

    if os.environ.has_key("TMPDIR"):
        config["temp_dir"] = os.environ["TMPDIR"]
    else:
        config["temp_dir"] = "/tmp"

    if os.environ.has_key("PICAX_DEBUG"):
        config["debug"] == True

def _dom_to_config(config, topnode, options, prefixes = ()):
    for child in topnode.childNodes:
        if child.nodeType != xml.dom.Node.ELEMENT_NODE:
            continue

        module_options = None
        for (prefix, prefix_name, prefix_key, prefix_func) in prefixes:
            if child.tagName == prefix_key:
                module_options = _get_module_options(prefix)
                config[prefix_key] = _dom_to_config({}, child, module_options)
                break
        if module_options is not None:
            continue

        if child.tagName == "repository":
            distro = child.getAttribute("distribution")
            comp = child.getAttribute("component")
            config["repository_list"].append((distro, comp))
            continue

        if child.tagName not in options.keys():
            raise ConfigError, "config file has invalid item: %s" \
                  % (child.tagName,)

        value = None
        if options[child.tagName]["parameter"]:
            for node in child.childNodes:
                if node.nodeType == xml.dom.Node.TEXT_NODE:
                    value = node.data
                    break
            if value is None:
                raise ConfigError, "config file item %s has no value" \
                      % (child.tagName,)

            value = _parse_value(options[child.tagName], value,
                                 "value %%s for config file item %s invalid"
                                 % (child.tagName,))
        else:
            value = True

        config[options[child.tagName]["config-key"]] = value

        if child.tagName == "installer":
            picax.installer.set_installer(value)
        elif child.tagName == "media":
            picax.media.set_media(value)

    return config

def _config_to_dom_tree(config, options, document, topnode, prefixes = ()):
    option_list = options.keys()
    option_list.sort()
    for option in option_list:
        if option in ("read-config", "write-config"):
            continue
        if config.has_key(options[option]["config-key"]):
            value = config[options[option]["config-key"]]
            if options[option]["parameter"]:
                if options[option].has_key("parameter-type"):
                    if options[option]["parameter-type"] == "number":
                        value = str(value)
                    elif options[option]["parameter-type"] == "multistring":
                        value = string.join(value, ":")
                    else:
                        raise ConfigError, "invalid parameter type '%s'" % (options[option]["parameter-type"],)
                node = document.createElement(option)
                node.appendChild(document.createTextNode(value))
                topnode.appendChild(node)
            else:
                if value:
                    node = document.createElement(option)
                    topnode.appendChild(node)

    for (prefix, prefix_name, prefix_key, prefix_func) in prefixes:
        if config.has_key(prefix_key):
            node = document.createElement(prefix_key)
            topnode.appendChild(node)
            suboptions = _get_module_options(prefix)
            _config_to_dom_tree(config[prefix_key], suboptions, document, node)

    for (distro, comp) in config["repository_list"]:
        node = document.createElement("repository")
        node.setAttribute("distribution", distro)
        node.setAttribute("component", comp)
        topnode.appendChild(node)

def _config_to_dom(config, options, prefixes):
    document = xml.dom.minidom.parseString("<picaxconfig/>")

    _config_to_dom_tree(config, options, document, document.documentElement,
                        prefixes)

    return document

def _parse_args(config, arglist, options, sub_prefixes = ()):
    temp_arglist = arglist[:]
    subprefix_arglist = {}
    for subprefix in map(lambda x: x[0], sub_prefixes):
        subprefix_arglist[subprefix] = []

    try:
        while len(temp_arglist) > 0 and temp_arglist[0][0] == "-":
            arg = temp_arglist.pop(0)
            stripped_arg = arg
            while stripped_arg[0] == "-":
                stripped_arg = stripped_arg[1:]
            module_arg = ""
            for ch in stripped_arg:
                if ch == "-":
                    break
                else:
                    module_arg = module_arg + ch

            if string.find(stripped_arg, "=") != -1:
                (stripped_arg, extra_arg) = string.split(stripped_arg, "=", 1)
                arg = "--" + stripped_arg
                temp_arglist.insert(0, extra_arg)

            if stripped_arg in ("h", "?"):
                config["help"] = True
            elif options.has_key(stripped_arg):
                config_key = options[stripped_arg]["config-key"]
                has_value = options[stripped_arg]["parameter"]
                if has_value:
                    value = _parse_value(options[stripped_arg],
                                         temp_arglist.pop(0),
                                         "invalid value %%s for parameter --%s"
                                         % (stripped_arg,))

                    config[config_key] = value
                else:
                    config[config_key] = True
            elif module_arg in map(lambda x: x[0], sub_prefixes):
                subprefix_arglist[module_arg].append(arg)
                if len(temp_arglist) > 0 and temp_arglist[0][0] != "-":
                    subprefix_arglist[module_arg].append(temp_arglist.pop(0))
            else:
                raise ConfigError, "unknown option: " + arg

    except IndexError:
        raise ConfigError, "option requires value"

    return (temp_arglist, subprefix_arglist)

def _interpret_args(config, subprefix_arglist, arglist):
    global module_prefixes
    global main_options

    if os.environ.has_key("PICAX_DEBUG"):
        config["debug"] = True

    if config.has_key("installer_component"):
        picax.installer.set_installer(config["installer_component"])
    if config.has_key("media_component"):
        picax.media.set_media(config["media_component"])

    if config["help"]:
        optionlist = main_options
        for (mprefix, mname, mkey, mfunc) in module_prefixes:
            if config.has_key(mname + "_component"):
                optionlist = mfunc()
                break

        usage(sys.stdout, optionlist)
        sys.exit(0)
    elif config["version"]:
        version(sys.stdout)
        sys.exit(0)

    if len(arglist) not in (1, 3):
        raise ConfigError, "invalid repository arguments"

    if len(arglist) == 3:
        config["repository_list"].append(tuple(arglist[1:]))

    if len(config["repository_list"]) < 1:
        raise ConfigError, "no repositories provided"

    if config["num_parts"] == 0 and \
       config["part_size"] == 0 and \
       not config.has_key("media_component"):
        raise ConfigError, \
              "must specify media type, part size, or number of parts"
    if config["source"] == "separate" and config["num_parts"] != 0:
        raise ConfigError, "cannot use separate source and num_parts together"
    if config.has_key("media_component") and \
       (config["part_size"] != 0 or config["num_parts"] != 0):
        raise ConfigError, "cannot set part size or number with a media module"

    new_repo_list = []
    for repo_item in config["repository_list"]:
        if repo_item not in new_repo_list:
            new_repo_list.append(repo_item)
    config["repository_list"] = new_repo_list

    config["base_path"] = arglist[0]
    config["base_path"] = os.path.abspath(config["base_path"])
    if not config.has_key("dest_path"):
        config["dest_path"] = config["base_path"]

    for (mprefix, mname, mkey, mfunc) in module_prefixes:
        if config.has_key(mname + "_component"):
            if not config.has_key(mkey):
                config[mkey] = {}
            if subprefix_arglist.has_key(mprefix):
                module_options = mfunc()
                _set_defaults(config[mkey], module_options)
                _parse_args(config[mkey], subprefix_arglist[mprefix],
                            module_options)
        else:
            if subprefix_arglist.has_key(mprefix) and \
               len(subprefix_arglist[mprefix]) > 0:
                raise ConfigError, \
                      "%s options given without %s" % (mname, mname)

    if config.has_key("order_file"):
        try:
            try:
                order_file = open(config["order_file"])
                order_lines = order_file.readlines()
                config["order_pkgs"] = map(string.strip, order_lines)
            finally:
                order_file.close()
        except:
            picax.log.get_logger().warning(
                "Could not read order file %s" % (option[1],))
    if not config.has_key("order_pkgs"):
        config["order_pkgs"] = []
    if config.has_key("media_component"):
        config["part_size"] = picax.media.get_part_size()

def get_config():
    global config

    if not config:
        raise RuntimeError, "configuration not initialized"

    return config

def version(out):
    out.write("PICAX 2.0pre (svn revision: $Rev: 5091 $)\n")

def usage(out, options = None):
    global main_options

    show_module_options = False
    if options is None:
        options = main_options
        show_module_options = True

    version(out)

    out.write("usage: %s [options] base-path [dist section]\n" \
              % (sys.argv[0],))
    out.write("  base-path: root URI for apt repository\n")
    out.write("  dist:      distribution name (such as 'woody')\n")
    out.write("  section:   component section name (such as 'main')\n")
    out.write("Options:\n")

    option_list = options.keys()
    option_list.sort()
    maxlen = 0
    option_strs = []
    for option in option_list:
        option_str = "  --%s" % (option,)
        if options[option]["parameter"]:
            if options[option].has_key("parameter-desc"):
                parameter_desc = options[option]["parameter-desc"]
            else:
                parameter_desc = "?"
            option_str = option_str + ("=<%s>" % (parameter_desc,))
        if len(option_str) > maxlen:
            maxlen = len(option_str)
        if options[option].has_key("doc"):
            doc_str = options[option]["doc"][0]
        else:
            doc_str = ""

        option_strs.append((option_str, doc_str))

    if show_module_options:
        option_strs.append(("  --inst-<option>", "Pass an option to the installer"))
        option_strs.append(("  --media-<option>", "Pass an option to the media handler"))

    if len(option_strs) < 1:
        out.write("  No options are supported by this module.\n")
    else:
        maxlen = maxlen + 2
        for (option_str, option_doc) in option_strs:
            while len(option_str) < maxlen:
                option_str = option_str + " "
            out.write(option_str + option_doc + "\n")

def handle_args(arglist):
    global config
    global main_options
    global module_prefixes

    _init()
    cmdline_config = config.copy()
    xml_config = config.copy()

    (remaining, subprefix_arglist) = _parse_args(cmdline_config, arglist,
                                                 main_options,
                                                 module_prefixes)

    _set_defaults(config, main_options)

    if cmdline_config.has_key("input_config_path"):
        try:
            document = xml.dom.minidom.parse(
                cmdline_config["input_config_path"])
        except:
            raise ConfigError, "cannot parse XML configuration file"
        xml_config = _dom_to_config(xml_config, document.documentElement,
                                    main_options, module_prefixes)
        config.update(xml_config)

    for config_key in cmdline_config.keys():
        if config_key not in map(lambda x: x[2], module_prefixes):
            config[config_key] = cmdline_config[config_key]

    _interpret_args(config, subprefix_arglist, remaining)

    if config.has_key("output_config_path"):
        document = _config_to_dom(config, main_options, module_prefixes)
        outfile = open(config["output_config_path"], "w")
        outfile.write(document.toprettyxml("    "))
        outfile.close()

    # Handle architecture after writing the default.
    # XXX: don't hard-code; detect!

    if not config.has_key("arch"):
        config["arch"] = "i386"
