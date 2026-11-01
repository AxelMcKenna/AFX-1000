"""Local circuit reconstruction after the isolated nine-EP U102 thermal merge.

All routes join actual original pins/barrels. The feedback source uses a second
filled/capped .55/.20 signal VIP; no switching/SET trace or foreign transit is
removed. The filled copper and resulting heat path require fresh extraction.
"""

import argparse
import gzip
import hashlib
import json
import types
from pathlib import Path

from ...common.sexpr import read_sexpr, sexpr
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
    archive = root / "generated/history" / f"before-u102-local-repair-{digest[:16]}.pcb.gz"
    if not archive.exists():
        archive.write_bytes(gzip.compress(raw, mtime=0))
    tree = coded(read_sexpr(raw.decode()))
    r = PowerRouter(tree)
    net = "AUX_FB"
    vip = (24.1, 19.675)
    assert r.safe_via(net, vip, diameter=0.55, clearance=0.16)
    tree.append(
        read_sexpr(
            f'(via (at {vip[0] + 100} {vip[1] + 100}) (size .55) (drill .20) (layers "F.Cu" "B.Cu") (free yes) (net {r.nets[net]}))'
        )
    )
    # Explicit short local capacitor return into the actual B spreading field.
    r = PowerRouter(tree)
    r.path("AGND", 5, [(29, 24.5), (29, 23.2)], 0.35)
    records = []

    def pad(ref, pin):
        return next(p for p in r.by_ref[ref] if p["pin"] == pin)

    def barrel(net, xy):
        return dict(net=net, xy=xy, layers=tuple(range(6)))

    plan = [
        (pad("R130", "2"), barrel("AUX_FB", vip), 0.16),
        (pad("R109", "1"), barrel("AUX_FB", vip), 0.16),
        (pad("R110", "1"), barrel("V2V5_AUX", (27.9, 15.9)), 0.16),
        (barrel("V2V5_AUX", (23.125, 21.625)), pad("J106", "1"), 0.25),
        (pad("R110", "2"), barrel("POWER_READY", (29.5, 11.75)), 0.16),
        (barrel("POWER_READY", (29.5, 11.75)), barrel("POWER_READY", (37.625, 13)), 0.16),
        (pad("C109", "1"), barrel("FAST_OV_REF", (30.25, 23.125)), 0.16),
        (pad("U101", "7"), barrel("INPUT_OV", (19.75, 8.75)), 0.16),
        (pad("R104", "1"), barrel("INPUT_OV", (19.75, 8.75)), 0.16),
        (pad("D102", "1"), barrel("INPUT_OV", (19.75, 8.75)), 0.16),
    ]
    for a, b, w in plan:
        r = PowerRouter(tree)
        r.max_search_nodes = 350000
        ok = r.connect(a, b, w)
        records.append(
            dict(net=a["net"], source_mm=a["xy"], target_mm=b["xy"], width_mm=w, joined=ok, routes=r.routes)
        )
        print("U102 local circuit", a["net"], a["xy"], b["xy"], ok, flush=True)
    pcb.write_text(sexpr(named(tree)) + "\n")
    (root / "generated/u102-local-repair.json").write_text(
        json.dumps(
            dict(
                before_pcb_sha256=digest,
                feedback_vip=dict(
                    ref="U102",
                    pin="2",
                    net=net,
                    land_mm=0.55,
                    finished_bore_mm=0.20,
                    required_filled_capped_and_flat=True,
                ),
                actual_local_connections=records,
                foreign_copper_displaced=False,
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
