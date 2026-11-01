"""Read-only per-layer filled-force exclusion screen at trapped physical pads."""

import hashlib
import json
from pathlib import Path

import numpy as np

from ...common.sexpr import children, first, read_sexpr
from ..revision26.layout import POWER_NETS
from ..revision26.router import LAYERS
from .distributed_mesh import DistributedBarrelMesh
from .repair import Router

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "generated/coherent-control-smt-work"
OUT = ROOT / "generated/residual-force-probe"
PADS = [
    ("R98", "1"),
    ("R98", "2"),
    ("C39", "1"),
    ("C2", "1"),
    ("U10", "5"),
    ("U10", "9"),
    ("R85", "2"),
    ("U11", "12"),
    ("U22", "11"),
]


def main():
    pcb = SOURCE / "generated/filled-coherent-control-smt.kicad_pcb"
    tree = read_sexpr(pcb.read_text())
    rt = Router(read_sexpr((SOURCE / "rail_disconnect.kicad_pcb").read_text()))
    rows = []
    for ref, pin in PADS:
        p = next(p for p in rt.by_ref[ref] if p["pin"] == pin)
        px, py = p["xy"]
        step = 0.01
        x = px + (np.arange(121) - 60) * step
        y = py + (np.arange(121) - 60) * step
        circle = (x[:, None] - px) ** 2 + (y[None, :] - py) ** 2 <= 0.5**2
        overlaps = []
        for net in sorted(POWER_NETS):
            m = DistributedBarrelMesh.__new__(DistributedBarrelMesh)
            m.x, m.y = x, y
            m.mask = np.zeros((6, len(x), len(y)), bool)
            for z in children(tree, "zone"):
                if not children(z, "net") or str(first(z, "net")[-1]).lstrip("/") != net:
                    continue
                for poly in children(z, "filled_polygon"):
                    pts = [(float(q[1]) - 100, float(q[2]) - 100) for q in first(poly, "pts")[1:]]
                    m.polygon(LAYERS.index(first(poly, "layer")[1]), pts)
            for i in range(6):
                a = int(np.count_nonzero(m.mask[i] & circle)) * step * step
                if a:
                    overlaps.append(
                        dict(
                            net=net, layer=LAYERS[i], nominal_via_clearance_disk_intersection_diagnostic_mm2=a
                        )
                    )
        rows.append(
            dict(
                ref=ref,
                pin=pin,
                net=p["net"],
                pad_centre_mm=[px, py],
                hypothetical_barrel_copper_radius_mm=0.3,
                native_zone_clearance_mm=0.2,
                filled_force_overlaps=overlaps,
            )
        )
        print(ref, pin, [(r["net"], r["layer"]) for r in overlaps], flush=True)
    OUT.mkdir(exist_ok=True)
    (OUT / "probe.json").write_text(
        json.dumps(
            dict(
                source_pcb_sha256=hashlib.sha256(pcb.read_bytes()).hexdigest(),
                recipe_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                grid_mm=0.01,
                rows=rows,
                read_only_no_copper_changed=True,
                intersection_samples_are_not_native_removed_area_or_resistance_bounds=True,
                qualified=False,
            ),
            indent=2,
        )
        + "\n"
    )


if __name__ == "__main__":
    main()
