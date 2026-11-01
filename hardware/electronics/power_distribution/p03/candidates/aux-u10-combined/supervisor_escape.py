"""Coherent six-pad monitor fanout repair; native topology is unchanged.

A MON_VIN barrel caged the adjacent P19 terminal. Replace that one barrel with
explicit separated port escapes, preserving both divider force and ground ends.
Actual In1 paths remain physical-mask checked and must enter the new ground
extraction. No supply-regulator SET or switching trace may be displaced.
"""

import argparse
import gzip
import hashlib
import json
import math
from pathlib import Path

from ...common.sexpr import children, first, read_sexpr, sexpr
from .quiet_crossover import CORRIDORS, CrossoverRouter
from .route import coded, named
from .spec import ROOT

PORTS = [
    ("U25", "6", "P03_MON_VIN", (142.15, 8.95)),
    ("R309", "1", "P03_MON_VIN", (144.2, 15.3)),
    ("R308", "2", "P03_MON_VIN", (147.8, 4.7)),
    ("U25", "3", "P03_MON_P19", (142.15, 10.95)),
    ("R305", "1", "P03_MON_P19", (144.2, 13.7)),
]


def implement(root):
    pcb = root / "power_p03.kicad_pcb"
    raw = pcb.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    archive = root / "generated/history" / f"before-monitor-fanout-{digest[:16]}.pcb.gz"
    if not archive.exists():
        archive.write_bytes(gzip.compress(raw, mtime=0))
    tree = coded(read_sexpr(raw.decode()))
    names = {str(n[1]): str(n[2]).lstrip("/") for n in children(tree, "net")}
    removed_old = 0
    for v in list(children(tree, "via")):
        xy = tuple(float(x) - 100 for x in first(v, "at")[1:3])
        if names[str(first(v, "net")[1])] == "P03_MON_VIN" and math.dist(xy, (141.75, 11.15)) < 0.01:
            tree.remove(v)
            removed_old += 1
    assert removed_old == 1, "Exact original MON_VIN barrel missing"
    displaced = []
    ports = []
    for ref, pin, net, xy in PORTS:
        r = CrossoverRouter(tree)
        full = r.geometry
        r.geometry = [g for g in full if g["kind"] != "line"]
        assert r.safe_via(net, xy, clearance=0.16), (ref, "fixed geometry conflict")
        for obj in list(children(tree, "segment")):
            other = names[str(first(obj, "net")[1])]
            if other == net:
                continue
            a, b = [tuple(float(x) - 100 for x in first(obj, k)[1:3]) for k in ("start", "end")]
            dx, dy = b[0] - a[0], b[1] - a[1]
            t = (
                max(0, min(1, ((xy[0] - a[0]) * dx + (xy[1] - a[1]) * dy) / (dx * dx + dy * dy)))
                if dx or dy
                else 0
            )
            if math.dist(xy, (a[0] + t * dx, a[1] + t * dy)) < 0.46 + float(first(obj, "width")[1]) / 2:
                assert not any(q in other for q in ("_SW", "BOOT", "_FB", "_SET", "RMID")), other
                tree.remove(obj)
                displaced.append((other, obj, a, b))
        r = CrossoverRouter(tree)
        r.via(net, xy)
        source = next(p for p in r.by_ref[ref] if p["pin"] == pin)
        ok = r.connect(source, dict(net=net, xy=xy, layers=source["layers"]), 0.16)
        ports.append(dict(ref=ref, pin=pin, net=net, barrel_mm=xy, local_joined=ok))
        print("Monitor local escape", ref, pin, ok, flush=True)
    CORRIDORS.update({n: [(0.6, 0.6, 159.4, 44.4)] for n in ("P03_MON_VIN", "P03_MON_P19")})
    joins = []
    for net, pairs in {
        "P03_MON_VIN": [((142.15, 8.95), (144.2, 15.3)), ((144.2, 15.3), (147.8, 4.7))],
        "P03_MON_P19": [((142.15, 10.95), (144.2, 13.7)), ((144.2, 13.7), (146.125, 6.25))],
    }.items():
        for a, b in pairs:
            r = CrossoverRouter(tree)
            r.only_in1 = True
            r.max_search_nodes = 1000000
            ok = r.connect(dict(net=net, xy=a, layers=(1,)), dict(net=net, xy=b, layers=(1,)), 0.16)
            joins.append(dict(net=net, endpoints_mm=[a, b], joined=ok, routes=r.routes))
            print("Monitor In1 connection", net, ok, flush=True)
    pcb.write_text(sexpr(named(tree)) + "\n")
    (root / "generated/supervisor-escape.json").write_text(
        json.dumps(
            dict(
                before_pcb_sha256=digest,
                removed_original_barrels=removed_old,
                actual_ports=ports,
                interconnects=joins,
                displaced_transit_nets=[n for n, _, _, _ in displaced],
                physical_obstacle_masks_preserved=True,
                clearance_relaxed=False,
                ground_model_renewal_required=True,
                native_refill_parity_and_connectivity_required=True,
                noise_and_physical_qualified=False,
            ),
            indent=2,
        )
        + "\n"
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", type=Path, default=ROOT)
    implement(p.parse_args().root)
