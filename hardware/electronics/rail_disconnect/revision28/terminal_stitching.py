"""Finite-barrel attachment arrays inside actual SMT terminal copper annuli.

Eight .300/.600mm through barrels at radius3.300mm are candidate IPC4761 TypeVII
filled/capped, flush planar structures. Manufacturer stencil/assembly/mechanical
acceptance is NOT established by this implementation or a native DRC pass.
"""

import hashlib
import json
import math
import uuid

from ...common.sexpr import a, children, read_sexpr, sexpr
from .repair import ROOT, Router
from .terminals import ALL_TERMINALS


def sites(x, y):
    return [
        (round(x + 3.3 * math.cos(i * math.pi / 4), 6), round(y + 3.3 * math.sin(i * math.pi / 4), 6))
        for i in range(8)
    ]


def main():
    path = ROOT / "rail_disconnect.kicad_pcb"
    before = path.read_bytes()
    tree = read_sexpr(before.decode())
    rt = Router(tree)
    rows = []
    for ref, (x, y, net) in ALL_TERMINALS.items():
        used = []
        for point in sites(x, y):
            # Reuse a real same-net nearby barrel rather than create overlapping
            # drills. Every reused/added coordinate is recorded for native QA.
            old = next(
                (
                    g
                    for g in rt.geometry
                    if g["kind"] == "via"
                    and g["net"] == net
                    and g.get("layers") == tuple(range(6))
                    and math.dist(g["xy"], point) < 0.56
                ),
                None,
            )
            if old is not None:
                used.append(dict(target_mm=point, actual_mm=old["xy"], new=False))
                continue
            rt.via(net, point)
            used.append(dict(target_mm=point, actual_mm=point, new=True))
        rows.append(dict(ref=ref, net=net, center_mm=[x, y], sites=used))
    ids = []
    for i, node in enumerate(tree):
        if isinstance(node, list) and node and node[0] == "via" and not children(node, "uuid"):
            uid = str(uuid.uuid5(uuid.NAMESPACE_URL, f"rmx:E28:terminal-stitch:{i}:{sexpr(node)}"))
            node.append([a("uuid"), a(uid)])
            ids.append(uid)
    path.write_text(sexpr(tree) + "\n")
    (ROOT / "generated/terminal-stitching.json").write_text(
        json.dumps(
            dict(
                before_sha256=hashlib.sha256(before).hexdigest(),
                after_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                ports=rows,
                new_barrel_ids=ids,
                drill_mm=0.3,
                land_mm=0.6,
                nominal_radius_mm=3.3,
                minimum_plating_requirement_mm=0.025,
                filled_capped_planarity_accepted=False,
                manufacturer_stencil_and_assembly_accepted=False,
                mechanical_joint_qualification=False,
                physical_qualified=False,
            ),
            indent=2,
        )
        + "\n"
    )
    print(
        "Added",
        len(ids),
        "actual terminal attachment barrels; fabrication/assembly/physical acceptance remains false.",
    )


if __name__ == "__main__":
    main()
