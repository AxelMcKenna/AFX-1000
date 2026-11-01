"""Inspect integer force contours and new-copper exclusions without area waivers.

Run with KiCad Python. Exact vertex changes remain changes, even when points
mostly slide along an existing edge. This complements, and never overrides,
the original strict native Boolean subtraction report.
"""

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

import pcbnew

from ...common.sexpr import children, first, read_sexpr
from .native_contract_compare import fingerprint
from .native_force_compare import FORCE_NETS, LAYERS


def ring(chain):
    points = [(chain.CPoint(i).x, chain.CPoint(i).y) for i in range(chain.PointCount())]
    minimum = min(points)
    return min(tuple(points[i:] + points[:i]) for i, value in enumerate(points) if value == minimum)


def contours(board, net, layer):
    result = []
    for zone in board.Zones():
        if zone.GetNetname().lstrip("/") != net or not zone.IsOnLayer(layer) or zone.GetIsRuleArea():
            continue
        polys = zone.GetFilledPolysList(layer)
        for i in range(polys.OutlineCount()):
            result.append(
                (
                    ring(polys.COutline(i)),
                    tuple(sorted(ring(polys.CHole(i, h)) for h in range(polys.HoleCount(i)))),
                )
            )
    return sorted(result)


def twice_area(points):
    return sum(a[0] * b[1] - a[1] * b[0] for a, b in zip(points, points[1:] + points[:1]))


def primitives(path):
    tree = read_sexpr(path.read_text())
    nets = {str(n[1]): str(n[2]).lstrip("/") for n in children(tree, "net")}
    result = []
    for kind in ("zone", "segment", "via"):
        for node in children(tree, kind):
            if not children(node, "net"):
                continue
            value = first(node, "net")
            name = (
                str(value[2]).lstrip("/")
                if len(value) > 2
                else nets.get(str(value[1]), str(value[1]).lstrip("/"))
            )
            if name in FORCE_NETS:
                result.append((kind, name, fingerprint(node)))
    return Counter(result)


def review(original, candidate):
    before, after = pcbnew.LoadBoard(str(original)), pcbnew.LoadBoard(str(candidate))
    old_ids = {t.m_Uuid.AsString() for t in before.GetTracks()}
    added = [t for t in after.GetTracks() if t.m_Uuid.AsString() not in old_ids]
    rows = []
    collision_rows = []
    for net in sorted(FORCE_NETS):
        for name in LAYERS:
            layer = before.GetLayerID(name)
            one, two = contours(before, net, layer), contours(after, net, layer)
            if not one and not two:
                continue
            changes = []
            for index, (a, b) in enumerate(zip(one, two)):
                if a == b:
                    continue
                points_a, holes_a = a
                points_b, holes_b = b
                details = []
                if len(points_a) == len(points_b):
                    for k, (p, q) in enumerate(zip(points_a, points_b)):
                        if p != q:
                            details.append(
                                dict(
                                    index=k,
                                    original_nm=p,
                                    candidate_nm=q,
                                    original_previous_nm=points_a[k - 1],
                                    original_next_nm=points_a[(k + 1) % len(points_a)],
                                )
                            )
                changes.append(
                    dict(
                        ring_index=index,
                        original_vertices=len(points_a),
                        candidate_vertices=len(points_b),
                        changed_vertex_details=details,
                        holes_exactly_equal=holes_a == holes_b,
                        signed_twice_area_change_nm2=twice_area(points_b) - twice_area(points_a),
                    )
                )
            rows.append(
                dict(
                    net=net,
                    layer=name,
                    original_rings=len(one),
                    candidate_rings=len(two),
                    exact_integer_rings_equal=one == two,
                    changed_rings=changes,
                )
            )
            old_zones = [
                z.GetFilledPolysList(layer)
                for z in before.Zones()
                if z.GetNetname().lstrip("/") == net and z.IsOnLayer(layer) and not z.GetIsRuleArea()
            ]
            checked = 0
            hits = []
            for item in added:
                if not item.IsOnLayer(layer) or item.GetNetname().lstrip("/") == net:
                    continue
                if item.GetClass() == "PCB_VIA":
                    # Entire physical copper land plus .200 mm electrical clearance.
                    shape = pcbnew.SHAPE_CIRCLE(item.GetPosition(), item.GetWidth(layer) // 2 + 200000)
                else:
                    shape = pcbnew.SHAPE_SEGMENT(item.GetStart(), item.GetEnd(), item.GetWidth() + 400000)
                checked += 1
                if any(poly.Collide(shape) for poly in old_zones):
                    hits.append(item.m_Uuid.AsString())
            collision_rows.append(
                dict(
                    net=net,
                    layer=name,
                    added_foreign_objects_checked=checked,
                    native_old_filled_region_hits=hits,
                )
            )
    return dict(
        method=__doc__,
        kicad_version=pcbnew.GetBuildVersion(),
        source_sha256={
            str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in (original, candidate, Path(__file__))
        },
        force_primitive_contracts_equal=primitives(original) == primitives(candidate),
        actual_integer_contours=rows,
        added_track_and_via_clearance_checks=collision_rows,
        all_new_foreign_copper_plus_0p2_clearance_disjoint_from_original_force=all(
            not r["native_old_filled_region_hits"] for r in collision_rows
        ),
        exact_all_force_contours_equal=all(r["exact_integer_rings_equal"] for r in rows),
        strict_previous_boolean_no_loss_result_overridden=False,
        resistance_startup_fabrication_and_physical_qualified=False,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("original", "candidate", "output"):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    result = review(args.original, args.candidate)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print("Exact force integer contours equal:", result["exact_all_force_contours_equal"])
    print("Force primitive contracts equal:", result["force_primitive_contracts_equal"])
    print(
        "All added foreign Cu plus clearance disjoint:",
        result["all_new_foreign_copper_plus_0p2_clearance_disjoint_from_original_force"],
    )
