"""Inventory copper at the midlines of the consolidated power board's isolation packages."""

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

from shapely import LineString, STRtree, union_all

from hardware.fabrication.route_nf_surface import shape


PIN_BANKS = {
    **{ref: ((1, 2, 3, 4), (5, 6, 7, 8)) for ref in ("E_U1", "E_U2", "E_U3", "E_U4")},
    "F_U15": ((1, 3), (4, 6)),
    **{ref: ((1, 2, 3), (4, 5, 6)) for ref in ("N_U5", "N_U6", "N_U11", "N_U12")},
    **{ref: ((1, 2), (4, 6)) for ref in ("N_U17", "N_U22")},
    **{ref: ((5, 6, 7, 8), (1, 2, 3, 4)) for ref in ("N_U19", "N_U24")},
}


def package_midline(pads, banks):
    hulls = []
    for bank in banks:
        lands = [pads[str(number)] for number in bank]
        hulls.append(union_all(lands).convex_hull)
    between = LineString([hull.centroid for hull in hulls])
    mid = between.centroid
    start, end = between.coords
    dx = (end[0] - start[0]) / between.length
    dy = (end[1] - start[1]) / between.length
    envelope = union_all(hulls).convex_hull
    extent = envelope.length
    axis = LineString([(mid.x - extent * dy, mid.y + extent * dx),
                       (mid.x + extent * dy, mid.y - extent * dx)])
    return envelope.intersection(axis)


def inventory(capture):
    pads = {ref: {} for ref in PIN_BANKS}
    copper = []
    for item in capture["objects"]:
        for layer, polygons in item["layers"].items():
            if polygons:
                geom = shape(polygons)
                copper.append((layer, item["net"], item["kind"], item["uuid"], geom))
                ref = item.get("ref")
                if ref in pads and item.get("pin") and layer in ("F.Cu", "B.Cu"):
                    pads[ref][item["pin"]] = geom
    for zone in capture["zones"]:
        if zone["polygons"] and not zone["keepout"]:
            copper.append((zone["layer"], zone["net"], "ZONE", zone["uuid"], shape(zone["polygons"])))

    tree = STRtree([item[-1] for item in copper])
    packages = {}
    for ref, banks in PIN_BANKS.items():
        midline = package_midline(pads[ref], banks)
        crossings = []
        for index in tree.query(midline, predicate="intersects"):
            layer, net, kind, uuid, geom = copper[index]
            crossings.append(dict(layer=layer, net=net, kind=kind, uuid=uuid,
                                  length_on_midline_mm=round(geom.intersection(midline).length, 6)))
        packages[ref] = dict(pin_banks=banks, midline_mm=list(midline.coords),
                             crossings=sorted(crossings, key=lambda row: (row["layer"], row["uuid"])))
    return packages


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("capture", type=Path)
    parser.add_argument("board", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    capture = json.loads(args.capture.read_text())
    digest = hashlib.sha256(args.board.read_bytes()).hexdigest()
    pcb_hashes = [value for path, value in capture["source_sha256"].items()
                  if Path(path).name == args.board.name]
    if pcb_hashes != [digest]:
        parser.error("The native capture and board file have different identities")
    packages = inventory(capture)
    entries = [row for package in packages.values() for row in package["crossings"]]
    report = dict(board_sha256=digest, native_version=capture["native_version"],
                  scope="Projected copper intersecting the midpoint between each package's two pin banks. "
                        "Each via or pad can appear on multiple layers. This measurement does not establish "
                        "installed creepage, clearance or withstand voltage.",
                  layer_intersections=len(entries), unique_copper_uuids=len({row["uuid"] for row in entries}),
                  layer_intersections_by_kind=dict(Counter(row["kind"] for row in entries)), packages=packages)
    args.output.write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
