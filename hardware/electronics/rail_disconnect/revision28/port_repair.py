"""Explicit post-routing J11 collision repair and R88 access relocation."""

import hashlib
import json
import math
import uuid

from ...common.sexpr import a, children, first, read_sexpr, sexpr
from .integrate_positive import ROOT, footprint, native_parts, write_schematic
from .repair import Router


def main():
    path = ROOT / "rail_disconnect.kicad_pcb"
    before = path.read_bytes()
    tree = read_sexpr(before.decode())
    parts = native_parts()
    by = {c["ref"]: c for c in parts}
    write_schematic(parts)
    nets = {str(n[2]).lstrip("/"): int(n[1]) for n in children(tree, "net")}
    names = {v: k for k, v in nets.items()}
    removed = []
    kept = []
    for node in tree:
        if isinstance(node, list) and node:
            if node[0] == "footprint":
                ref = next(p[2] for p in children(node, "property") if p[1] == "Reference")
                if ref in ("J11", "R88"):
                    removed.append(sexpr(node))
                    continue
                if ref in by:
                    for prop in children(node, "property"):
                        if prop[1] in ("Value", "MPN"):
                            prop[2] = by[ref]["part"]
            if node[0] in ("segment", "via"):
                keys = ("at",) if node[0] == "via" else ("start", "end")
                coords = [tuple(float(v) - 100 for v in first(node, k)[1:3]) for k in keys]
                net = names[int(first(node, "net")[1])]
                # Remove actual old positive-stud fanout and oldR88land vias.
                old_stitch = net == "5V_DIG_SRC" and any(
                    abs(math.dist(p, (118, 6)) - radius) < 1e-5 for p in coords for radius in (3.3, 4.8)
                )
                old_resistor = any(
                    math.dist(p, q) < 0.01 for p in coords for q in ((109.05, 1.5), (110.95, 1.5))
                )
                # Real new NPTH and solder land must clear all layers/copper.
                newhole = any(math.dist(p, (115, 6)) < 2.7 for p in coords)
                newland = (
                    (node[0] == "via" or first(node, "layer")[1] == "F.Cu")
                    and net != "5V_DIG_SRC"
                    and any(math.dist(p, (115, 6)) < 4.8 for p in coords)
                )
                if old_stitch or old_resistor or newhole or newland:
                    removed.append(sexpr(node))
                    continue
        kept.append(node)
    tree = kept
    for ref, pose in (("J11", (115, 6, 0, "F")), ("R88", (110.5, 13, 0, "F"))):
        tree.append(footprint(by[ref], pose, nets))
    rt = Router(tree)
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        rt.path("5V_DIG_SRC", 0, [(115 + 3.3 * dx, 6 + 3.3 * dy), (115 + 4.8 * dx, 6 + 4.8 * dy)], 0.8)
        rt.via("5V_DIG_SRC", (115 + 4.8 * dx, 6 + 4.8 * dy))
    for pad in rt.by_ref["R88"]:
        rt.via(pad["net"], pad["xy"])
    for i, node in enumerate(tree):
        if (
            isinstance(node, list)
            and node
            and node[0] in ("segment", "via", "zone")
            and not children(node, "uuid")
        ):
            node.append(
                [a("uuid"), a(str(uuid.uuid5(uuid.NAMESPACE_URL, f"rmx:E28:port-repair:{i}:{sexpr(node)}")))]
            )
    path.write_text(sexpr(tree) + "\n")
    (ROOT / "generated/port-repair.json").write_text(
        json.dumps(
            dict(
                before_sha256=hashlib.sha256(before).hexdigest(),
                after_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                removed_items=removed,
                new_ports={"J11": [115, 6], "R88": [110.5, 13, 0, "F"]},
                physical_qualified=False,
            ),
            indent=2,
        )
        + "\n"
    )


if __name__ == "__main__":
    main()
