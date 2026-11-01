"""Private 20-percent depth/height enclosure blanks and outer-envelope checks.

Original control XY and PCB mounts are references only. Raising the panel
requires renewed control-PCB, shaft, switch and harness interfaces. These are
actual shell/lid solids, not an integrated or fabrication-ready new assembly.
"""

import argparse
import json
import math
import subprocess
from pathlib import Path

from hardware.cad.a12.generate import REPO, sha
from hardware.cad.a12.harness.receiver_support_fit import surface_components
from hardware.cad.a12.positive_links.collisions import snapshot
from hardware.cad.a12.thermal.verify import binary_stl

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "generated"
WIDTH, DEPTH, HEIGHT = 334, 188.4, 45.6
FASTENERS = [[x, y] for y in [8, 149, 180.4] for x in [8, 167, 326]]


def generate():
    _, _, hashes = snapshot()
    for p in [Path(__file__), REPO / "hardware/cad/a12/harness/receiver_support_fit.py"]:
        hashes[str(p.relative_to(REPO))] = sha(p)
    OUT.mkdir(parents=True, exist_ok=True)
    scad = "include <" + str(ROOT.parent / "thermal-integration.scad") + ">\n"
    scad += """
// Reproduce with generate.py: explicit -D body_depth/shell_height/fasteners
// are part of every native command and are bound in verification.json.
growth_case="shell";
module growth_shell(){retained_thermal_shell();}
module growth_lid(){translate([0,0,panel_z])front_panel();}
module growth_outer_controls(){
 for(k=knobs)translate([k[1],k[2],shell_height+2.8])knob(k[3],k[4]);
 for(b=buttons)button_pose(b)key_sweep(b);
 for(c=caps)if(c[1]=="switch")translate([c[2],c[3],panel_z])selector_cap();
 translate([0,0,shell_height-38])lever_sweep();
}
if(growth_case=="shell")growth_shell();
if(growth_case=="lid")growth_lid();
if(growth_case=="outer_reference"){growth_shell();rear_panel();growth_outer_controls();thermal_feet();}
// Only the intended coplanar lid-seating interface is separated numerically.
if(growth_case=="lid_collision")intersection(){growth_shell();translate([0,0,.00002])growth_lid();}
if(growth_case=="front_floor_positive_control")intersection(){growth_shell();translate([166.9,174.9,1])cube([.2,.2,.2]);}
if(growth_case=="high_wall_positive_control")intersection(){growth_shell();translate([166.9,187,41.9])cube([.2,.2,.2]);}
if(growth_case=="front_boss_positive_control")intersection(){growth_shell();translate([10,180.3,10])cube([.2,.2,.2]);}
if(growth_case=="front_pilot_empty_control")intersection(){growth_shell();translate([7.9,180.3,10])cube([.2,.2,.2]);}
"""
    (OUT / "candidate.scad").write_text(scad)
    plan = dict(
        scope=__doc__,
        source_sha256=hashes,
        original_shell_mm=[334, 157, 38],
        candidate_shell_mm=[WIDTH, DEPTH, HEIGHT],
        width_growth_fraction=0,
        depth_growth_fraction=0.2,
        height_growth_fraction=0.2,
        rectangular_bounding_volume_ratio=1.44,
        floor_area_ratio=1.2,
        baseline_rectangular_box_area_mm2=2 * (334 * 157 + 334 * 38 + 157 * 38),
        candidate_rectangular_box_area_mm2=2 * (WIDTH * DEPTH + WIDTH * HEIGHT + DEPTH * HEIGHT),
        added_strip_world_y_mm=[157, DEPTH],
        added_strip_is_front_not_rear=True,
        panel_z_mm=43.6,
        panel_upward_shift_mm=7.6,
        fasteners_xy_mm=FASTENERS,
        retained_old_front_row_y_mm=149,
        new_front_row_y_mm=180.4,
        intended_lid_seat_boolean_guard_mm=0.00002,
        PCB_mounts_are_original_references_only=True,
        old_thermal_base_depth_mm=157,
        enlarged_thermal_base_required=True,
        new_front_base_attachment_and_feet_qualified=False,
        actual_control_PCB_shaft_and_switch_interfaces_renewed=False,
        power_links_H9_access_receiver_neck_and_fanout_resolved=False,
        full_integration_verified=False,
        thermal_qualified=False,
        structural_or_physical_qualified=False,
        fabrication_released=False,
        baseline_sources_modified=False,
    )
    assert all(sha(REPO / n) == h for n, h in hashes.items())
    (OUT / "plan.json").write_text(json.dumps(plan, indent=2) + "\n")
    return plan


