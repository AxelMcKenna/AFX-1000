"""KiCad exported-netlist parsing and component values."""

import re
import xml.etree.ElementTree as ET


def netlist(path):
    tree = ET.parse(path)
    pins = {}
    for net in tree.findall("./nets/net"):
        name = net.attrib["name"].lstrip("/")
        for node in net.findall("node"):
            if not node.attrib["ref"].startswith("#"):
                pins.setdefault(node.attrib["ref"], {})[node.attrib["pin"]] = name
    parts = {
        c.attrib["ref"]: c for c in tree.findall("./components/comp") if not c.attrib["ref"].startswith("#")
    }
    return parts, pins


def number(value):
    token = value.split()[0]
    if token.endswith("M"):
        return float(token[:-1]) * 1e6
    if token.endswith("R"):
        return float(token[:-1])
    m = re.fullmatch(r"([0-9.]+)([kmunp]?)(?:F)?", token)
    if not m:
        raise ValueError(value)
    return float(m[1]) * {"": 1, "k": 1000, "m": 0.001, "u": 1e-6, "n": 1e-9, "p": 1e-12}[m[2]]
