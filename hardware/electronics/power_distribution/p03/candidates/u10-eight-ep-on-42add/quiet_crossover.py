"""Declared native candidate crossovers on In1, with physical masks intact.

These are deliberate new cuts in the return-plane geometry. They require fresh
coupled ground, thermal and noise qualification; no old return model is reused.
Only the stated bounded corridors may use In1. In4 remains reserved.
"""

import argparse
import gzip
import hashlib
import json
import math
from pathlib import Path

from ...common.sexpr import children, first, read_sexpr, sexpr
from . import route
from .route import PowerRouter, coded, named
from .spec import ROOT

CORRIDORS = {
    "VIN_PROTECTED": [(0.6, 0.6, 159.4, 44.4)],
    "V5_REG_SRC": [(0.6, 0.6, 159.4, 44.4)],
    "AUX_START_DELAY": [(28, 12, 34, 21)],
}


class CrossoverRouter(PowerRouter):
    def masks(self, net, width):
        blocked, via = super().masks(net, width)
        if net in CORRIDORS:
            physical, _ = route.PHYSICAL_MASKS(self, net, width)
            allowed = False
            for x0, y0, x1, y1 in CORRIDORS[net]:
                allowed = allowed | ((self.xx >= x0) & (self.xx <= x1) & (self.yy >= y0) & (self.yy <= y1))
            selected_layer = getattr(self, "crossover_layer", 1)
            blocked[selected_layer] &= ~(allowed & ~physical[selected_layer])
            # The frozen limiting converter spreader and quiet corridors are
            # never opened to a new VIN/monitor route through this exception.
            x0, y0, x1, y1 = route.THERMAL_REGIONS["U13"]
            forbidden = (
                (self.xx > x0 - 0.2 - width / 2)
                & (self.xx < x1 + 0.2 + width / 2)
                & (self.yy > y0 - 0.2 - width / 2)
                & (self.yy < y1 + 0.2 + width / 2)
            )
            blocked[selected_layer] |= forbidden
            if getattr(self, "only_in1", False):
                for z in range(6):
                    if z != selected_layer:
                        blocked[z] = True
                via[:] = True
        return blocked, via


def implement(root):
    pcb = root / "power_p03.kicad_pcb"
    raw = pcb.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    archive = root / "generated/history" / f"before-declared-in1-crossovers-{digest[:16]}.pcb.gz"
    if not archive.exists():
        archive.write_bytes(gzip.compress(raw, mtime=0))
    tree = coded(read_sexpr(raw.decode()))
    names = {str(n[1]): str(n[2]).lstrip("/") for n in children(tree, "net")}
    records = []
    displaced = []

    def stage(net, xy, diameter=0.6):
        r = CrossoverRouter(tree)
        full = r.geometry
        r.geometry = [g for g in full if g["kind"] != "line"]
        reuse = any(
            g["kind"] == "via" and g["net"] == net and math.dist(g["xy"], xy) < 0.05 for g in r.geometry
        )
        if not reuse and not r.safe_via(net, xy, diameter=diameter, clearance=0.16):
            return False
        r.geometry = full
        for obj in list(children(tree, "segment")):
            other = names[str(first(obj, "net")[1])]
            if other == net:
                continue
            a, b = [tuple(float(v) - 100 for v in first(obj, k)[1:3]) for k in ("start", "end")]
            dx, dy = b[0] - a[0], b[1] - a[1]
            t = (
                max(0, min(1, ((xy[0] - a[0]) * dx + (xy[1] - a[1]) * dy) / (dx * dx + dy * dy)))
                if dx or dy
                else 0
            )
            if (
                math.dist(xy, (a[0] + t * dx, a[1] + t * dy))
                < diameter / 2 + 0.16 + float(first(obj, "width")[1]) / 2
            ):
                assert "SW" not in other and "BOOT" not in other, other
                tree.remove(obj)
                displaced.append((obj, other, a, b))
        CrossoverRouter(tree).via(net, xy, diameter=diameter)
        return True

    # Real input-plane endpoints selected from the filled-copper diagnostic.
    if stage("VIN_PROTECTED", (78.075, 15.075)) and stage("VIN_PROTECTED", (136.275, 14.475)):
        r = CrossoverRouter(tree)
        r.only_in1 = True
        r.max_search_nodes = 1000000
        ok = r.connect(
            dict(net="VIN_PROTECTED", xy=(78.075, 15.075), layers=(1,)),
            dict(net="VIN_PROTECTED", xy=(136.275, 14.475), layers=(1,)),
            0.25,
        )
        records.append(dict(net="VIN_PROTECTED", joined=ok, width_mm=0.25, routes=r.routes))
        print("Bounded In1 VIN feed", ok, flush=True)
    if stage("V5_REG_SRC", (144.75, 10.9)):
        r = CrossoverRouter(tree)
        r.only_in1 = True
        r.max_search_nodes = 1000000
        ok = r.connect(
            dict(net="V5_REG_SRC", xy=(144.75, 10.9), layers=(1,)),
            dict(net="V5_REG_SRC", xy=(67.5, 32.875), layers=(1,)),
            0.16,
        )
        records.append(dict(net="V5_REG_SRC", joined=ok, width_mm=0.16, routes=r.routes))
        print("Bounded In1 presence sense", ok, flush=True)
    if False:  # AUX already independently closed; preserve its actual saved routing.
        r = CrossoverRouter(tree)
        r.max_search_nodes = 400000
        source = next(p for p in r.by_ref["U102"] if p["pin"] == "7")
        local = r.connect(source, dict(net="AUX_START_DELAY", xy=(29.25, 19.675), layers=(0,)), 0.16)
        remote = r.connect(
            dict(net="AUX_START_DELAY", xy=(29.25, 19.675), layers=(1,)),
            dict(net="AUX_START_DELAY", xy=(31.75, 14.45), layers=(1,)),
            0.16,
        )
        records.append(dict(net="AUX_START_DELAY", local_joined=local, remote_joined=remote, routes=r.routes))
        print("Bounded In1 AUX soft-start", local, remote, flush=True)
    reroutes = []
    for obj, net, a, b in displaced:
        r = CrossoverRouter(tree)
        r.max_search_nodes = 400000
        layer = route.LAYERS.index(str(first(obj, "layer")[1]))
        width = float(first(obj, "width")[1])
        ok = r.connect(dict(net=net, xy=a, layers=(layer,)), dict(net=net, xy=b, layers=(layer,)), width)
        reroutes.append(dict(net=net, original_layer=route.LAYERS[layer], original_width_mm=width, joined=ok))
    pcb.write_text(sexpr(named(tree)) + "\n")
    (root / "generated/declared-in1-crossovers.json").write_text(
        json.dumps(
            dict(
                before_pcb_sha256=digest,
                bounded_corridors_mm=CORRIDORS,
                records=records,
                displaced_transit_reroutes=reroutes,
                physical_obstacle_mask_preserved=True,
                clearance_relaxed=False,
                return_plane_geometry_changed=True,
                coupled_ground_and_thermal_extraction_required=True,
                noise_and_physical_qualified=False,
            ),
            indent=2,
        )
        + "\n"
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", type=Path, default=ROOT)
    implement(p.parse_args().root)
