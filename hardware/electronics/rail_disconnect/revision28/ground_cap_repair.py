"""Actual C40 return-barrel connection around the neighboring ILM barrel."""

import hashlib
import json
import math
import uuid

from ...common.sexpr import a, children, read_sexpr, sexpr
from .focused import legal_line
from .repair import ROOT, Router


def main(layer=1):
    path = ROOT / "rail_disconnect.kicad_pcb"
    before = path.read_bytes()
    tree = read_sexpr(before.decode())
    rt = Router(tree)
    pad = next(p for p in rt.by_ref["C40"] if p["pin"] == "2")
    assert pad["net"] == "AGND" and math.dist(pad["xy"], (43.95, 2)) < 1e-7
    start = rt.existing_via("AGND", pad["xy"])
    finish = rt.existing_via("AGND", (45, 5))
    assert start and finish
    if layer == 1:
        from .ground_corridor import path_between

        points, visited = path_between(rt, start, finish, layer)
    else:
        points = [start, (44.5, 2.5), (44.5, 4.2), finish]
        visited = None
    assert all(legal_line(rt, "AGND", layer, p, q, 0.2) for p, q in zip(points, points[1:]))
    rt.path("AGND", layer, points, 0.2)
    ids = []
    for index, node in enumerate(tree):
        if isinstance(node, list) and node and node[0] == "segment" and not children(node, "uuid"):
            uid = str(uuid.uuid5(uuid.NAMESPACE_URL, f"rmx:E28:C40-return:{index}:{sexpr(node)}"))
            node.append([a("uuid"), a(uid)])
            ids.append(uid)
    assert ids
    path.write_text(sexpr(tree) + "\n")
    (ROOT / "generated/c40-return-connection.json").write_text(
        json.dumps(
            dict(
                before_sha256=hashlib.sha256(before).hexdigest(),
                after_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                actual_pin="C40.2",
                net="AGND",
                points_mm=points,
                layer=("F.Cu", "In1.Cu", "In2.Cu", "In3.Cu", "In4.Cu", "B.Cu")[layer],
                local_search_visited=visited,
                width_mm=0.2,
                existing_actual_barrels_reused=True,
                added_drills=0,
                protected_ids=ids,
                native_and_filled_force_preservation_check_required=True,
                bypass_effective_capacitance_and_dynamic_proof=False,
                physical_qualified=False,
            ),
            indent=2,
        )
        + "\n"
    )
    print("Connected actual C40 ground barrel to existing ground barrel", points)


if __name__ == "__main__":
    main()
