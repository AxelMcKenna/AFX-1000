"""Join actual filled-net islands with legal plated barrels, not zone origins.

The raster only proposes geometric candidates. Actual KiCad refill, net identity
and connectivity remain authoritative; this is not copper resistance/ampacity
qualification. Matching same-net copper on different layers must be present at
both electrodes before a proposed bridge gets credit.
"""

import argparse
import gzip
import hashlib
import json
import math
from pathlib import Path

import numpy as np
from scipy.ndimage import distance_transform_edt, label

from ...common.sexpr import read_sexpr, sexpr
from ...rail_disconnect.revision28.copper import Mesh
from .route import PowerRouter, coded, named
from .spec import ROOT


def components(tree, net, step=0.15):
    mesh = Mesh(tree, net, step, bounds=(160, 45))
    labels = np.zeros_like(mesh.mask, dtype=np.int32)
    offset = 0
    for z in range(6):
        row, n = label(mesh.mask[z])
        row[row > 0] += offset
        labels[z] = row
        offset += n
    parent = list(range(offset + 1))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    for (x, y), drill, radius in mesh.holes:
        ix = np.where(abs(mesh.x - x) <= radius + step)[0]
        iy = np.where(abs(mesh.y - y) <= radius + step)[0]
        circle = (mesh.x[ix, None] - x) ** 2 + (mesh.y[None, iy] - y) ** 2 <= (radius + 0.05) ** 2
        ids = set(labels[:, ix[:, None], iy[None, :]][:, circle].flat) - {0}
        if ids:
            root = find(min(ids))
            for i in ids:
                parent[find(i)] = root
    roots = np.array([find(i) for i in range(offset + 1)], np.int32)
    labels = roots[labels]
    ports = {}
    for (ref, pin), layers in mesh.pads.items():
        for z, region in layers.items():
            for i in set(labels[z][region & mesh.mask[z]].flat) - {0}:
                ports.setdefault(int(i), set()).add(ref + "." + pin)
    return mesh, labels, ports


def implement(root, net):
    pcb = root / "power_p03.kicad_pcb"
    raw = pcb.read_bytes()
    before = hashlib.sha256(raw).hexdigest()
    archive = root / "generated/history" / f"before-{net.lower()}-island-stitch-{before[:16]}.pcb.gz"
    if not archive.exists():
        archive.write_bytes(gzip.compress(raw, mtime=0))
    tree = read_sexpr(raw.decode())
    mesh, labels, ports = components(tree, net)
    r = PowerRouter(coded(tree))
    ids = sorted(set(labels.flat) - {0}, key=lambda i: -np.count_nonzero(labels == i))
    reports = []
    # Only islands large enough to be physically meaningful are proposed here;
    # tiny/raster-ambiguous polygons remain for direct native review.
    ids = [i for i in ids if np.count_nonzero(labels == i) * mesh.step**2 > 0.25]
    for ii, a in enumerate(ids):
        for b in ids[ii + 1 :]:
            aa = np.any(labels == a, axis=0)
            bb = np.any(labels == b, axis=0)
            overlap = aa & bb
            if not np.any(overlap):
                continue
            score = np.zeros_like(mesh.x[:, None] + mesh.y[None, :])
            # Prefer the interior of the matching copper, with stable margin
            # rather than a single coincident raster cell at a narrow neck.
            for z in range(6):
                score = np.maximum(score, distance_transform_edt(labels[z] == a) * mesh.step)
            score = np.minimum(
                score, np.max([distance_transform_edt(labels[z] == b) * mesh.step for z in range(6)], axis=0)
            )
            cells = np.argwhere(overlap)
            cells = sorted(cells, key=lambda ij: -score[tuple(ij)])
            chosen = []
            for ix, iy in cells:
                xy = (float(mesh.x[ix]), float(mesh.y[iy]))
                if any(math.dist(xy, q) < 1 for q in chosen):
                    continue
                if not r.safe_via(net, xy, clearance=0.16):
                    continue
                r.via(net, xy)
                chosen.append(xy)
                if len(chosen) == 2:
                    break
            reports.append(
                dict(
                    component_a=int(a),
                    component_b=int(b),
                    ports_a=sorted(ports.get(a, set())),
                    ports_b=sorted(ports.get(b, set())),
                    actual_matching_layer_candidates=len(cells),
                    authored_vias_mm=chosen,
                )
            )
            if chosen:
                print(net, "actual filled island bridge", a, b, chosen, flush=True)
    pcb.write_text(sexpr(named(tree)) + "\n")
    (root / f"generated/{net.lower()}-island-stitch.json").write_text(
        json.dumps(
            dict(
                prior_pcb_sha256=before,
                diagnostic_grid_mm=mesh.step,
                connections=reports,
                native_refill_net_identity_and_connectivity_required=True,
                clearance_relaxed=False,
                copper_resistance_and_ampacity_qualified=False,
                physical_qualified=False,
            ),
            indent=2,
        )
        + "\n"
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", type=Path, default=ROOT)
    p.add_argument("--net", choices=("VIN_PROTECTED", "P12_SRC"), required=True)
    args = p.parse_args()
    implement(args.root, args.net)
