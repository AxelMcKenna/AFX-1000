"""Finish guard/monitor connections around the actual merged U102 field.

A small capped signal barrel fits between the existing C105 pads at .175 mm
nominal clearance. Move only the AUX pullup spur above that passive to release
its actual barrel window; the original supply and resistor nodes are retained.
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
    digest = hashlib.sha256(raw).hexdigest()
    archive = root / "generated/history" / f"before-u102-final-escape-{digest[:16]}.pcb.gz"
    if not archive.exists():
        archive.write_bytes(gzip.compress(raw, mtime=0))
    tree = coded(read_sexpr(raw.decode()))
    names = {str(n[1]): str(n[2]).lstrip("/") for n in children(tree, "net")}
    via = (25, 16.5)
    removed = []
    for obj in list(children(tree, "segment")):
        if names[str(first(obj, "net")[1])] != "V2V5_AUX" or first(obj, "layer")[1] != "B.Cu":
            continue
        a, b = [tuple(float(v) - 100 for v in first(obj, k)[1:3]) for k in ("start", "end")]
        dx, dy = b[0] - a[0], b[1] - a[1]
        t = (
            max(0, min(1, ((via[0] - a[0]) * dx + (via[1] - a[1]) * dy) / (dx * dx + dy * dy)))
            if dx or dy
            else 0
        )
        if math.dist(via, (a[0] + t * dx, a[1] + t * dy)) < 0.275 + 0.16 + float(first(obj, "width")[1]) / 2:
            tree.remove(obj)
            removed.append([a, b])
    r = PowerRouter(tree)
    assert r.safe_via("INPUT_OV", via, diameter=0.55, clearance=0.16)
    tree.append(
        read_sexpr(
            f'(via (at 125 116.5) (size .55) (drill .20) (layers "F.Cu" "B.Cu") (free yes) (net {r.nets["INPUT_OV"]}))'
        )
    )
    r = PowerRouter(tree)
    r.max_search_nodes = 400000

    def pad(ref, pin):
        return next(p for p in r.by_ref[ref] if p["pin"] == pin)

    def barrel(net, xy):
        return dict(net=net, xy=xy, layers=tuple(range(6)))

    records = []
    aux = r.connect(pad("R110", "1"), barrel("V2V5_AUX", (27.9, 15.9)), 0.16)
    records.append(dict(net="V2V5_AUX", pullup_spur_joined=aux, routes=r.routes))
    print("AUX pullup spur", aux, flush=True)
    r = PowerRouter(tree)
    r.max_search_nodes = 400000
    ovlocal = r.connect(pad("U101", "7"), dict(net="INPUT_OV", xy=via, layers=(0,)), 0.16)
    ovremote = r.connect(barrel("INPUT_OV", via), barrel("INPUT_OV", (19.75, 8.75)), 0.16)
    records.append(dict(net="INPUT_OV", local_joined=ovlocal, remote_joined=ovremote, routes=r.routes))
    print("Guard OV escape", ovlocal, ovremote, flush=True)
    r = PowerRouter(tree)
    r.max_search_nodes = 600000
    tp = pad("J103", "2")
    assert r.safe_via("POWER_READY", tp["xy"], clearance=0.16)
    r.via("POWER_READY", tp["xy"])
    pg = r.connect(barrel("POWER_READY", tp["xy"]), barrel("POWER_READY", (29.5, 11.75)), 0.16)
    records.append(dict(net="POWER_READY", probe_joined=pg, routes=r.routes))
    print("Guard PG probe", pg, flush=True)
    pcb.write_text(sexpr(named(tree)) + "\n")
    (root / "generated/u102-final-escape.json").write_text(
        json.dumps(
            dict(
                before_pcb_sha256=digest,
                under_C105_signal_via=dict(
                    net="INPUT_OV",
                    at_mm=via,
                    land_mm=0.55,
                    finished_bore_mm=0.20,
                    nominal_adjacent_pad_clearance_mm=0.175,
                ),
                relocated_same_node_aux_spur_segments_mm=removed,
                connections=records,
                cap_planarization_and_assembly_required=True,
                foreign_copper_removed=False,
                clearance_relaxed=False,
                native_refill_and_connectivity_required=True,
                thermal_ground_noise_and_physical_qualified=False,
            ),
            indent=2,
        )
        + "\n"
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", type=Path, required=True)
    implement(p.parse_args().root)
