"""Bind actual power fill to the relocated positive force terminals."""

import hashlib
import json
import uuid

from ...common.sexpr import a, children, first, read_sexpr, sexpr
from ..revision26.planes import ribbon
from .repair import ROOT


def main():
    path = ROOT / "rail_disconnect.kicad_pcb"
    before = path.read_bytes()
    tree = read_sexpr(before.decode())
    nets = {str(n[2]).lstrip("/"): int(n[1]) for n in children(tree, "net")}
    arm_ids = {str(uuid.uuid5(uuid.NAMESPACE_URL, f"rmx:E28:digital-force-arm:{i}")) for i in range(3)}
    removed = []
    kept = []
    for node in tree:
        drop = False
        if isinstance(node, list) and node and node[0] == "zone":
            drop = (
                str(first(node, "net")[1]) == str(nets["5V_DIG_SRC"]) and first(node, "layer")[1] == "In1.Cu"
            )
            drop |= bool(children(node, "uuid") and str(first(node, "uuid")[1]) in arm_ids)
        if drop:
            removed.append(sexpr(node))
        else:
            kept.append(node)
    assert len(removed) in (5, 8)
    added = ribbon("5V_DIG_SRC", "In1.Cu", [(115, 6), (130.524, 5.5), (134.524, 20.5)], 8, 36, nets)
    for i, node in enumerate(added):
        node.append(
            [
                a("uuid"),
                a(str(uuid.uuid5(uuid.NAMESPACE_URL, f"rmx:E28:force-source-ribbon:{i}:{sexpr(node)}"))),
            ]
        )
    arm = ribbon("5V_DIG", "In3.Cu", [(146, 2.5), (153, 12)], 8, 36, nets)
    assert len(arm) == 3
    for i, node in enumerate(arm):
        node.append([a("uuid"), a(str(uuid.uuid5(uuid.NAMESPACE_URL, f"rmx:E28:digital-force-arm:{i}")))])
    path.write_text(sexpr(kept + added + arm) + "\n")
    (ROOT / "generated/force-source-ribbon-repair.json").write_text(
        json.dumps(
            dict(
                before_sha256=hashlib.sha256(before).hexdigest(),
                after_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                removed_items=removed,
                actual_source_stud="J11",
                centreline_mm=[[115, 6], [130.524, 5.5], [134.524, 20.5]],
                protected_force_pad="J4.1",
                protected_force_arm_mm=[[146, 2.5], [153, 12]],
                nominal_zone_width_mm=8,
                filled_continuity_and_resistance_qualified=False,
            ),
            indent=2,
        )
        + "\n"
    )


if __name__ == "__main__":
    main()
