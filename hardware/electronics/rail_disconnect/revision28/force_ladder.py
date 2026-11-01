"""Physical through-barrel attachments for fragmented parallel analog copper.

Choose actual shared In3/In4 filled copper, retain all foreign force fills, and
emit real plated holes. Native checks and finite positive/return extraction are
mandatory; a raster or added area never establishes a resistance bound.
"""

import hashlib
import json
import math
import uuid
from pathlib import Path

import numpy as np
from scipy.ndimage import distance_transform_edt, label

from ...common.sexpr import a, children, read_sexpr, sexpr
from ..revision26 import router as aid
from ..revision26.layout import Layout
from .force_guard import ForceGuard
from .native_mesh import NativePadMesh
from .repair import ROOT, Router


def main(native_label, pads_path, limit=16, preserve_foreign_force=True):
    path = ROOT / "rail_disconnect.kicad_pcb"
    before = path.read_bytes()
    receipt_path = ROOT / "generated" / ("native-" + native_label + ".json")
    receipt = json.loads(receipt_path.read_text())
    assert receipt["pcb_sha256"] == hashlib.sha256(before).hexdigest()
    assert receipt["source_unchanged_after_check"]
    filled = ROOT / "generated" / ("filled-" + native_label + ".kicad_pcb")
    pads_path = Path(pads_path)
    pads = json.loads(pads_path.read_text())
    assert pads["source_pcb_sha256"] == hashlib.sha256(filled.read_bytes()).hexdigest()
    native_tree = read_sexpr(filled.read_text())
    step = 0.125
    mesh = NativePadMesh(native_tree, "V5_REG", step, pads)
    islands, count = label(mesh.mask[4])
    sizes = np.bincount(islands.ravel())
    shared = distance_transform_edt(mesh.mask[3] & mesh.mask[4], sampling=step) > 0.32
    tree = read_sexpr(before.decode())
    aid.STEP = step
    rt = Router(tree)
    guard = ForceGuard(native_tree, rt, step)
    _, blocked = guard.apply("V5_REG", np.zeros((6, rt.nx, rt.ny), bool), np.zeros((rt.nx, rt.ny), bool), 0.2)
    judge = Layout.__new__(Layout)
    judge.router = rt
    plans = []
    rejected_islands = []
    for region in sorted(range(1, count + 1), key=lambda i: -sizes[i]):
        if sizes[region] < 200 or len(plans) >= limit:
            continue
        candidates = []
        for ix, iy in np.argwhere(shared & (islands == region)):
            xy = (float(mesh.x[ix]), float(mesh.y[iy]))
            rx, ry = (round(v / step) for v in xy)
            if not (0 <= rx < rt.nx and 0 <= ry < rt.ny) or (preserve_foreign_force and blocked[rx, ry]):
                continue
            candidates.append(xy)
        existing = [g["xy"] for g in rt.geometry if g["kind"] == "via" and g["net"] == "V5_REG"]
        candidates.sort(key=lambda p: -min(math.dist(p, q) for q in existing))
        selected = []
        for xy in candidates:
            if len(selected) >= 2 or len(plans) >= limit:
                break
            if any(math.dist(xy, q) < 2 for q in selected):
                continue
            if not judge.free_via("V5_REG", xy):
                continue
            previous = len(children(tree, "via"))
            rt.via("V5_REG", xy)
            if len(children(tree, "via")) != previous + 1:
                continue
            selected.append(xy)
            plans.append(
                dict(
                    xy_mm=xy,
                    native_in4_island=region,
                    actual_shared_copper_area_mm2=float(sizes[region]) * step**2,
                )
            )
        if not selected:
            rejected_islands.append(region)
    assert plans, "No physical, foreign-force-safe cross-layer attachment sites"
    ids = []
    for index, node in enumerate(tree):
        if isinstance(node, list) and node and node[0] == "via" and not children(node, "uuid"):
            uid = str(uuid.uuid5(uuid.NAMESPACE_URL, f"rmx:E28:force-ladder:{index}:{sexpr(node)}"))
            node.append([a("uuid"), a(uid)])
            ids.append(uid)
    assert len(ids) == len(plans)
    path.write_text(sexpr(tree) + "\n")
    (ROOT / "generated/analog-force-ladder.json").write_text(
        json.dumps(
            dict(
                before_sha256=hashlib.sha256(before).hexdigest(),
                after_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                native_receipt_sha256=hashlib.sha256(receipt_path.read_bytes()).hexdigest(),
                native_filled_sha256=pads["source_pcb_sha256"],
                native_pad_geometry_sha256=hashlib.sha256(pads_path.read_bytes()).hexdigest(),
                plans=plans,
                unattachable_in4_islands=rejected_islands,
                protected_ids=ids,
                barrel_drill_mm=0.3,
                barrel_land_mm=0.6,
                foreign_force_antipads_permitted_for_explicit_development_comparison=not preserve_foreign_force,
                actual_lost_force_material_and_complete_positive_extraction_required=True,
                added_ideal_layer_shortcuts=False,
                certified_resistance_upper_bound=False,
                actual_native_and_positive_return_recheck_required=True,
                filled_capped_process_accepted=False,
                physical_qualified=False,
            ),
            indent=2,
        )
        + "\n"
    )
    print("Added", len(plans), "actual analog interlayer attachments", plans, flush=True)


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("native_label")
    p.add_argument("pads_path")
    args = p.parse_args()
    main(args.native_label, args.pads_path)
