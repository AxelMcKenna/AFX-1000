"""Explicit local fanouts for the separate front-side U10 thermal candidate.

Only actual intersecting traces are displaced; fixed pads and eight direct live
EP barrels remain intact. Each removed original object is retained for audit.
New foreign-barrel voids require a renewed actual-copper thermal/ground model.
"""

import argparse
import gzip
import hashlib
import json
import math
import types
from pathlib import Path

from ...common.sexpr import children, first, read_sexpr, sexpr
from . import route
from .route import PowerRouter, coded, named


def implement(root):
    route.STEP = 0.05
    route.mask_globals["STEP"] = 0.05
    PowerRouter.connect = types.FunctionType(
        route.Router.connect.__code__, dict(route.Router.connect.__globals__, STEP=0.05)
    )
    pcb = root / "power_p03.kicad_pcb"
    raw = pcb.read_bytes()
    before = hashlib.sha256(raw).hexdigest()
    (root / "generated/history" / ("before-u10-access-" + before[:16] + ".pcb.gz")).write_bytes(
        gzip.compress(raw, mtime=0)
    )
    tree = coded(read_sexpr(raw.decode()))
    nets = {str(n[1]): str(n[2]).lstrip("/") for n in children(tree, "net")}
    removed = []
    staged = [("AGND", (92, 29.3)), ("N19_RMID", (95.9, 27.7))]
    for net, xy in staged:
        r = PowerRouter(tree)
        geometry = r.geometry
        r.geometry = [g for g in geometry if g["kind"] != "line"]
        assert r.safe_via(net, xy, diameter=0.55, clearance=0.165)
        for obj in list(children(tree, "segment")):
            other = nets[str(first(obj, "net")[1])]
            if other == net:
                continue
            a, b = [tuple(float(q) - 100 for q in first(obj, k)[1:3]) for k in ("start", "end")]
            dx, dy = b[0] - a[0], b[1] - a[1]
            t = (
                max(0, min(1, ((xy[0] - a[0]) * dx + (xy[1] - a[1]) * dy) / (dx * dx + dy * dy)))
                if dx or dy
                else 0
            )
            if (
                math.dist(xy, (a[0] + t * dx, a[1] + t * dy))
                < 0.275 + 0.165 + float(first(obj, "width")[1]) / 2
            ):
                assert "SW" not in other and "BOOT" not in other, other
                removed.append(
                    dict(
                        net=other,
                        exact_sexpr=sexpr(obj),
                        layer=first(obj, "layer")[1],
                        width_mm=float(first(obj, "width")[1]),
                        endpoints_mm=[a, b],
                    )
                )
                tree.remove(obj)
        r = PowerRouter(tree)
        assert r.safe_via(net, xy, diameter=0.55, clearance=0.165)
        tree.append(
            read_sexpr(
                f'(via(at {100 + xy[0]} {100 + xy[1]})(size .55)(drill .20)(layers "F.Cu" "B.Cu")(free yes)(net {r.nets[net]}))'
            )
        )
    records = []
    for net, xy in staged:
        r = PowerRouter(tree)
        ref, pin = ("U10", "3") if net == "AGND" else ("R34", "2")
        source = next(p for p in r.by_ref[ref] if p["pin"] == pin)
        r.max_search_nodes = 1000000
        ok = r.connect(source, dict(net=net, xy=xy, layers=(0 if net == "AGND" else 5,)), 0.16)
        records.append(dict(net=net, local_connected=ok, routes=r.routes))
        print("U10 actual local fanout", net, ok, flush=True)
    pcb.write_text(sexpr(named(tree)) + "\n")
    (root / "generated/u10-access.json").write_text(
        json.dumps(
            dict(
                before_pcb_sha256=before,
                staged_barrels=staged,
                land_mm=0.55,
                finished_hole_mm=0.20,
                displaced_original_objects=removed,
                local_connections=records,
                clearance_relaxed=False,
                requires_native_reclosure_and_actual_thermal_ground_reextraction=True,
                physical_qualified=False,
            ),
            indent=2,
        )
        + "\n"
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", type=Path, required=True)
    implement(p.parse_args().root)
