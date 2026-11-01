"""Actual six-pin Schmitt and separate HF/VIN bypass repair, pending native closure."""

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
from .board import valid_box
from .route import PowerRouter, coded, named
from .spec import MOUNTS, ROOT, THERMAL_REGIONS

POSES = {
    "U26": (153, 10, 0, "B"),
    "C301": (153.5, 12.65, 180, "B"),
    "C302": (149.4, 14.25, 180, "B"),
    "R316": (151.5, 16.5, 0, "B"),
    "C202": (48, 17.2, 0, "F"),
    "C203": (48, 8.8, 0, "F"),
    "C222": (136, 32.1, 0, "F"),
    "C223": (136, 23.8, 0, "F"),
    "R221": (139.6, 33.5, 0, "F"),
    "C210": (47.75, 15.4, 0, "F"),
    "C211": (47.75, 10.6, 0, "F"),
    "C230": (135.75, 30.4, 0, "F"),
    "C231": (135.75, 25.6, 0, "F"),
}


def implement(root, cli):
    pcb = root / "power_p03.kicad_pcb"
    raw = pcb.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    archive = root / "generated/history" / f"before-schmitt-hf-{digest[:16]}.kicad_pcb.gz"
    if not archive.exists():
        archive.write_bytes(gzip.compress(raw, mtime=0))
    tree = coded(read_sexpr(raw.decode()))
    router = PowerRouter(tree)
    parts = {p["ref"]: p for p in json.loads((root / "components.json").read_text())}
    library = footprint_root(str(cli))
    used = {
        s: [(f"mount{i}", [x - 3.7, y - 3.7, x + 3.7, y + 3.7]) for i, (x, y) in enumerate(MOUNTS)]
        for s in ("F", "B")
    }
    used["B"].extend(("thermal_" + r, b) for r, b in THERMAL_REGIONS.items())
    old = []
    for fp in children(tree, "footprint"):
        ref = next(p[2] for p in children(fp, "property") if p[1] == "Reference")
        if ref in POSES:
            old.append(fp)
        else:
            side = first(fp, "layer")[1][0]
            used[side].append((ref, [x - 100 for x in courtyard(fp, side + ".CrtYd")]))
    oldpads = [p for ref in POSES for p in router.by_ref[ref] if p["layers"]]
    new = []
    for ref, pose in POSES.items():
        c = parts[ref]
        lib, name = c["footprint"].split(":")
        c = dict(c, value=c["part"], mpn=c["part"], nets={p["number"]: p["net"] for p in c["pins"]})
        fp = placed_footprint(c, pose, library / (lib + ".pretty") / (name + ".kicad_mod"), router.nets)
        box = [x - 100 for x in courtyard(fp, pose[3] + ".CrtYd")]
        assert valid_box(box), ref
        assert not any(overlap(box, b, 0.15) for _, b in used[pose[3]]), (
            ref,
            [r for r, b in used[pose[3]] if overlap(box, b, 0.15)],
        )
        used[pose[3]].append((ref, box))
        new.append(fp)
    for fp in old:
        tree.remove(fp)
    tree.extend(new)
    after = PowerRouter(tree)
    pads = oldpads + [p for ref in POSES for p in after.by_ref[ref] if p["layers"]]
    removed = []
    for obj in list(children(tree, "segment")):
        layer = first(obj, "layer")[1]
        a, b = [tuple(float(v) - 100 for v in first(obj, k)[1:3]) for k in ("start", "end")]
        dx, dy = b[0] - a[0], b[1] - a[1]
        for pad in pads:
            if layer not in ["F.Cu" if z == 0 else "B.Cu" for z in pad["layers"]]:
                continue
            q = pad["xy"]
            t = (
                max(0, min(1, ((q[0] - a[0]) * dx + (q[1] - a[1]) * dy) / (dx * dx + dy * dy)))
                if dx or dy
                else 0
            )
            if (
                math.dist(q, (a[0] + t * dx, a[1] + t * dy))
                < max(pad["size"]) / 2 + 0.16 + float(first(obj, "width")[1]) / 2
            ):
                tree.remove(obj)
                removed.append(obj[0])
                break
    pcb.write_text(sexpr(named(tree)) + "\n")
    (root / "generated/schmitt-hf-layout.json").write_text(
        json.dumps(
            dict(
                before_pcb_sha256=digest,
                poses=POSES,
                removed_local_old_attachments=len(removed),
                new_component_count=len(parts),
                clearance_relaxed=False,
                physical_qualified=False,
                native_refill_parity_and_erc_required=True,
            ),
            indent=2,
        )
        + "\n"
    )
    print(
        "Native six-pin Schmitt/HF repair authored;13 local poses; fresh native verification required",
        flush=True,
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", type=Path, default=ROOT)
    p.add_argument("--kicad-cli", type=Path, required=True)
    args = p.parse_args()
    implement(args.root, args.kicad_cli)
