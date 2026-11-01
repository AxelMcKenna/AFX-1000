"""Release the guard OV escape by placing the moved AUX pullup to the left.

The .55/.20 OV barrel is outside the C105 body. All actual source nodes, capacitor
locations and thermal EPs are retained. R110 remains north of the TIM cutout.
"""

import argparse
import gzip
import hashlib
import json
import math
import types
from pathlib import Path

from ...common.placement import footprint_root, placed_footprint
from ...common.sexpr import children, first, read_sexpr, sexpr
from . import route
from .route import PowerRouter, coded, named


def implement(root, cli):
    route.STEP = 0.05
    route.mask_globals["STEP"] = 0.05
    PowerRouter.connect = types.FunctionType(
        route.Router.connect.__code__, dict(route.Router.connect.__globals__, STEP=0.05)
    )
    pcb = root / "power_p03.kicad_pcb"
    raw = pcb.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    archive = root / "generated/history" / f"before-u102-guard-access-{digest[:16]}.pcb.gz"
    if not archive.exists():
        archive.write_bytes(gzip.compress(raw, mtime=0))
    tree = coded(read_sexpr(raw.decode()))
    r = PowerRouter(tree)
    names = {str(n[1]): str(n[2]).lstrip("/") for n in children(tree, "net")}
    old = next(
        f
        for f in children(tree, "footprint")
        if any(p[1:3] == ["Reference", "R110"] for p in children(f, "property"))
    )
    c = next(p for p in json.loads((root / "components.json").read_text()) if p["ref"] == "R110")
    lib, fp = c["footprint"].split(":")
    c = dict(c, value=c["part"], mpn=c["part"], nets={p["number"]: p["net"] for p in c["pins"]})
    new = placed_footprint(
        c, (22.25, 14.7, 0, "B"), footprint_root(str(cli)) / (lib + ".pretty") / (fp + ".kicad_mod"), r.nets
    )
    tree.remove(old)
    tree.append(new)
    removed = []
    for obj in list(children(tree, "segment")):
        net = names[str(first(obj, "net")[1])]
        z = first(obj, "layer")[1]
        a, b = [tuple(float(v) - 100 for v in first(obj, k)[1:3]) for k in ("start", "end")]
        if net == "INPUT_OV" and z == "F.Cu" and all(22 <= p[0] <= 25 and 14 <= p[1] <= 17 for p in [a, b]):
            tree.remove(obj)
            removed.append(net)
            continue
        if (
            net in {"V2V5_AUX", "POWER_READY"}
            and z == "B.Cu"
            and min(a[0], b[0]) < 30.8
            and max(a[0], b[0]) > 20
            and min(a[1], b[1]) < 16.5
            and max(a[1], b[1]) > 13.7
        ):
            tree.remove(obj)
            removed.append(net)
    # The old failed corner route's redundant barrel is not an acceptance path.
    for v in list(children(tree, "via")):
        xy = tuple(float(x) - 100 for x in first(v, "at")[1:3])
        if names[str(first(v, "net")[1])] == "INPUT_OV" and math.dist(xy, (22.55, 16.45)) < 1e-6:
            tree.remove(v)
    r = PowerRouter(tree)
    ov = (24.2, 15.3)
    assert any(
        g["kind"] == "via" and g["net"] == "INPUT_OV" and math.dist(g["xy"], ov) < 1e-6 for g in r.geometry
    ) or r.safe_via("INPUT_OV", ov, diameter=0.55, clearance=0.16 - 1e-10), (
        "New OV barrel conflicts with actual copper"
    )
    if not any(
        g["kind"] == "via" and g["net"] == "INPUT_OV" and math.dist(g["xy"], ov) < 1e-6 for g in r.geometry
    ):
        tree.append(
            read_sexpr(
                f'(via (at 124.2 115.3) (size .55) (drill .20) (layers "F.Cu" "B.Cu") (free yes) (net {r.nets["INPUT_OV"]}))'
            )
        )
    r = PowerRouter(tree)
    run = (28.5, 14.6)
    assert r.safe_via("POWER_RUN", run, clearance=0.16 - 1e-10)
    r.via("POWER_RUN", run)
    r = PowerRouter(tree)
    r.max_search_nodes = 500000

    def pad(ref, pin):
        return next(p for p in r.by_ref[ref] if p["pin"] == pin)

    def barrel(net, xy):
        return dict(net=net, xy=xy, layers=tuple(range(6)))

    records = []
    for a, b in [
        (pad("U101", "12"), dict(net="POWER_RUN", xy=run, layers=(0,))),
        (pad("U101", "7"), dict(net="INPUT_OV", xy=ov, layers=(0,))),
        (barrel("INPUT_OV", ov), barrel("INPUT_OV", (19.75, 8.75))),
        (pad("R110", "1"), barrel("V2V5_AUX", (22.125, 19.0))),
        (pad("R110", "2"), barrel("POWER_READY", (29.5, 11.75))),
    ]:
        ok = r.connect(a, b, 0.16)
        records.append(dict(net=a["net"], source_mm=a["xy"], target_mm=b["xy"], joined=ok, routes=r.routes))
        print("Final guard access", a["net"], ok, flush=True)
    pcb.write_text(sexpr(named(tree)) + "\n")
    (root / "generated/u102-guard-access.json").write_text(
        json.dumps(
            dict(
                before_pcb_sha256=digest,
                new_R110_B_pose_mm=[22.25, 14.7, 0],
                OV_barrel_mm=ov,
                land_mm=0.55,
                finished_bore_mm=0.20,
                removed_only_affected_control_nodes=removed,
                connections=records,
                clearance_relaxed=False,
                all_nine_thermal_EP_barrels_retained=True,
                native_refill_and_connectivity_required=True,
                thermal_ground_fit_noise_and_physical_qualified=False,
            ),
            indent=2,
        )
        + "\n"
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", type=Path, required=True)
    p.add_argument("--kicad-cli", type=Path, required=True)
    args = p.parse_args()
    implement(args.root, args.kicad_cli)
