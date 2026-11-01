"""Correct coupling-capacitor port order without expanding its physical envelope."""

import argparse
import copy
import gzip
import hashlib
import json
import math
from pathlib import Path

from ...common.placement import footprint_root, placed_footprint
from ...common.sexpr import children, first, read_sexpr, sexpr
from ...output_stage.check_placement import courtyard, transform
from .route import coded, named
from .spec import ROOT


def implement(root, cli):
    path = root / "power_p03.kicad_pcb"
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    archive = root / "generated/history" / f"before-c63-order-{digest[:16]}.kicad_pcb.gz"
    if not archive.exists():
        archive.write_bytes(gzip.compress(raw, mtime=0))
    tree = coded(read_sexpr(raw.decode()))
    original_fp = next(
        f
        for f in children(tree, "footprint")
        if any(p[1:3] == ["Reference", "C63"] for p in children(f, "property"))
    )
    before = copy.deepcopy(original_fp)
    old_box = courtyard(before, "F.CrtYd")
    # Native saved pad angles are absolute. Rebuild from the actual library
    # rather than edit only the footprint angle and leave stale pad rotations.
    component = next(c for c in json.loads((root / "components.json").read_text()) if c["ref"] == "C63")
    lib, name = component["footprint"].split(":")
    library = footprint_root(str(cli)) / (lib + ".pretty") / (name + ".kicad_mod")
    at = first(before, "at")
    component = dict(
        component,
        value=component["part"],
        mpn=component["part"],
        nets={p["number"]: p["net"] for p in component["pins"]},
    )
    nets = {str(n[2]).lstrip("/"): int(n[1]) for n in children(tree, "net")}
    fp = placed_footprint(component, (float(at[1]) - 100, float(at[2]) - 100, 270, "F"), library, nets)
    tree.remove(original_fp)
    tree.append(fp)
    assert all(abs(x - y) < 1e-6 for x, y in zip(old_box, courtyard(fp, "F.CrtYd"))), (
        "Physical envelope changed"
    )
    pins = [p for p in children(fp, "pad") if children(p, "net")]
    positions = [transform(fp, first(p, "at")[1:3]) for p in pins]
    names = {str(n[1]): str(n[2]).lstrip("/") for n in children(tree, "net")}
    actual = {
        str(p[1]): dict(net=names[str(first(p, "net")[1])], xy_mm=list(transform(fp, first(p, "at")[1:3])))
        for p in pins
    }
    assert actual["1"]["net"] == "LO_N_SW" and actual["2"]["net"] == "LO_CUK_NODE"
    assert actual["1"]["xy_mm"][1] < actual["2"]["xy_mm"][1], "Switch must escape toward upper IC pin"
    removed = []
    for obj in list(tree):
        if not isinstance(obj, list) or not obj or obj[0] not in {"segment", "via"}:
            continue
        if names[str(first(obj, "net")[1])] not in {"LO_N_SW", "LO_CUK_NODE"}:
            continue
        if obj[0] == "via":
            point = tuple(map(float, first(obj, "at")[1:3]))
            near = any(math.dist(point, p) < 2.0 for p in positions)
        else:
            ax, ay = map(float, first(obj, "start")[1:3])
            bx, by = map(float, first(obj, "end")[1:3])
            dx, dy = bx - ax, by - ay
            near = False
            for x, y in positions:
                t = max(0, min(1, ((x - ax) * dx + (y - ay) * dy) / (dx * dx + dy * dy))) if dx or dy else 0
                near |= math.hypot(x - ax - t * dx, y - ay - t * dy) < 2.0
        if near:
            tree.remove(obj)
            removed.append(obj[0])
    path.write_text(sexpr(named(tree)) + "\n")
    (root / "generated/cuk-port-order.json").write_text(
        json.dumps(
            dict(
                before_pcb_sha256=digest,
                reference="C63",
                prior_angle_deg=float(first(before, "at")[3]),
                adopted_angle_deg=270,
                unchanged_courtyard_mm=old_box,
                actual_native_pads=actual,
                removed_local_old_node_copper=removed,
                native_refill_parity_and_hot_loop_verification_required=True,
                switching_and_thermal_qualified=False,
            ),
            indent=2,
        )
        + "\n"
    )
    print(
        "C63 switch/coupling port order corrected; same physical courtyard, native closure required",
        flush=True,
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", type=Path, default=ROOT)
    p.add_argument("--kicad-cli", type=Path, required=True)
    args = p.parse_args()
    implement(args.root, args.kicad_cli)
