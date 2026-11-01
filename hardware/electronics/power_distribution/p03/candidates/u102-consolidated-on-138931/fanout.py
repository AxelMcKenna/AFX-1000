"""Deliberate buck signal escape repair; every resulting route needs native DRC.

This reworks obstructing pre-existing copper and records its prior snapshot.
It preserves the right-hand switching/PGND region and all U13 direct EP vias.
"""

import gzip
import hashlib
import json
import math

from ...common.sexpr import first, read_sexpr, sexpr
from .route import OUT, ROOT, PowerRouter, coded, copper_geometry, named


def implement():
    p = ROOT / "power_p03.kicad_pcb"
    raw = p.read_bytes()
    (OUT / "history/before-buck-fanout.kicad_pcb.gz").write_bytes(gzip.compress(raw, mtime=0))
    tree = coded(read_sexpr(raw.decode()))
    poses = {"U20": (47, 13), "U23": (135, 28)}
    removed = []
    for o in list(tree):
        if not isinstance(o, list) or not o or o[0] not in {"segment", "via"}:
            continue
        points = (
            [list(map(float, first(o, "at")[1:3]))]
            if o[0] == "via"
            else [list(map(float, first(o, t)[1:3])) for t in ("start", "end")]
        )
        for cx, cy in poses.values():
            # Clear actual escape lane, preserving right-hand power/PGND path.
            x0, x1, y0, y1 = cx - 5.0 + 100, cx + 0.8 + 100, cy - 4.5 + 100, cy + 6.0 + 100
            if (
                min(q[0] for q in points) <= x1
                and max(q[0] for q in points) >= x0
                and min(q[1] for q in points) <= y1
                and max(q[1] for q in points) >= y0
            ):
                removed.append(dict(geometry=copper_geometry(o), reason="buck fine-pin escape corridor"))
                tree.remove(o)
                break
    r = PowerRouter(tree)
    r.max_search_nodes = 5000
    records = []
    for ref, (cx, cy) in poses.items():
        for number, dx, dy in [
            ("1", -1.2125, -3.0),
            ("2", -4, -0.5),
            ("3", -3, 0),
            ("4", -4.5, 0.5),
            ("6", -2.5, 1.5),
            ("7", 0.5, 5.75),
            ("14", -0.7, -4),
            ("13", -0.2, -3),
        ]:
            pads = [p for p in r.by_ref[ref] if p["pin"] == number and p["layers"]]
            pad = min(pads, key=lambda p: math.dist(p["xy"], (cx + dx, cy + dy)))
            end = (cx + dx, cy + dy)
            candidates = sorted(
                (
                    (cx + i * 0.25, cy + j * 0.25)
                    for i in range(-22, 5)
                    for j in range(-20, 25)
                    if r.safe_via(pad["net"], (cx + i * 0.25, cy + j * 0.25))
                ),
                key=lambda xy: math.dist(xy, end) + math.dist(xy, pad["xy"]) * 0.5,
            )
            chosen = None
            for candidate in candidates[:50]:
                if r.connect(pad, dict(net=pad["net"], xy=candidate, layers=(0,)), 0.16):
                    chosen = candidate
                    break
            if chosen is None:
                raise ValueError((ref, number, "surface escape blocked", end, candidates[:3]))
            end = chosen
            r.via(pad["net"], end)
            records.append(dict(ref=ref, pin=number, net=pad["net"], via_mm=end))
    p.write_text(sexpr(named(tree)) + "\n")
    (OUT / "buck-fanout-repair.json").write_text(
        json.dumps(
            dict(
                prior_sha256=hashlib.sha256(raw).hexdigest(),
                removed_copper=removed,
                implemented_fanouts=records,
                physical_qualified=False,
            ),
            indent=2,
        )
        + "\n"
    )
    print("fanout", len(records), "ripup", len(removed))


if __name__ == "__main__":
    implement()