def verify(executable):
    plan = json.loads((OUT / "plan.json").read_text())
    inputs = {str(p.relative_to(REPO)): sha(p) for p in [OUT / "plan.json", OUT / "candidate.scad"]}
    cases = {}
    (OUT / "verification.json").unlink(missing_ok=True)
    for name in [
        "shell",
        "lid",
        "outer_reference",
        "lid_collision",
        "front_floor_positive_control",
        "high_wall_positive_control",
        "front_boss_positive_control",
        "front_pilot_empty_control",
    ]:
        target = OUT / (name + ".stl")
        target.unlink(missing_ok=True)
        cmd = [str(executable), "--hardwarnings", "--backend", "Manifold", "--export-format", "binstl"]
        for key in ["part", "thermal_part", "positive_part"]:
            cmd += ["-D", key + '="growth_only"']
        for key, value in dict(
            body_width=WIDTH, body_depth=DEPTH, shell_height=HEIGHT, fasteners=FASTENERS, growth_case=name
        ).items():
            cmd += ["-D", key + "=" + json.dumps(value)]
        cmd += ["-o", str(target), str(OUT / "candidate.scad")]
        process = subprocess.run(cmd, capture_output=True, text=True, timeout=240)
        log = process.stdout + process.stderr
        (OUT / (name + ".log")).write_text(log)
        clean = not any(t in log for t in ["WARNING", "ERROR"])
        expect_empty = name in ["lid_collision", "front_pilot_empty_control"]
        empty = (
            process.returncode == 1 and "Current top level object is empty." in log and not target.exists()
        )
        if expect_empty and empty and clean:
            row = dict(clear=True, empty=True)
        elif process.returncode == 0 and target.exists() and "NoError" in log and clean:
            stats = binary_stl(target)
            ok = not expect_empty and stats["volume_mm3"] > 0.001
            if name.endswith("positive_control"):
                ok &= math.isclose(stats["volume_mm3"], 0.008, abs_tol=1e-6)
            if name == "shell":
                ok &= all(
                    math.isclose(a, b, abs_tol=3e-5) for a, b in zip(stats["min_mm"], [0, 0, 0], strict=True)
                )
                ok &= all(
                    math.isclose(a, b, abs_tol=3e-5)
                    for a, b in zip(stats["max_mm"], [WIDTH, DEPTH, HEIGHT], strict=True)
                )
                stats.update(surface_components(target))
                ok &= (
                    stats["connected_surface_components"] == 1
                    and stats["edges_without_exactly_two_faces"] == 0
                )
            if name == "outer_reference":
                stats["overall_height_mm"] = stats["max_mm"][2] - stats["min_mm"][2]
                ok &= math.isclose(stats["overall_height_mm"], 95.2, abs_tol=3e-5)
            row = dict(clear=bool(ok), **stats)
        else:
            row = dict(clear=False, returncode=process.returncode)
        row["command"] = cmd
        cases[name] = row
        print(name, row, flush=True)
    changed = [n for n, h in {**plan["source_sha256"], **inputs}.items() if sha(REPO / n) != h]
    report = dict(
        scope=__doc__,
        cases=cases,
        changed_inputs=changed,
        native_enclosure_blank_checks_clear=not changed and all(r["clear"] for r in cases.values()),
        source_sha256=plan["source_sha256"],
        evidence_inputs_sha256=inputs,
        evidence_sha256={
            str(p.relative_to(REPO)): sha(p) for p in OUT.iterdir() if p.suffix in [".stl", ".log"]
        },
        control_board_shaft_engagement_verified=False,
        full_integration_verified=False,
        thermal_qualified=False,
        structural_or_physical_qualified=False,
        fabrication_released=False,
    )
    (OUT / "verification.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--openscad", type=Path, required=True)
    args = parser.parse_args()
    generate()
    raise SystemExit(0 if verify(args.openscad)["native_enclosure_blank_checks_clear"] else 1)
