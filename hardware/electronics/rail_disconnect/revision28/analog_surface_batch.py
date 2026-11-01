"""Bounded explicit surface joins on the sealed 32-open dual-plane placement."""

import hashlib
import json
import math
import uuid
from pathlib import Path

from ...common.sexpr import children, first, read_sexpr, sexpr
from ..revision26 import router as aid
from .repair import Router
from .u23_band_route_2d import path_between

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "generated/u28-return-dual-plane-work"
WORK = ROOT / "generated/u28-analog-surface-batch-work"
SOURCE_SHA = "dd6a6f5adab873526234818c1b4274925e8c8e75b9cfe34be1ca9f258753e5ec"


def main():
    original = (SOURCE / "rail_disconnect.kicad_pcb").read_bytes()
    assert hashlib.sha256(original).hexdigest() == SOURCE_SHA
    assert not WORK.exists()
    tree = read_sexpr(original.decode())
    filled_path = SOURCE / "generated/filled-u28-return-dual-plane1.kicad_pcb"
    filled = read_sexpr(filled_path.read_text())
    layer5_pours = []
    for zone in children(filled, "zone"):
        if not children(zone, "net"):
            continue
        for poly in children(zone, "filled_polygon"):
            if first(poly, "layer")[1] != "B.Cu":
                continue
            ps = [(float(p[1]) - 100, float(p[2]) - 100) for p in first(poly, "pts")[1:]]
            layer5_pours.append(
                dict(
                    net=str(first(zone, "net")[-1]),
                    box=[min(p[i] for p in ps) for i in (0, 1)] + [max(p[i] for p in ps) for i in (0, 1)],
                )
            )
    plans = [
        ("E28_ANA_0_ILM", (43.8, 3.6), ("R97", "1")),
        ("E28_ANA_0_DVDT", (43.3, 6.8), ("R98", "1")),
        ("E28_ANA_0_DVDT_CAP", ("R98", "2"), ("C39", "1")),
    ]
    aid.STEP = 0.125
    added, results = [], []
    for net, aa, bb in plans:
        router = Router(tree)

        def pad(port):
            rows = [
                p
                for p in router.by_ref[port[0]]
                if p["pin"] == port[1] and p["net"] == net and p["layers"] == (5,)
            ]
            assert len(rows) == 1, (port, rows)
            return rows[0]["xy"]

        if isinstance(aa[0], (float, int)):
            assert any(
                g["kind"] == "via" and g["net"] == net and math.dist(g["xy"], aa) < 1e-6
                for g in router.geometry
            )
            start = aa
        else:
            start = pad(aa)
        finish = pad(bb)
        trials = []
        for margin in (2, 4):
            # Every new segment stays in this region. No B.Cu filled polygon
            # intersects it even after trace/clearance expansion; no power or
            # return-zone withdrawal is silently enabled by the local helper.
            bounds = [min(start[i], finish[i]) - margin - 0.321 for i in (0, 1)] + [
                max(start[i], finish[i]) + margin + 0.321 for i in (0, 1)
            ]
            overlap = [
                p
                for p in layer5_pours
                if not (
                    p["box"][2] < bounds[0]
                    or p["box"][0] > bounds[2]
                    or p["box"][3] < bounds[1]
                    or p["box"][1] > bounds[3]
                )
            ]
            if overlap:
                trials.append(dict(margin=margin, refused_foreign_filled_polygon_bbox=overlap))
                continue
            try:
                points, visited = path_between(router, start, finish, 5, margin=margin, step=0.025, net=net)
            except AssertionError as error:
                trials.append(dict(margin=margin, failed=str(error)))
                continue
            net_id = router.nets[net]
            objects = []
            for index, (a, b) in enumerate(zip(points, points[1:])):
                if math.dist(a, b) < 1e-8:
                    continue
                identity = uuid.uuid5(
                    uuid.NAMESPACE_URL, f"rmx:E28:analogSurface32:{SOURCE_SHA}:{net}:{index}:{a}:{b}"
                )
                node = read_sexpr(
                    f'(segment (start {100 + a[0]:.6f} {100 + a[1]:.6f}) (end {100 + b[0]:.6f} {100 + b[1]:.6f}) (width .2) (layer "B.Cu") (net {net_id}) (uuid {identity}))'
                )
                tree.append(node)
                added.append(sexpr(node))
                objects.append(str(identity))
            trials.append(
                dict(
                    margin=margin,
                    route_points_mm=points,
                    visited_cells=visited,
                    added_track_UUIDs=objects,
                    whole_expanded_region_has_no_filled_B_polygon=True,
                )
            )
            break
        results.append(dict(net=net, actual_pad_refs=[list(aa), list(bb)], attempts=trials))
        print(net, "routed" if trials and "route_points_mm" in trials[-1] else "no path", flush=True)
    import shutil

    WORK.mkdir()
    (WORK / "generated").mkdir()
    for p in SOURCE.iterdir():
        if p.is_file() and (
            p.suffix in (".kicad_pcb", ".kicad_sch", ".kicad_pro", ".kicad_sym")
            or p.name in ("components.json", "fp-lib-table", "sym-lib-table")
        ):
            shutil.copy2(p, WORK / p.name)
        elif p.suffix == ".pretty":
            shutil.copytree(p, WORK / p.name)
    (WORK / "rail_disconnect.kicad_pcb").write_text(sexpr(tree) + "\n")
    report = dict(
        source_PCB_sha256=SOURCE_SHA,
        filled_source_sha256=hashlib.sha256(filled_path.read_bytes()).hexdigest(),
        recipe_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        attempts=results,
        added_actual_track_objects=added,
        removed_or_moved_source_copper_objects=[],
        new_drills=0,
        all_package_pad_placement_mask_rules_and_reviewed_leaf_exceptions_preserved=True,
        J8_ground_proposal_not_adopted=True,
        new_native_and_conductor_checks_pending=True,
        physical_qualification=False,
    )
    (WORK / "generated/surface-route-batch.json").write_text(json.dumps(report, indent=2) + "\n")
    assert hashlib.sha256((SOURCE / "rail_disconnect.kicad_pcb").read_bytes()).hexdigest() == SOURCE_SHA


if __name__ == "__main__":
    main()
