"""Scratch-only timing-cap placement repair freeing real SSOP barrel access."""

import argparse
import gzip
import hashlib
import json
import math
from pathlib import Path

from ...common.placement import footprint_root, placed_footprint
from ...common.sexpr import children, first, read_sexpr, sexpr
from ...output_stage.check_placement import courtyard
from ...power_supply.place import overlap
from .route import PowerRouter, coded, named
from .spec import MOUNTS, ROOT

POSE = (151.5, 14, 90, "F")


def implement(root, cli, ref="C300", pose=POSE, superseded_barrels=None):
    pcb = root / "power_p03.kicad_pcb"
    raw = pcb.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    archive = root / "generated/history" / f"before-{ref.lower()}-placement-{digest[:16]}.pcb.gz"
    if not archive.exists():
        archive.write_bytes(gzip.compress(raw, mtime=0))
    tree = coded(read_sexpr(raw.decode()))
    r = PowerRouter(tree)
    fp = next(
        f
        for f in children(tree, "footprint")
        if any(p[1] == "Reference" and p[2] == ref for p in children(f, "property"))
    )
    part = next(p for p in json.loads((root / "components.json").read_text()) if p["ref"] == ref)
    lib, name = part["footprint"].split(":")
    part = dict(
        part, value=part["part"], mpn=part["part"], nets={p["number"]: p["net"] for p in part["pins"]}
    )
    new = placed_footprint(
        part, pose, footprint_root(str(cli)) / (lib + ".pretty") / (name + ".kicad_mod"), r.nets
    )
    box = [x - 100 for x in courtyard(new, "F.CrtYd")]
    used = [(f"mount{i}", [x - 3.7, y - 3.7, x + 3.7, y + 3.7]) for i, (x, y) in enumerate(MOUNTS)]
    for f in children(tree, "footprint"):
        if f is not fp and first(f, "layer")[1] == "F.Cu":
            used.append(
                (
                    next(p[2] for p in children(f, "property") if p[1] == "Reference"),
                    [x - 100 for x in courtyard(f, "F.CrtYd")],
                )
            )
    assert not any(overlap(box, b, 0.15) for _, b in used), [(n, b) for n, b in used if overlap(box, b, 0.15)]
    oldpads = r.by_ref[ref]
    tree.remove(fp)
    tree.append(new)
    pads = oldpads + PowerRouter(tree).by_ref[ref]
    removed = []
    for obj in list(children(tree, "segment")):
        if first(obj, "layer")[1] != "F.Cu":
            continue
        aa, bb = [tuple(float(v) - 100 for v in first(obj, k)[1:3]) for k in ("start", "end")]
        dx, dy = bb[0] - aa[0], bb[1] - aa[1]
        for p in pads:
            t = (
                max(0, min(1, ((p["xy"][0] - aa[0]) * dx + (p["xy"][1] - aa[1]) * dy) / (dx * dx + dy * dy)))
                if dx or dy
                else 0
            )
            if (
                math.dist(p["xy"], (aa[0] + t * dx, aa[1] + t * dy))
                < max(p["size"]) / 2 + 0.16 + float(first(obj, "width")[1]) / 2
            ):
                tree.remove(obj)
                removed.append("localFattachment")
                break
    # Superseded capacitor return and two remote ground-stitch barrels form an
    # actual all-layer cage. Remove these exact barrels only; SSOP ground must
    # still pass native connectivity via its retained alternate ground paths.
    old_barrels = (
        ({(146.95, 10), (147.25, 9.0875), (147.25, 11.25), (145.05, 10)} if ref == "C300" else set())
        if superseded_barrels is None
        else superseded_barrels
    )
    names = {str(n[1]): str(n[2]).lstrip("/") for n in children(tree, "net")}
    for v in list(children(tree, "via")):
        xy = tuple(round(float(x) - 100, 6) for x in first(v, "at")[1:3])
        if xy in old_barrels:
            assert names[str(first(v, "net")[1])] in {"AGND", "P03_MON_TIMER"}
            tree.remove(v)
            removed.append(dict(barrel=xy, net=names[str(first(v, "net")[1])]))
    pcb.write_text(sexpr(named(tree)) + "\n")
    (root / f"generated/{ref.lower()}-layout.json").write_text(
        json.dumps(
            dict(
                before_pcb_sha256=digest,
                new_pose_mm=pose,
                removed=removed,
                capacitor_value_and_mpn_unchanged=True,
                clearance_relaxed=False,
                native_routing_and_assembly_recheck_required=True,
                physical_qualified=False,
            ),
            indent=2,
        )
        + "\n"
    )
    print("Actual local component candidate moved", ref, pose, "native checks required", flush=True)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", type=Path, default=ROOT)
    p.add_argument("--kicad-cli", type=Path, required=True)
    args = p.parse_args()
    implement(args.root, args.kicad_cli)
