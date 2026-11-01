"""Author bounded, same-face local AUX loops, preserving exact displaced tracks.

A long A* detour is not accepted as local decoupling. Fixed foreign pads/barrels
are never removed to force a loop; the actual native DRC remains authoritative.
"""

import argparse
import hashlib
import json
import math
from pathlib import Path

from ...common.sexpr import children, first, read_sexpr, sexpr
from .route import PowerRouter, coded, named

LOOPS = [
    (
        "C106",
        "1",
        "1",
        "V2V5_AUX",
        0.25,
        [(24.1, 19.025), (23, 19.025), (23, 22.8), (24.625, 22.8), (24.625, 23.6)],
    ),
    (
        "C113",
        "1",
        "8",
        "VIN_IC",
        0.25,
        [
            (29.95, 16.5),
            (30.5, 16.5),
            (30.5, 17.5),
            (30.2, 17.85),
            (29.875, 18.25),
            (29.6, 18.55),
            (29.6, 19.025),
            (28.4, 19.025),
        ],
    ),
    (
        "C113",
        "2",
        "4",
        "AGND",
        0.25,
        [
            (28.05, 16.5),
            (27.1, 16.5),
            (27.1, 18),
            (26.8, 18.8),
            (26.25, 20),
            (26.25, 21.8),
            (24.1, 21.8),
            (24.1, 20.975),
        ],
    ),
    (
        "C110",
        "1",
        "7",
        "AUX_START_DELAY",
        0.16,
        [(29.3, 22.625), (29.6, 22.625), (29.6, 19.675), (28.4, 19.675)],
    ),
]


def point_distance(p, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    t = max(0, min(1, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / (dx * dx + dy * dy))) if dx or dy else 0
    return math.dist(p, (a[0] + t * dx, a[1] + t * dy))


def line_distance(a, b, c, d):
    def cross(p, q, r):
        return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])

    if cross(a, b, c) * cross(a, b, d) < 0 and cross(c, d, a) * cross(c, d, b) < 0:
        return 0
    return min(
        point_distance(a, c, d), point_distance(b, c, d), point_distance(c, a, b), point_distance(d, a, b)
    )


def rect_distance(a, b, g):
    x, y = g["xy"]
    w, h = [s / 2 for s in g["size"]]
    if any(x - w <= p[0] <= x + w and y - h <= p[1] <= y + h for p in (a, b)):
        return 0
    v = [(x - w, y - h), (x + w, y - h), (x + w, y + h), (x - w, y + h)]
    return min(line_distance(a, b, p, q) for p, q in zip(v, v[1:] + v[:1]))


def implement(root):
    pcb = root / "power_p03.kicad_pcb"
    raw = pcb.read_bytes()
    tree = coded(read_sexpr(raw.decode()))
    r = PowerRouter(tree)
    names = {str(n[1]): str(n[2]).lstrip("/") for n in children(tree, "net")}
    # Reject and discard the exploratory forty-mm OUT detour, never call it a
    # successful local capacitor connection merely because it joins two pins.
    rejected = []
    for obj in list(children(tree, "segment")):
        if names[str(first(obj, "net")[1])] == "V2V5_AUX" and not children(obj, "uuid"):
            rejected.append(sexpr(obj))
            tree.remove(obj)
    displaced = []
    records = []
    for ref, pin, upin, net, width, points in LOOPS:
        r = PowerRouter(tree)
        blockers = []
        for g in r.geometry:
            if g["net"] == net or 0 not in g["layers"] or g["kind"] == "line":
                continue
            for a, b in zip(points, points[1:]):
                distance = (
                    point_distance(g["xy"], a, b) - g["radius"]
                    if g["kind"] == "via"
                    else rect_distance(a, b, g)
                )
                if distance < width / 2 + 0.16 - 1e-8:
                    blockers.append(g)
                    break
        assert not blockers, (ref, pin, "Fixed geometry obstructs proposed local loop", blockers)
        for obj in list(children(tree, "segment")):
            other = names[str(first(obj, "net")[1])]
            if first(obj, "layer")[1] != "F.Cu" or other == net:
                continue
            c, d = [tuple(float(q) - 100 for q in first(obj, k)[1:3]) for k in ["start", "end"]]
            if any(
                line_distance(a, b, c, d) < width / 2 + float(first(obj, "width")[1]) / 2 + 0.16 - 1e-8
                for a, b in zip(points, points[1:])
            ):
                assert "SW" not in other and "BOOT" not in other, other
                displaced.append(dict(net=other, exact_sexpr=sexpr(obj), for_loop=[ref, pin]))
                tree.remove(obj)
        r = PowerRouter(tree)
        r.path(net, 0, points, width)
        records.append(
            dict(
                cap=ref,
                cap_pin=pin,
                regulator_pin=upin,
                net=net,
                layer="F.Cu",
                width_mm=width,
                points_mm=points,
                centreline_length_mm=sum(math.dist(a, b) for a, b in zip(points, points[1:])),
                through_via_in_local_path=False,
            )
        )
    pcb.write_text(sexpr(named(tree)) + "\n")
    (root / "generated/aux-bounded-front-loops.json").write_text(
        json.dumps(
            dict(
                before_pcb_sha256=hashlib.sha256(raw).hexdigest(),
                explicit_local_front_paths=records,
                rejected_nonlocal_OUT_detour=rejected,
                displaced_source_tracks=displaced,
                fixed_pads_and_vias_removed=False,
                native_loop_integrity_and_stability_qualification_required=True,
                physical_qualified=False,
            ),
            indent=2,
        )
        + "\n"
    )
    print("Actual bounded same-face AUX paths authored", len(records), flush=True)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", type=Path, required=True)
    implement(p.parse_args().root)
