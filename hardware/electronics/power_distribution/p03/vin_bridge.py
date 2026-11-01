"""Route VIN between actual filled-plane electrodes and real input terminals.

A zone origin is not an electrical terminal. This candidate pass selects clear
plated-barrel sites inside the actual disconnected filled components, then
routes their actual electrodes. No foreign transit is displaced or waived.
"""

import argparse
import copy
import gzip
import hashlib
import json
import math
from pathlib import Path

import numpy as np

from ...common.sexpr import read_sexpr, sexpr
from .island_stitch import components
from .route import PowerRouter, coded, named
from .spec import ROOT


def implement(root):
    pcb = root / "power_p03.kicad_pcb"
    raw = pcb.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    archive = root / "generated/history" / f"before-vin-electrode-bridge-{digest[:16]}.pcb.gz"
    if not archive.exists():
        archive.write_bytes(gzip.compress(raw, mtime=0))
    tree = read_sexpr(raw.decode())
    mesh, labels, ports = components(tree, "VIN_PROTECTED")
    tree = coded(tree)
    r = PowerRouter(tree)

    def owner(port):
        found = [i for i, p in ports.items() if port in p]
        assert len(found) == 1, (port, found)
        return found[0]

    def sites(router, component, near):
        mask = np.any(labels == component, axis=0)
        cells = np.argwhere(mask)
        cells = sorted(cells, key=lambda ij: math.dist((mesh.x[ij[0]], mesh.y[ij[1]]), near))
        candidates = []
        for ix, iy in cells:
            xy = (float(mesh.x[ix]), float(mesh.y[iy]))
            if any(math.dist(xy, q) < 2 for q in candidates):
                continue
            if router.safe_via("VIN_PROTECTED", xy, diameter=0.9, clearance=0.16):
                candidates.append(xy)
                if len(candidates) == 4:
                    break
        return candidates

    plan = [("U101.17", "U23.12", (97, 20), (119, 20)), ("U23.12", "U13.8", (140, 21), (140, 17))]
    results = []
    for a, b, anear, bnear in plan:
        if owner(a) == owner(b):
            continue
        aa, bb = sites(r, owner(a), anear), sites(r, owner(b), bnear)
        joined = False
        for ap, bp in sorted([(a, b) for a in aa for b in bb], key=lambda p: math.dist(*p))[:4]:
            candidate = copy.deepcopy(tree)
            rr = PowerRouter(candidate)
            rr.via("VIN_PROTECTED", ap, diameter=0.9)
            rr.via("VIN_PROTECTED", bp, diameter=0.9)
            rr.max_search_nodes = 600000
            if rr.connect(
                dict(net="VIN_PROTECTED", xy=ap, layers=tuple(range(6))),
                dict(net="VIN_PROTECTED", xy=bp, layers=tuple(range(6))),
                0.75,
            ):
                tree, r = candidate, rr
                joined = True
                results.append(dict(ports=[a, b], barrels_mm=[ap, bp], width_mm=0.75, authored=True))
                print("VIN actual-electrode bridge", a, b, ap, bp, flush=True)
                break
        if not joined:
            results.append(dict(ports=[a, b], candidate_a_mm=aa, candidate_b_mm=bb, authored=False))
    # The lower analog input bank is an actual same-face VIN/HF island.
    # Extend its bulk force pad to a physically clear barrel in the lower plane.
    source = next(p for p in r.by_ref["C222"] if p["pin"] == "1")
    joined = False
    for xy in [] if owner("C222.1") == owner("U23.12") else sites(r, owner("U23.12"), (138, 32)):
        candidate = copy.deepcopy(tree)
        rr = PowerRouter(candidate)
        rr.via("VIN_PROTECTED", xy)
        rr.max_search_nodes = 400000
        if rr.connect(source, dict(net="VIN_PROTECTED", xy=xy, layers=tuple(range(6))), 0.5):
            tree, r = candidate, rr
            joined = True
            results.append(dict(ports=["C222.1", "U23.12"], barrels_mm=[xy], width_mm=0.5, authored=True))
            print("Analog VIN bulk-to-plane", xy, flush=True)
            break
    if not joined:
        results.append(dict(ports=["C222.1", "U23.12"], authored=False))
    pcb.write_text(sexpr(named(tree)) + "\n")
    (root / "generated/vin-electrode-bridges.json").write_text(
        json.dumps(
            dict(
                before_pcb_sha256=digest,
                actual_filled_electrode_bridges=results,
                no_foreign_copper_displaced=True,
                clearance_relaxed=False,
                native_refill_and_connectivity_required=True,
                ampacity_and_input_noise_qualified=False,
                physical_qualified=False,
            ),
            indent=2,
        )
        + "\n"
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", type=Path, default=ROOT)
    implement(p.parse_args().root)
