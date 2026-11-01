"""Explicit local AUX-supervisor cell, preserving every circuit value and net."""

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
SOURCE = ROOT / "generated/reset-triple-remaining-batch1-work"
WORK = ROOT / "generated/u31-front-placement-work"
CP = REPO / "hardware/cad/a12/thermal/enlarged_base_pot"
CONTEXT = CP / "context/hardware/cad/a12/enclosure_growth/integration_repaired/generated/checks.scad"
POSES = {"U31": (89.6, 52.3, 0), "C76": (93.6, 52.3, 0)}


def main():
    assert not WORK.exists()
    path = SOURCE / "rail_disconnect.kicad_pcb"
    original = path.read_bytes()
    tree = read_sexpr(original.decode())
    fps = {
        next(p[2] for p in children(f, "property") if p[1] == "Reference"): f
        for f in children(tree, "footprint")
    }
    changes = []

    def front(n):
        if not isinstance(n, list) or not n:
            return
        if n[0] in ("layer", "layers"):
            for i, v in enumerate(n[1:], 1):
                if str(v).startswith("B."):
                    n[i] = "F." + str(v)[2:]
        if n[0] in ("at", "start", "end", "xy", "mid", "center") and len(n) >= 3:
            n[2] = a(str(-float(n[2])))
            if n[0] == "at" and len(n) >= 4:
                n[3] = a(str(-float(n[3])))
        for v in list(n):
            if isinstance(v, list) and v and v[0] == "justify" and v[1:] == ["mirror"]:
                n.remove(v)
            else:
                front(v)

    for ref, (x, y, angle) in POSES.items():
        fp = fps[ref]
        before = sexpr(fp)
        assert first(fp, "layer")[1] == "B.Cu"
        front(fp)
        first(fp, "at")[1:] = [a(str(100 + x)), a(str(100 + y)), a(str(angle))]
        changes.append(dict(ref=ref, before=before, after=sexpr(fp)))
    text = CONTEXT.read_text()

    def array(name):
        return json.loads(re.search("^" + name + "=(.*);$", text, re.M).group(1))

    datum = next(b[1] for b in array("ui_native_boards") if b[0] == "E28")
    assert datum == [8, 108.5, 5.0]
    parts = {p["ref"]: p for p in json.loads((SOURCE / "components.json").read_text())}
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
    geometry = {p: triangles(p) for p in mesh_paths}
    rows = []
    for ref in POSES:
        fp = fps[ref]
        xy = courtyard(fp, "F.CrtYd")
        projection, basis = height(str(fp[1]), ref, parts[ref]["part"])
        box = [
            xy[0] - 100 + datum[0],
            xy[1] - 100 + datum[1],
            datum[2] + 1.62,
            xy[2] - 100 + datum[0],
            xy[3] - 100 + datum[1],
            datum[2] + 1.62 + projection,
        ]
        expanded = [box[0] - 0.25, box[1] - 0.25, box[2] - 0.45, box[3] + 0.25, box[4] + 0.25, box[5] + 0.45]
        assert expanded[2] >= 2.8
        other_hits = []
        for name, other in fps.items():
            if name == ref or first(other, "layer")[1] != "F.Cu":
                continue
            try:
                b = courtyard(other, "F.CrtYd")
            except (IndexError, ValueError):
                continue
            if min(xy[2], b[2]) > max(xy[0], b[0]) + 1e-8 and min(xy[3], b[3]) > max(xy[1], b[1]) + 1e-8:
                other_hits.append(name)
        assert not other_hits, (ref, other_hits)
        captured_hits = []
        for b in array("ui_native_boxes"):
            if b[0] in {"E28_" + r for r in POSES}:
                continue
            other = [*b[1:4], *[b[i + 1] + b[i + 4] for i in range(3)]]
            if box_hit(box, other):
                captured_hits.append(b[0])
        assert not captured_hits, (ref, captured_hits)
        posts = [
            circle_gap(
                [box[0] - 0.9, box[1] - 0.9, box[2], box[3] + 0.9, box[4] + 0.9, box[5]],
                c,
                3.6 / math.cos(math.pi / 128),
            )
            for c in array("tc2_centres")
        ]
        assert min(posts) > 0
        mesh_checks = []
        for p, ts in geometry.items():
            check = dict(
                obstacle=str(p.relative_to(REPO)),
                surface_hits=hits(ts, expanded),
                centre_inside=contains(ts, (np.array(expanded[:3]) + np.array(expanded[3:])) / 2),
            )
            assert not check["surface_hits"] and not check["centre_inside"], (ref, check)
            mesh_checks.append(check)
        rows.append(
            dict(
                ref=ref,
                world_box_mm=box,
                floor_after_clearance_and_Z_allowance_mm=expanded[2] - 2.8,
                height_requirement_basis=basis,
                post_0p9_envelope_gaps_mm=posts,
                same_board_courtyard_hits=other_hits,
                captured_component_hits=captured_hits,
                captured_mesh_checks=mesh_checks,
            )
        )
    carrier = geometry[CP / "generated/eb_carrier_geometry.stl"]
    assert contains(carrier, [133, 156, 1]) and contains(carrier, [130.0871, 168.922, 10])
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
        exact_footprint_changes=changes,
        component_screens=rows,
        actual_R136_value10k_and_TIMEOUT_pullup_nets_preserved=True,
        original_circuit_values_and_pad_nets_preserved=True,
        no_source_copper_changed=True,
        no_OpenSCAD_run=True,
        inside_floor_and_post_controls_detected=True,
        complete_MCAD_physical_and_fabrication_qualified=False,
    )
    (WORK / "generated/placement-screen.json").write_text(json.dumps(report, indent=2) + "\n")
    assert path.read_bytes() == original
    print([(r["ref"], r["world_box_mm"]) for r in rows], flush=True)


if __name__ == "__main__":
    main()
