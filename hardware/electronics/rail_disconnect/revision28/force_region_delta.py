"""Export exact native negative-force regions and an independent Shapely delta.

Native integer rings remain the original evidence. Invalid fractured polygons
are explicitly reported before Shapely make_valid; no area threshold converts
a physical loss into a pass or overrides the native findings.
"""

import argparse
import hashlib
import json
from pathlib import Path

SELECTION = (("N12_SRC", "F.Cu"), ("N12_SRC", "B.Cu"), ("N19_SRC", "F.Cu"), ("N19_SRC", "B.Cu"))


def export_native(before, after, output):
    import pcbnew

    from .native_force_compare import union

    def chain(c):
        return [[c.CPoint(i).x, c.CPoint(i).y] for i in range(c.PointCount())]

    def regions(p):
        return [
            dict(
                outer_nm=chain(p.COutline(i)), holes_nm=[chain(p.CHole(i, h)) for h in range(p.HoleCount(i))]
            )
            for i in range(p.OutlineCount())
        ]

    old, new = pcbnew.LoadBoard(str(before)), pcbnew.LoadBoard(str(after))
    rows = []
    for net, layer_name in SELECTION:
        layer = old.GetLayerID(layer_name)
        a, b = union(old, net, layer), union(new, net, layer)
        lost, gained = pcbnew.SHAPE_POLY_SET(), pcbnew.SHAPE_POLY_SET()
        lost.BooleanSubtract(a, b)
        gained.BooleanSubtract(b, a)
        rows.append(
            dict(
                net=net,
                layer=layer_name,
                original=regions(a),
                candidate=regions(b),
                removed_native=regions(lost),
                gained_native=regions(gained),
                original_native_area_mm2=a.Area() / 1e12,
                candidate_native_area_mm2=b.Area() / 1e12,
                removed_native_area_mm2=lost.Area() / 1e12,
                gained_native_area_mm2=gained.Area() / 1e12,
            )
        )
    result = dict(
        scope=__doc__,
        source_sha256={
            str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in (before, after, Path(__file__))
        },
        kicad_version=pcbnew.GetBuildVersion(),
        rows=rows,
        physical_qualified=False,
    )
    output.write_text(json.dumps(result, indent=2) + "\n")


def compare_shapely(source, output):
    from shapely import make_valid, union_all
    from shapely.geometry import Polygon, mapping

    raw = json.loads(source.read_text())
    features = []
    rows = []
    for row in raw["rows"]:
        shapes = []
        invalid = []
        for key in ("original", "candidate"):
            parts = []
            bad = []
            for index, p in enumerate(row[key]):
                polygon = Polygon(
                    [(x / 1e6, y / 1e6) for x, y in p["outer_nm"]],
                    [[(x / 1e6, y / 1e6) for x, y in hole] for hole in p["holes_nm"]],
                )
                if not polygon.is_valid:
                    bad.append(index)
                    polygon = make_valid(polygon)
                parts.append(polygon)
            shapes.append(union_all(parts))
            invalid.append(bad)
        old, new = shapes
        removed, gained = old.difference(new), new.difference(old)
        result = dict(
            net=row["net"],
            layer=row["layer"],
            invalid_original_ring_indices=invalid[0],
            invalid_candidate_ring_indices=invalid[1],
            original_shapely_area_mm2=old.area,
            candidate_shapely_area_mm2=new.area,
            removed_shapely_area_mm2=removed.area,
            gained_shapely_area_mm2=gained.area,
            native_removed_area_mm2=row["removed_native_area_mm2"],
            native_gained_area_mm2=row["gained_native_area_mm2"],
        )
        rows.append(result)
        for name, shape in (("removed", removed), ("gained", gained)):
            features.append(
                dict(
                    type="Feature",
                    properties=dict(net=row["net"], layer=row["layer"], operation=name, units="mm"),
                    geometry=mapping(shape),
                )
            )
    result = dict(
        type="FeatureCollection",
        features=features,
        analysis=rows,
        native_input_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
        recipe_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        native_loss_result_overridden=False,
        physical_and_resistance_qualified=False,
    )
    output.write_text(json.dumps(result, indent=2) + "\n")
    print([(r["net"], r["layer"], r["removed_shapely_area_mm2"], r["gained_shapely_area_mm2"]) for r in rows])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("native", "shapely"))
    parser.add_argument("source", type=Path)
    parser.add_argument("candidate_or_output", type=Path)
    parser.add_argument("output", type=Path, nargs="?")
    args = parser.parse_args()
    if args.operation == "native":
        assert args.output is not None
        export_native(args.source, args.candidate_or_output, args.output)
    else:
        compare_shapely(args.source, args.candidate_or_output)
