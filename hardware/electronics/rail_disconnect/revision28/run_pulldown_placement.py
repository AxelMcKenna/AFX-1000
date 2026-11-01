"""One source-bound logic-pulldown relocation and numeric pre-routing screen."""

import hashlib
import json
import math
import re
import shutil
from pathlib import Path

import numpy as np

from ....cad.a12.repaired import height
from ...common.sexpr import a, children, first, read_sexpr, sexpr
from ...output_stage.check_placement import courtyard
from .u26_band_mesh_screen import contains, hits, triangles
from .u26_band_screen import box_hit, circle_gap

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[3]
SOURCE = ROOT / "generated/u28-existing-control-ground-repair-work"
WORK = ROOT / "generated/u28-run-pulldown-placement-work"
CP = REPO / "hardware/cad/a12/thermal/enlarged_base_pot"
CONTEXT = CP / "context/hardware/cad/a12/enclosure_growth/integration_repaired/generated/checks.scad"


def main():
    assert not WORK.exists()
    path = SOURCE / "rail_disconnect.kicad_pcb"
    original = path.read_bytes()
    tree = read_sexpr(original.decode())
    fp = next(
        f
        for f in children(tree, "footprint")
        if any(p[1] == "Reference" and p[2] == "R93" for p in children(f, "property"))
    )
    before = sexpr(fp)
    assert first(fp, "layer")[1] == "B.Cu"
    first(fp, "at")[1:] = [a("177.9125"), a("152.2"), a("0")]
    text = CONTEXT.read_text()

    def array(n):
        return json.loads(re.search("^" + n + "=(.*);$", text, re.M).group(1))

    datum = next(b[1] for b in array("ui_native_boards") if b[0] == "E28")
    assert datum == [8, 108.5, 5.0]
    xy = courtyard(fp, "B.CrtYd")
    part = next(p for p in json.loads((SOURCE / "components.json").read_text()) if p["ref"] == "R93")
    projection, basis = height(str(fp[1]), "R93", part["part"])
    box = [
        xy[0] - 100 + datum[0],
        xy[1] - 100 + datum[1],
        datum[2] - projection,
        xy[2] - 100 + datum[0],
        xy[3] - 100 + datum[1],
        datum[2],
    ]
    expanded = [box[0] - 0.25, box[1] - 0.25, box[2] - 0.45, box[3] + 0.25, box[4] + 0.25, box[5] + 0.45]
    assert expanded[2] >= 2.8
    same_board = []
    for other in children(tree, "footprint"):
        ref = next(p[2] for p in children(other, "property") if p[1] == "Reference")
        if ref == "R93" or first(other, "layer")[1] != "B.Cu":
            continue
        try:
            b = courtyard(other, "B.CrtYd")
        except (IndexError, ValueError):
            continue
        if min(xy[2], b[2]) > max(xy[0], b[0]) + 1e-8 and min(xy[3], b[3]) > max(xy[1], b[1]) + 1e-8:
            same_board.append(str(ref))
    assert not same_board
    captures = []
    for row in array("ui_native_boxes"):
        if row[0] == "E28_R93":
            continue
        other = [*row[1:4], *[row[i + 1] + row[i + 4] for i in range(3)]]
        if box_hit(box, other):
            captures.append(row[0])
    assert not captures
    posts = [
        dict(
            centre_mm=c,
            extra_0p9_gap_mm=circle_gap(
                [box[0] - 0.9, box[1] - 0.9, box[2], box[3] + 0.9, box[4] + 0.9, box[5]],
                c,
                3.6 / math.cos(math.pi / 128),
            ),
        )
        for c in array("tc2_centres")
    ]
    assert all(r["extra_0p9_gap_mm"] > 0 for r in posts)
    mesh_paths = [
        CP / "generated" / (n + ".stl")
        for n in (
            "eb_carrier_geometry",
            "eb_attachment_geometry",
            "eb_metal_geometry",
            "eb_interface_geometry",
            "eb_retained_power_review",
            "ei_controls_geometry",
            "ei_all_ports_geometry",
            "ei_trill_frontbay_geometry",
            "ps_body_geometry",
            "ps_stack",
            "cp_pot_hardware_review",
        )
    ]
    checks = []
    for p in mesh_paths:
        ts = triangles(p)
        row = dict(
            obstacle=str(p.relative_to(REPO)),
            surface_hits=hits(ts, expanded),
            centre_inside=contains(ts, (np.array(expanded[:3]) + np.array(expanded[3:])) / 2),
        )
        assert not row["surface_hits"] and not row["centre_inside"]
        checks.append(row)
    controls = triangles(CP / "generated/eb_carrier_geometry.stl")
    assert contains(controls, [133, 156, 1]) and contains(controls, [130.0871, 168.922, 10])
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
    (WORK / path.name).write_text(sexpr(tree) + "\n")
    inputs = [
        path,
        SOURCE / "components.json",
        CONTEXT,
        Path(__file__),
        ROOT / "u26_band_mesh_screen.py",
        ROOT / "u26_band_screen.py",
        REPO / "hardware/cad/a12/repaired.py",
        *mesh_paths,
    ]
    report = dict(
        source_sha256={str(p.relative_to(REPO)): hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs},
        changed_ref="R93",
        old_actual_footprint=before,
        new_actual_footprint=sexpr(fp),
        world_box_mm=box,
        floor_after_0p25_clearance_and_0p2Z_mm=expanded[2] - 2.8,
        height_requirement_basis=basis,
        same_board_courtyard_hits=same_board,
        captured_component_hits=captures,
        TC02_post_checks=posts,
        mesh_checks=checks,
        inside_floor_and_post_controls_detected=True,
        no_OpenSCAD_run=True,
        no_copper_changed=True,
        physical_and_complete_MCAD_qualified=False,
    )
    (WORK / "generated/placement-screen.json").write_text(json.dumps(report, indent=2) + "\n")
    assert path.read_bytes() == original
    print(box, projection, flush=True)


if __name__ == "__main__":
    main()
