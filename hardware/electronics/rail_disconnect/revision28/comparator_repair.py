"""Repair actual backside SOIC/floor collision using TI PW0014A pattern."""

import hashlib
import json
import uuid

from ...common.sexpr import a, children, first, read_sexpr, sexpr
from .integrate_positive import ROOT, footprint, native_parts, write_schematic
from .positive_footprints import main as patterns
from .repair import Router


def main():
    patterns()
    parts = native_parts()
    by = {c["ref"]: c for c in parts}
    write_schematic(parts)
    path = ROOT / "rail_disconnect.kicad_pcb"
    before = path.read_bytes()
    tree = read_sexpr(before.decode())
    nets = {str(n[2]).lstrip("/"): int(n[1]) for n in children(tree, "net")}
    removed = []
    kept = []
    for node in tree:
        drop = False
        if isinstance(node, list) and node:
            if node[0] == "footprint":
                ref = next(p[2] for p in children(node, "property") if p[1] == "Reference")
                drop = ref == "U18"
                if ref in ("U9", "U10"):
                    for prop in children(node, "property"):
                        if prop[1] in ("MPN", "Value"):
                            prop[2] = by[ref]["part"]
            elif node[0] in ("segment", "via"):
                keys = ("at",) if node[0] == "via" else ("start", "end")
                pts = [tuple(float(v) - 100 for v in first(node, key)[1:3]) for key in keys]
                relevant = node[0] == "via" or first(node, "layer")[1] == "B.Cu"
                drop = relevant and any(103 <= x <= 115 and 34.5 <= y <= 44.5 for x, y in pts)
        if drop:
            removed.append(sexpr(node))
        else:
            kept.append(node)
    tree = kept + [footprint(by["U18"], (109, 39.5, 0, "B"), nets)]
    rt = Router(tree)
    for p in rt.by_ref["U18"]:
        sign = 1 if p["xy"][0] > 109 else -1
        endpoint = (round(p["xy"][0] + sign * (p["size"][0] / 2 + 0.575 + int(p["pin"]) % 2), 6), p["xy"][1])
        rt.path(p["net"], 5, [p["xy"], endpoint], 0.2)
        rt.via(p["net"], endpoint)
    for i, node in enumerate(tree):
        if (
            isinstance(node, list)
            and node
            and node[0] in ("segment", "via", "zone")
            and not children(node, "uuid")
        ):
            node.append(
                [a("uuid"), a(str(uuid.uuid5(uuid.NAMESPACE_URL, f"rmx:E28:PW14:{i}:{sexpr(node)}")))]
            )
    path.write_text(sexpr(tree) + "\n")
    (ROOT / "generated/comparator-package-repair.json").write_text(
        json.dumps(
            dict(
                before_sha256=hashlib.sha256(before).hexdigest(),
                after_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                removed_items=removed,
                official_ordering={"U9": "TLV1824DR", "U10": "TLV1824DR", "U18": "TLV1824PWR"},
                u18_pose=[109, 39.5, 0, "B"],
                body_max_mm=1.2,
                additional_seat_max_mm=0.1,
                pcb_bottom_z_mm=4.6,
                floor_top_z_mm=2.8,
                nominal_floor_gap_mm=0.5,
                mechanical_tolerance_reviewed=False,
                physical_qualified=False,
            ),
            indent=2,
        )
        + "\n"
    )


if __name__ == "__main__":
    main()
