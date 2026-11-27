"""Check through-via drills against KiCad's plotted mask and paste apertures."""

import argparse
from dataclasses import replace
from hashlib import sha256
from pathlib import Path
import json

from gerbonara import GerberFile
from gerbonara.utils import MM
from shapely import Point, Polygon, STRtree, make_valid, union_all

from hardware.electronics.common.sexpr import children, first, read_sexpr


def openings(path):
    gerber = GerberFile.open(path)
    geometries = []
    for obj in gerber.objects:
        for prim in obj.to_primitives(MM):
            if not prim.polarity_dark:
                raise ValueError(
                    f"Clear primitive in {path.name} requires polarity composition"
                )
            if prim.is_zero_size():
                continue
            contour = prim.to_arc_poly()
            centers = list(contour.arc_centers)
            for index, arc in enumerate(centers):
                end = contour.outline[(index + 1) % len(contour.outline)]
                if arc and contour.outline[index] == end == arc[1]:
                    centers[index] = None
            outline = (
                replace(contour, arc_centers=centers)
                .approximate_arcs(max_error=0.0005)
                .outline
            )
            polygon = Polygon(outline)
            if not polygon.is_valid:
                # KiCad represents some annular regions with a retraced, zero-area bridge.
                valid = make_valid(polygon)
                areas = [
                    g
                    for g in getattr(valid, "geoms", [valid])
                    if g.geom_type in ("Polygon", "MultiPolygon")
                ]
                region = union_all(areas)
                if abs(region.area - polygon.area) > 1e-7:
                    raise ValueError(
                        f"Aperture area changed while resolving {path.name}"
                    )
                polygon = region
            if polygon.area:
                geometries.append(polygon)
    if not geometries:
        raise ValueError(f"Empty aperture plot {path.name}")
    return STRtree(geometries)


def inspect(board, folder, review):
    data = json.loads(review.read_text())
    assert data["sha256"] == sha256(board.read_bytes()).hexdigest()
    text = read_sexpr(board.read_text())
    vias = []
    for node in children(text, "via"):
        x, y = map(float, first(node, "at")[1:3])
        radius = float(first(node, "drill")[1]) / 2
        vias.append((first(node, "uuid")[1], Point(x, -y), radius))
    assert len(vias) == data["through_vias"]
    target = {c["via_uuid"] for c in data["contacts"]}
    results = {}
    for layer, suffix in [
        ("F.Paste", "gtp"),
        ("B.Paste", "gbp"),
        ("F.Mask", "gts"),
        ("B.Mask", "gbs"),
    ]:
        path = folder / (board.stem + "-" + layer.replace(".", "_") + "." + suffix)
        side, kind = layer.split(".")
        header = path.read_text()[:1200]
        function = "Soldermask" if kind == "Mask" else "Paste"
        polarity = "Negative" if kind == "Mask" else "Positive"
        for attribute in (
            f"ProjectId,{board.stem},",
            "SameCoordinates,Original",
            f"FilePolarity,{polarity}",
            f"FileFunction,{function}," + ("Top" if side == "F" else "Bot"),
        ):
            if "%TF." + attribute not in header:
                raise ValueError(f"Unexpected origin or layer identification in {path}")
        tree = openings(path)
        gaps = []
        for uid, p, r in vias:
            nearest = tree.geometries[tree.nearest(p)]
            gaps.append((p.distance(nearest) - r, uid))
        minimum, uid = min(gaps)
        results[layer] = dict(
            aperture_primitives=len(tree.geometries),
            drills_intersecting_openings=sum(v < 0 for v, u in gaps),
            drills_within_1um_of_opening_edge=sum(abs(v) <= 0.001 for v, u in gaps),
            minimum_drill_edge_gap_mm=round(minimum, 6),
            nearest_via=uid,
            intersecting_via_uuids=[u for v, u in gaps if v < 0],
            minimum_gap_on_land_review_vias_mm=(
                round(min((v for v, u in gaps if u in target), default=0), 6)
                if target
                else None
            ),
        )
    return dict(
        board_sha256=data["sha256"],
        plotted_layer_check=results,
        arc_approximation_mm=0.0005,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("board", "plots", "land_review", "output"):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    result = inspect(args.board, args.plots, args.land_review)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(result)
