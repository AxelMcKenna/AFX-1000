"""Explicit compact local-bypass and force-stud access repair in E28 only."""

import copy
import hashlib
import json
import math
import uuid

from ...common.sexpr import a, children, first, read_sexpr, sexpr
from ..revision26 import router as aid
from ..revision26.layout import Layout
from .integrate_positive import LIB, ROOT, footprint, native_parts
from .repair import Router
from .terminals import ALL_TERMINALS

TARGETS = {
    "C39": (45, 7, 90, "B"),
    "C40": (43, 2, 0, "B"),
    "C42": (39, 8, 0, "B"),
    "C46": (132.3, 8, 0, "B"),
    "C48": (133.5, 17.6, 0, "B"),
    "C50": (38, 18.5, 0, "B"),
    "C52": (137.2, 18, 0, "B"),
    "R32": (106, 19, 0, "F"),
    "C72": (109.5, 11, 0, "F"),
    "R88": (109.5, 13.2, 0, "F"),
}


def main(targets=None, label="local-bypass-repair", drop_refs=(), via_pins=None):
    targets = TARGETS if targets is None else targets
    path = ROOT / "rail_disconnect.kicad_pcb"
    before = path.read_bytes()
    tree = read_sexpr(before.decode())
    parts = native_parts()
    by = {c["ref"]: c for c in parts}
    nets = {str(n[2]).lstrip("/"): int(n[1]) for n in children(tree, "net")}
    old = aid.Router(tree)
    oldpoints = [p["xy"] for ref in targets for p in old.by_ref[ref]]
    removed = []
    keep = []
    for node in tree:
        remove = False
        if isinstance(node, list) and node:
            if node[0] == "footprint":
                ref = next(p[2] for p in children(node, "property") if p[1] == "Reference")
                remove = ref in targets or ref in drop_refs
            elif node[0] in ("segment", "via"):
                keys = ("at",) if node[0] == "via" else ("start", "end")
                coords = [tuple(float(v) - 100 for v in first(node, k)[1:3]) for k in keys]
                remove = any(math.dist(p, q) < 0.015 for p in coords for q in oldpoints)
        if remove:
            removed.append(sexpr(node))
        else:
            keep.append(node)
    tree = keep
    poses = {}
    for ref, preferred in targets.items():
        # Placement is checked against actual fixed pads/courtyards and mounts.
        # Historical tracks/vias are locally ripped up below, never exempted.
        bare = [n for n in tree if not (isinstance(n, list) and n and n[0] in ("segment", "via"))]
        layout = Layout(bare, by, {}, LIB)
        layout.router = Router(bare)
        layout.bodies = []
        for fp in children(bare, "footprint"):
            name = next(p[2] for p in children(fp, "property") if p[1] == "Reference")
            side, box = layout.body(fp)
            layout.bodies.append((name, side, box))
            if name == "J4":
                layout.bodies.append((name + "_tails", "B", box))
        for name, (x, y, net) in ALL_TERMINALS.items():
            layout.bodies.append((name + "_access", "B", (x + 95, y + 95, x + 105, y + 105)))
        candidates = [preferred] + [
            (preferred[0] + dx * 0.5, preferred[1] + dy * 0.5, angle, preferred[3])
            for radius in range(1, 17)
            for dx, dy in (
                (radius, 0),
                (-radius, 0),
                (0, radius),
                (0, -radius),
                (radius, radius),
                (-radius, radius),
                (radius, -radius),
                (-radius, -radius),
            )
            for angle in (preferred[2], (preferred[2] + 90) % 180)
        ]
        for pose in candidates:
            fp = footprint(by[ref], pose, nets)
            if not layout.legal_body(ref, fp):
                continue
            trial = aid.Router([n for n in bare if isinstance(n, list) and n and n[0] == "net"] + [fp])
            test = copy.copy(layout)
            test.router = copy.copy(layout.router)
            test.router.geometry = list(layout.router.geometry) + list(trial.geometry)
            valid = True
            for pad in trial.pads:
                if via_pins is not None and ref in via_pins and pad["pin"] not in via_pins[ref]:
                    continue
                geom = test.router.geometry
                # E28 declares filled/capped flush via-in-pad processing. Same-
                # net SMD copper on either face is not a drill prohibition;
                # foreign copper, every existing hole and PTH reserve remains.
                test.router.geometry = [g for g in geom if g is not pad and g["net"] != "BULK_BODY_NOVIA" and not (g['kind']=='rect' and g['net']==pad['net'] and not g.get('through'))]
                if not test.free_via(pad["net"], pad["xy"]):
                    valid = False
                    break
                test.router.geometry = geom
            if valid:
                break
        else:
            (ROOT / f"generated/{label}-partial.kicad_pcb").write_text(sexpr(tree) + "\n")
            (ROOT / f"generated/{label}-partial.json").write_text(
                json.dumps(dict(placements=poses, failed=ref), indent=2) + "\n"
            )
            raise AssertionError((ref, "No legal local land/barrel placement"))
        points = [p["xy"] for p in trial.pads]
        result = []
        for node in tree:
            remove = False
            if isinstance(node, list) and node and node[0] in ("segment", "via"):
                keys = ("at",) if node[0] == "via" else ("start", "end")
                coords = [tuple(float(v) - 100 for v in first(node, k)[1:3]) for k in keys]
                remove = any(math.dist(p, q) < 1.25 for p in coords for q in points)
            if remove:
                removed.append(sexpr(node))
            else:
                result.append(node)
        tree = result + [fp]
        rt = Router(tree)
        for pad in rt.by_ref[ref]:
            if via_pins is not None and ref in via_pins and pad["pin"] not in via_pins[ref]:
                continue
            rt.via(pad["net"], pad["xy"])
        poses[ref] = pose
        print(ref, pose, flush=True)
    for i, node in enumerate(tree):
        if (
            isinstance(node, list)
            and node
            and node[0] in ("segment", "via", "zone")
            and not children(node, "uuid")
        ):
            node.append(
                [a("uuid"), a(str(uuid.uuid5(uuid.NAMESPACE_URL, f"rmx:E28:local-repair:{i}:{sexpr(node)}")))]
            )
    path.write_text(sexpr(tree) + "\n")
    (ROOT / f"generated/{label}.json").write_text(
        json.dumps(
            dict(
                before_sha256=hashlib.sha256(before).hexdigest(),
                after_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                placements=poses,
                removed_items=removed,
                physical_qualified=False,
            ),
            indent=2,
        )
        + "\n"
    )


if __name__ == "__main__":
    main()
