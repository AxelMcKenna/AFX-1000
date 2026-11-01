"""Read-only local all-layer barrel-clearance probe for real fault pads."""

import hashlib
import json
from pathlib import Path

import numpy as np
from scipy.ndimage import distance_transform_edt

from ...common.sexpr import children, first, read_sexpr
from ..revision26.layout import POWER_NETS
from .copper import Mesh
from .repair import Router

ROOT = Path(__file__).resolve().parent
WORK = ROOT / "generated/u14-residual-batch1-work"


def candidates(rt, filled, net, box):
    x = np.arange(box[0], box[2] + 0.0001, 0.025)
    y = np.arange(box[1], box[3] + 0.0001, 0.025)
    xx, yy = x[:, None], y[None, :]
    distance = np.full((len(x), len(y)), 100.0)
    for g in rt.geometry:
        if g["net"] == net or not g["layers"]:
            continue
        if g["kind"] == "line":
            ax, ay = g["start"]
            bx, by = g["end"]
            dx, dy = bx - ax, by - ay
            t = np.clip(((xx - ax) * dx + (yy - ay) * dy) / max(dx * dx + dy * dy, 1e-30), 0, 1)
            d = np.sqrt((xx - ax - t * dx) ** 2 + (yy - ay - t * dy) ** 2) - g["width"] / 2
        elif g["kind"] == "via":
            d = np.sqrt((xx - g["xy"][0]) ** 2 + (yy - g["xy"][1]) ** 2) - g["radius"]
        else:
            gx, gy = g["xy"]
            w, h = g["size"]
            d = np.sqrt(np.maximum(abs(xx - gx) - w / 2, 0) ** 2 + np.maximum(abs(yy - gy) - h / 2, 0) ** 2)
        distance = np.minimum(distance, d)
    raster = Mesh.__new__(Mesh)
    # Include enough outside the candidate box that an off-box foreign plane
    # edge cannot masquerade as an empty local mask.
    raster.x = np.arange(box[0] - 0.75, box[2] + 0.7501, 0.025)
    raster.y = np.arange(box[1] - 0.75, box[3] + 0.7501, 0.025)
    raster.mask = np.zeros((6, len(raster.x), len(raster.y)), bool)
    for z in children(filled, "zone"):
        if not children(z, "net") or str(first(z, "net")[-1]).lstrip("/") not in POWER_NETS:
            continue
        for p in children(z, "filled_polygon"):
            layer = ("F.Cu", "In1.Cu", "In2.Cu", "In3.Cu", "In4.Cu", "B.Cu").index(str(first(p, "layer")[1]))
            ps = [(float(q[1]) - 100, float(q[2]) - 100) for q in first(p, "pts")[1:]]
            raster.polygon(layer, ps)
    mask = np.any(raster.mask, axis=0)
    if mask.any():
        d = distance_transform_edt(~mask, sampling=0.025)
        force_distance = d[30 : 30 + len(x), 30 : 30 + len(y)]
    else:
        force_distance = np.full(distance.shape, 100.0)
    safe = (distance > 0.521) & (force_distance > 0.556)
    points = [
        dict(
            xy=[float(x[i]), float(y[j])],
            foreign_physical_copper_gap_mm=float(distance[i, j]),
            foreign_filled_force_distance_mm=float(force_distance[i, j]),
        )
        for i, j in np.argwhere(safe)
    ]
    points.sort(key=lambda q: -q["foreign_physical_copper_gap_mm"])
    return dict(
        box_mm=box,
        all_layer_rule=".6mm land/.3drill, >=.2mm clearance plus search guards",
        candidates=points,
        maximum_physical_gap_mm=float(distance.max()),
        maximum_force_gap_mm=float(force_distance.max()),
    )


def main():
    path = WORK / "rail_disconnect.kicad_pcb"
    fill = WORK / "generated/filled-surface-batch1.kicad_pcb"
    before = path.read_bytes()
    tree = read_sexpr(before.decode())
    filled = read_sexpr(fill.read_text())
    rt = Router(tree)
    regions = [
        ("E28_OUT_UV_FAULT", "U23.10", [127.2, 28.4, 129.2, 29.025]),
        ("E28_OUT_UV_FAULT", "U26.3", [134.7, 30.2, 136.6, 33.0]),
        ("E28_TIMEOUT_FAULT", "U23.13", [125.0, 30.2, 129.2, 34.0]),
        ("E28_TIMEOUT_FAULT", "U26.6", [132.7, 30.2, 134.7, 33.0]),
    ]
    report = dict(
        source_pcb_sha256=hashlib.sha256(before).hexdigest(),
        filled_source_sha256=hashlib.sha256(fill.read_bytes()).hexdigest(),
        recipe_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        regions={},
        actual_copper_added=False,
        qualification=False,
    )
    for net, port, box in regions:
        row = candidates(rt, filled, net, box)
        report["regions"][port] = dict(net=net, **row)
        print(port, len(row["candidates"]), row["maximum_physical_gap_mm"], flush=True)
    (WORK / "generated/fault-via-clearance-probe.json").write_text(json.dumps(report, indent=2) + "\n")
    assert path.read_bytes() == before


if __name__ == "__main__":
    main()
