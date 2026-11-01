"""Stitch actual isolated native filled copper; never use zone-origin airwires.

KiCad's zone-item position is its outline vertex, not an electrical island
terminal. Same-zone-to-same-zone airwires can therefore share identical reported
XY despite representing separate copper islands. Read actual filled polygons.
"""

import argparse
import json
import math
from pathlib import Path

from ...common.sexpr import children, first, read_sexpr, sexpr
from .route import ROOT, PowerRouter, coded, named


def inside(point, polygon):
    x, y = point
    odd = False
    for (ax, ay), (bx, by) in zip(polygon, polygon[1:] + polygon[:1]):
        if (ay > y) != (by > y) and x < (bx - ax) * (y - ay) / (by - ay) + ax:
            odd = not odd
    return odd


def implement(root=ROOT):
    out = root / "generated"
    pcb = root / "power_p03.kicad_pcb"
    tree = coded(read_sexpr(pcb.read_text()))
    router = PowerRouter(tree)
    report = json.loads((out / "route-drc.json").read_text())
    zone_ids = {
        i["uuid"]
        for row in report["unconnected_items"]
        for i in row["items"]
        if i["description"].startswith("Zone ")
    }
    names = {str(n[1]): str(n[2]).lstrip("/") for n in children(tree, "net")}
    # VIN's reference is actual In3 filled copper, not any barrel that happens
    # to sit in the isolated front patch. A barrel on another isolated island
    # does not establish a connection to the main supply plane.
    reference_fills = []
    for zone in children(tree, "zone"):
        if not children(zone, "net"):
            continue
        if names[str(first(zone, "net")[1])] != "VIN_PROTECTED":
            continue
        if not children(zone, "layer") or first(zone, "layer")[1] != "In3.Cu":
            continue
        for fill in children(zone, "filled_polygon"):
            reference_fills.append(
                [tuple(float(x) - 100 for x in xy[1:3]) for xy in children(first(fill, "pts"), "xy")]
            )

    def area(poly):
        return abs(sum(ax * by - bx * ay for (ax, ay), (bx, by) in zip(poly, poly[1:] + poly[:1]))) / 2

    main_vin = max(reference_fills, key=area) if reference_fills else []
    added = []
    holds = []
    for zone in children(tree, "zone"):
        if not children(zone, "uuid") or str(first(zone, "uuid")[1]) not in zone_ids:
            continue
        net = names[str(first(zone, "net")[1])]
        for fill in children(zone, "filled_polygon"):
            polygon = [tuple(float(x) - 100 for x in xy[1:3]) for xy in children(first(fill, "pts"), "xy")]
            existing = [
                g
                for g in router.geometry
                if g["kind"] == "via"
                and g["net"] == net
                and inside(g["xy"], polygon)
                and (net != "VIN_PROTECTED" or inside(g["xy"], main_vin))
            ]
            if existing:
                continue
            x0, x1 = min(x for x, y in polygon), max(x for x, y in polygon)
            y0, y1 = min(y for x, y in polygon), max(y for x, y in polygon)
            choices = [
                (i * 0.25, j * 0.25)
                for i in range(math.ceil(x0 * 4), math.floor(x1 * 4) + 1)
                for j in range(math.ceil(y0 * 4), math.floor(y1 * 4) + 1)
                if inside((i * 0.25, j * 0.25), polygon)
                and (net != "VIN_PROTECTED" or inside((i * 0.25, j * 0.25), main_vin))
            ]
            centre = ((x0 + x1) / 2, (y0 + y1) / 2)
            choices.sort(key=lambda p: math.dist(p, centre))
            chosen = next((p for p in choices if router.safe_via(net, p)), None)
            if chosen is None:
                holds.append(
                    dict(
                        net=net,
                        bounds_mm=[x0, y0, x1, y1],
                        reason="No actual legal through-via centre in isolated native fill",
                    )
                )
                continue
            router.via(net, chosen)
            added.append(dict(net=net, via_mm=chosen))
    pcb.write_text(sexpr(named(tree)) + "\n")
    (out / "zone-stitching.json").write_text(
        json.dumps(
            dict(added=added, holds=holds, native_refill_and_closure_required=True, physical_qualified=False),
            indent=2,
        )
        + "\n"
    )
    print("native filled-island stitches", len(added), "holds", len(holds))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    implement(parser.parse_args().root)
