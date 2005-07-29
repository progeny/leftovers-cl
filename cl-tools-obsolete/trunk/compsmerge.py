#!/usr/bin/python

import sys
import optparse
import xml.dom
import xml.dom.minidom

def pretty_format(tree, node = None, indent_level = 1):
    if not node:
        node = tree.documentElement

    for child in node.childNodes[:]:
        has_subchildren = False
        if child.hasChildNodes():
            for subchild in child.childNodes:
                if subchild.hasChildNodes():
                    has_subchildren = True
                    break
        if has_subchildren:
            pretty_format(tree, child, indent_level + 1)
            child.appendChild(tree.createTextNode("\n" + ("  " * indent_level)))

        prefix = tree.createTextNode("\n" + ("  " * indent_level))
        node.insertBefore(prefix, child)

def parse_grouphierarchy(tree, node):
    cat_list = []
    for category in node.childNodes:
        if category.nodeType != xml.dom.Node.ELEMENT_NODE:
            continue
        cat_name = None
        cat_subcats = []
        for child in category.childNodes:
            if child.nodeType != xml.dom.Node.ELEMENT_NODE:
                continue
            if child.tagName == "name":
                cat_name = child.childNodes[0].data
            elif child.tagName == "subcategories":
                for subcat in child.childNodes:
                    if subcat.nodeType != xml.dom.Node.ELEMENT_NODE:
                        continue
                    cat_subcats.append(subcat.childNodes[0].data)
        if cat_name and cat_subcats:
            cat_list.append((cat_name, tuple(cat_subcats)))

    return tuple(cat_list)

def main():
    # Parse options and get input file list.

    option_parser = optparse.OptionParser()
    option_parser.add_option("-f", "--output-file", dest="outfile",
                             default=None, help="write output to FILE",
                             metavar="FILE")
    (options, args) = option_parser.parse_args()

    # Create the output DOM tree.

    out_tree = xml.dom.minidom.getDOMImplementation().createDocument(None,
                                                                     "comps",
                                                                     None)

    # Iterate over the input file list.
    hierarchy = {}
    for in_fn in args:
        errstr = None

        # Parse each file.

        try:
            in_tree = xml.dom.minidom.parse(in_fn)
        except:
            in_tree = None

        # Sanity-check the parse tree.

        if not in_tree:
            errstr = "W: problem with parsing %s\n" % (in_fn,)
        elif in_tree.documentElement.tagName != "comps":
            errstr = "W: %s is not a comps file\n" % (in_fn,)

        if errstr:
            sys.stderr.write(errstr)
            continue

        # Clone each child of the toplevel node to the output node.

        for child in in_tree.documentElement.childNodes:
            if child.nodeType == xml.dom.Node.ELEMENT_NODE and \
               child.tagName == "grouphierarchy":
                for (cat, subcats) in parse_grouphierarchy(in_tree, child):
                    if not hierarchy.has_key(cat):
                        hierarchy[cat] = []
                    hierarchy[cat].extend(subcats[:])
            else:
                new_child = child.cloneNode(True)
                out_tree.documentElement.appendChild(new_child)

    # Add group hierarchy information.

    hierarchy_node = out_tree.createElement("grouphierarchy")
    out_tree.documentElement.appendChild(hierarchy_node)

    for cat in hierarchy.keys():
        cat_node = out_tree.createElement("category")
        hierarchy_node.appendChild(cat_node)

        name_node = out_tree.createElement("name")
        name_node.appendChild(out_tree.createTextNode(cat))
        cat_node.appendChild(name_node)

        subcat_node = out_tree.createElement("subcategories")
        cat_node.appendChild(subcat_node)
        for subcat in hierarchy[cat]:
            subcat_item_node = out_tree.createElement("subcategory")
            subcat_item_node.appendChild(out_tree.createTextNode(subcat))
            subcat_node.appendChild(subcat_item_node)

    # Format group hierarchy information properly.

    pretty_format(out_tree, hierarchy_node, 2)
    out_tree.documentElement.insertBefore(out_tree.createTextNode("  "),
                                          hierarchy_node)
    hierarchy_node.appendChild(out_tree.createTextNode("\n  "))
    out_tree.documentElement.appendChild(out_tree.createTextNode("\n"))

    # Write the output node to the proper output.

    if options.outfile:
        outfile = open(options.outfile, "w")
    else:
        outfile = sys.stdout

    outfile.write(out_tree.toxml("utf-8"))
    outfile.write("\n")

if __name__ == "__main__":
    main()
