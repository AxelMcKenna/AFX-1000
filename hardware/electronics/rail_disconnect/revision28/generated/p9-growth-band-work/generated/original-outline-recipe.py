"""Private +9.25 mm PCB band for the larger housing study.

Exactly three bottom-edge lines change. Existing boss reliefs, every other
edge, part, pad, hole, track, via, zone and rule remain literal source objects.
No routing, board support or housing fit approval follows from this proposal.
"""

import argparse
import copy
import hashlib
import json
import shutil
from pathlib import Path

from ...common.sexpr import a, children, first, read_sexpr, sexpr

ROOT = Path(__file__).resolve().parent


def main(workspace):
    source = ROOT / "generated/j4-p9-mask-work"
    path = source / "rail_disconnect.kicad_pcb"
    before = path.read_bytes()
    assert (
        hashlib.sha256(before).hexdigest()
        == "e7b00fbadc7c61eafe2d4c35489213605c469d73039c831eaf1513f303344a1b"
    )
    tree = read_sexpr(before.decode())
    previous = copy.deepcopy(tree)
    changes = []
    for edge in children(tree, "gr_line"):
        if first(edge, "layer")[1] != "Edge.Cuts":
            continue
        old = copy.deepcopy(edge)
        for name in ("start", "end"):
            point = first(edge, name)
            if float(point[2]) == 145.25:
                assert float(point[1]) in (105, 256)
                point[2] = a("154.5")
        if edge != old:
            changes.append(dict(before=sexpr(old), after=sexpr(edge)))
    assert len(changes) == 3
    assert sum(aa != bb for aa, bb in zip(previous, tree)) == 3 and len(tree) == len(previous)
    workspace = Path(workspace).resolve()
    assert workspace.is_relative_to(ROOT / "generated") and not workspace.exists()
    workspace.mkdir()
    (workspace / "generated").mkdir()
    for p in source.iterdir():
        if p.is_file() and (
            p.suffix in (".kicad_pcb", ".kicad_sch", ".kicad_pro", ".kicad_sym")
            or p.name in ("components.json", "fp-lib-table", "sym-lib-table")
        ):
            shutil.copy2(p, workspace / p.name)
        elif p.suffix == ".pretty":
            shutil.copytree(p, workspace / p.name)
    (workspace / path.name).write_text(sexpr(tree) + "\n")
    report = dict(
        source_pcb_sha256=hashlib.sha256(before).hexdigest(),
        candidate_pcb_sha256=hashlib.sha256((workspace / path.name).read_bytes()).hexdigest(),
        recipe_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        changes=changes,
        original_outline_size_mm=[156, 45.25],
        candidate_outline_size_mm=[156, 54.5],
        added_board_band_mm=9.25,
        new_band_board_x_range_mm=[5, 156],
        existing_operative_force_ports_parts_holes_and_boss_reliefs_unchanged=True,
        all_existing_copper_objects_and_zones_unchanged=True,
        housing_datum_nominal_mm=[8, 108.5, 5],
        candidate_maximum_housing_y_mm=163.0,
        existing_routing_mesh_bounds_require_update_before_use=True,
        new_band_has_no_new_ground_pours_or_routing=True,
        native_and_actual_housing_support_fit_required=True,
        fabrication_support_assembly_and_physical_qualified=False,
    )
    (workspace / "generated/outline-growth.json").write_text(json.dumps(report, indent=2) + "\n")
    print("Three actual bottom edges extended; no other geometry or copper changes")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("workspace")
    main(p.parse_args().workspace)
