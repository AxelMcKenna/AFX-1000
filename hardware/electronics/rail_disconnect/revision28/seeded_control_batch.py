"""Bare control-pad routes with native-pad-contained initial escape seeds.

The initial trace tube must be contained in actual existing SMD copper. This
avoids declaring a legal factory pad trapped merely by raster guard rounding.
All foreign force regions remain obstacles. No drills or component moves.
"""

import hashlib
import itertools
import json
import math
import shutil
import uuid
from pathlib import Path

from ...common.sexpr import read_sexpr, sexpr
from .filled_surface_path import path_between
from .repair import Router

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "generated/u28-existing-control-ground-repair-work"
WORK = ROOT / "generated/u28-seeded-control-work"


def seeds(pad, native_pads, target):
    from shapely import union_all
    from shapely.geometry import LineString, Polygon

    rows = [p for p in native_pads["pad_polygons"] if p["ref"] == pad["ref"] and p["pin"] == pad["pin"]]
    assert len(rows) == 1
    row = rows[0]
    start = pad["position_mm"]
    if row["attribute"] != 1:
        return [start]
    name = ("F.Cu", "In1.Cu", "In2.Cu", "In3.Cu", "In4.Cu", "B.Cu")[pad["layers"][0]]
    native = union_all(
        [
            Polygon(
                [(x - 100, y - 100) for x, y in p["outer"]],
                [[(x - 100, y - 100) for x, y in h] for h in p["holes"]],
            )
            for p in row["layers"][name]
        ]
    )
    options = []
    for distance, direction in itertools.product((0.1, 0.15, 0.2, 0.3), ((1, 0), (-1, 0), (0, 1), (0, -1))):
        q = [round(start[i] + distance * direction[i], 6) for i in (0, 1)]
        tube = LineString([start, q]).buffer(0.1, quad_segs=64)
        if native.covers(tube):
            options.append(q)
    options.sort(key=lambda q: math.dist(q, target))
    return [start, *options[:2]]


def main():
    import shapely

    assert not WORK.exists()
    source = SOURCE / "rail_disconnect.kicad_pcb"
    original = source.read_bytes()
    digest = hashlib.sha256(original).hexdigest()
    tree = read_sexpr(original.decode())
    filled_path = SOURCE / "generated/filled-existing-control-ground-repair1.kicad_pcb"
    filled = read_sexpr(filled_path.read_text())
    pad_path = SOURCE / "generated/native-pads.json"
    pads = json.loads(pad_path.read_text())
    assert pads["source_pcb_sha256"] == hashlib.sha256(filled_path.read_bytes()).hexdigest()
    inventory_path = SOURCE / "generated/residual-components.json"
    inventory = json.loads(inventory_path.read_text())
    assert [v for p, v in inventory["source_sha256"].items() if Path(p).resolve() == source] == [digest]
    plans = (
        ("POWER_RUN", "R93", "1"),
        ("E28_AUX_SENSE", "U19", "1"),
        ("E28_AUX_CT", "U19", "5"),
        ("E28_TIMEOUT", "R136", "1"),
        ("E28_SAFE_REQUEST", "U12", "13"),
        ("REF_LOW_OK", "U11", "12"),
        ("V5_REG_OV_OK", "U11", "9"),
        ("V5_REG_OV_REF", "U10", "5"),
        ("REF_LOW_POSITIVE", "U10", "9"),
    )
    results, added = [], []
    for net, ref, pin in plans:
        router = Router(tree)
        groups = inventory["inventory"][net]["components"]
        own = next(g for g in groups if any(o.get("ref") == ref and o.get("pin") == pin for o in g))
        start_pad = next(o for o in own if o.get("ref") == ref and o.get("pin") == pin)
        assert start_pad["layers"] in ([0], [5])
        layer = start_pad["layers"][0]
        other = [g for g in groups if g is not own and any(o["kind"] == "PAD" for o in g)]
        anchors = []
        for g in other:
            for o in g:
                if layer not in o["layers"]:
                    continue
                anchors.append(o["position_mm"])
                if o["kind"] == "PCB_TRACK":
                    anchors.append(o["end_mm"])
        anchors = sorted({tuple(p) for p in anchors}, key=lambda p: math.dist(p, start_pad["position_mm"]))[
            :2
        ]
        attempts = []
        done = False
        for end in anchors:
            for seed, step in itertools.product(seeds(start_pad, pads, end), (0.05, 0.025)):
                try:
                    points, visited = path_between(
                        router, seed, end, layer, filled, pads, margin=4, step=step, net=net
                    )
                except AssertionError as error:
                    attempts.append(dict(seed=seed, target=end, grid=step, failure=str(error)))
                    continue
                full = [start_pad["position_mm"], *points]
                objects = []
                for index, (a, b) in enumerate(zip(full, full[1:])):
                    if math.dist(a, b) < 1e-8:
                        continue
                    uid = uuid.uuid5(
                        uuid.NAMESPACE_URL, f"rmx:E28:seededControl:{digest}:{net}:{index}:{a}:{b}"
                    )
                    name = ("F.Cu", "In1.Cu", "In2.Cu", "In3.Cu", "In4.Cu", "B.Cu")[layer]
                    node = read_sexpr(
                        f'(segment (start {100 + a[0]:.6f} {100 + a[1]:.6f}) (end {100 + b[0]:.6f} {100 + b[1]:.6f}) (width .2) (layer "{name}") (net {router.nets[net]}) (uuid {uid}))'
                    )
                    tree.append(node)
                    added.append(sexpr(node))
                    objects.append(sexpr(node))
                attempts.append(
                    dict(
                        seed=seed,
                        target=end,
                        grid=step,
                        visited=visited,
                        full_native_pad_contained_initial_escape=True,
                        source_actual_pad=[ref, pin],
                        actual_new_tracks=objects,
                    )
                )
                done = True
                break
            if done:
                break
        results.append(dict(net=net, proposed_join=done, attempts=attempts))
        print(net, done, flush=True)
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
    (WORK / source.name).write_text(sexpr(tree) + "\n")
    report = dict(
        source_pcb_sha256=digest,
        recipe_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        native_inventory_sha256=hashlib.sha256(inventory_path.read_bytes()).hexdigest(),
        native_pads_sha256=hashlib.sha256(pad_path.read_bytes()).hexdigest(),
        shapely_version=shapely.__version__,
        attempts=results,
        all_old_objects_preserved=True,
        new_drills=0,
        part_moves=0,
        actual_added_tracks=added,
        all_foreign_force_fill_preserved_during_search=True,
        native_and_PDN_pending=True,
        qualified=False,
    )
    (WORK / "generated/seeded-control-routes.json").write_text(json.dumps(report, indent=2) + "\n")
    assert source.read_bytes() == original


if __name__ == "__main__":
    main()
