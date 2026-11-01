"""Final two actual control connections in the isolated U102 thermal merge."""

import argparse
import gzip
import hashlib
import json
import math
import types
from pathlib import Path

from ...common.sexpr import children, first, read_sexpr, sexpr
from . import route
from .quiet_crossover import CORRIDORS, CrossoverRouter
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
    archive = root / "generated/history" / f"before-u102-last-controls-{digest[:16]}.pcb.gz"
    if not archive.exists():
        archive.write_bytes(gzip.compress(raw, mtime=0))
    tree = coded(read_sexpr(raw.decode()))
    r = PowerRouter(tree)
    ov = (22.55, 16.45)
    assert r.safe_via("INPUT_OV", ov, clearance=0.16)
    r.via("INPUT_OV", ov)
    r.max_search_nodes = 400000
    source = next(p for p in r.by_ref["U101"] if p["pin"] == "7")
    local = r.connect(source, dict(net="INPUT_OV", xy=ov, layers=(0,)), 0.16)
    manual = []
    if not local:
        manual = [source["xy"], (24.5, 15.2), (22.55, 15.2), ov]
        r.path("INPUT_OV", 0, manual, 0.16)
    remote = r.connect(
        dict(net="INPUT_OV", xy=ov, layers=tuple(range(6))),
        dict(net="INPUT_OV", xy=(19.75, 8.75), layers=tuple(range(6))),
        0.16,
    )
    if remote:
        names = {str(n[1]): str(n[2]).lstrip("/") for n in children(tree, "net")}
        for v in list(children(tree, "via")):
            xy = tuple(float(x) - 100 for x in first(v, "at")[1:3])
            if names[str(first(v, "net")[1])] == "INPUT_OV" and math.dist(xy, (25, 16.5)) < 1e-6:
                tree.remove(v)  # Rejected under-C105 route is no longer needed.
    print("Guard OV actual left-corner escape", local, remote, "manual candidate", bool(manual), flush=True)
    r = PowerRouter(tree)
    tp = next(p for p in r.by_ref["J103"] if p["pin"] == "2")
    reuse = any(
        g["kind"] == "via" and g["net"] == "POWER_READY" and math.dist(g["xy"], tp["xy"]) < 1e-6
        for g in r.geometry
    )
    assert reuse or r.safe_via("POWER_READY", tp["xy"], clearance=0.16)
    if not reuse:
        r.via("POWER_READY", tp["xy"])
    CORRIDORS["POWER_READY"] = [(0.6, 0.6, 159.4, 44.4)]
    pg = False
    pg_routes = []
    for layer in (1, 4):
        r = CrossoverRouter(tree)
        r.only_in1 = True
        r.crossover_layer = layer
        r.max_search_nodes = 1000000
        pg = r.connect(
            dict(net="POWER_READY", xy=tp["xy"], layers=(layer,)),
            dict(net="POWER_READY", xy=(29.5, 11.75), layers=(layer,)),
            0.16,
        )
        if pg:
            pg_routes = r.routes
            break
    print("Guard PG actual probe-to-source", pg, flush=True)
    pcb.write_text(sexpr(named(tree)) + "\n")
    (root / "generated/u102-last-controls.json").write_text(
        json.dumps(
            dict(
                before_pcb_sha256=digest,
                actual_input_OV_barrel_mm=ov,
                OV_local_astar_joined=local,
                OV_manual_preview_mm=manual,
                OV_remote_joined=remote,
                POWER_READY_probe_joined=pg,
                POWER_READY_routes=pg_routes,
                foreign_copper_removed=False,
                clearance_relaxed=False,
                native_refill_and_connectivity_required=True,
                current_thermal_ground_noise_and_physical_qualified=False,
            ),
            indent=2,
        )
        + "\n"
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", type=Path, required=True)
    implement(p.parse_args().root)
