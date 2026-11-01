"""Coherent 7.6 mm lift of the lever, sensor and four support posts.

Native geometry checks only: bearings, magnet, spring, fastener, sensor signal,
force/stiffness and physical operation remain unqualified.
"""

import argparse
import json
import math
import subprocess
from pathlib import Path

from hardware.cad.a12.generate import REPO, sha
from hardware.cad.a12.thermal.verify import binary_stl

from .generate import FASTENERS

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "lever-fit"
MAP = ROOT.parent / "panel_mount_audit/report.json"


def generate():
    report = json.loads(MAP.read_text())
    assert report["candidate_shell_mm"] == [334, 188.4, 45.6]
    assert report["panel_shift_mm"] == 7.6
    group = report["lever_group"]
    assert group["candidate_pivot_xyz_mm"] == [316, 82, 31.6]
    assert group["coupled_mount_indices"] == [16, 17, 18, 19]
    mounts = []
    for row in report["board_mounts"]:
        assert row["candidate"] is not None
        assert row["candidate"][0] == row["baseline"][0]
        if row["index"] in group["coupled_mount_indices"]:
            assert row["translation_xyz_mm"] == [0, 0, 7.6] and row["candidate"][3] == 14.6
        else:
            assert row["translation_xyz_mm"] == [0, 0, 0]
        mounts.append(row["candidate"])
    sensor = [r for r in report["envelopes"] if r["id"] in group["coupled_envelope_ids"]]
    assert len(sensor) == 2 and all(r["translation_xyz_mm"] == [0, 0, 7.6] for r in sensor)
    hashes = dict(report["source_sha256"])
    for p in [MAP, Path(__file__), Path(__file__).with_name("generate.py")]:
        hashes[str(p.relative_to(REPO))] = sha(p)
    assert all(sha(REPO / n) == h for n, h in hashes.items())
    OUT.mkdir(parents=True, exist_ok=True)
    scad = "include <" + str(ROOT.parent / "thermal-integration.scad") + ">\n"
    scad += "lever_sensor_reserves=" + json.dumps([r["candidate"] for r in sensor]) + ";\n"
    scad += """
lever_case="geometry";
module lift_bracket(){translate([0,0,7.6])lever_bracket();}
module lift_sweep(){translate([0,0,7.6])lever_sweep();}
module lift_arm(){translate([0,0,7.6])lever_arm(35);}
module lift_panel(){translate([0,0,panel_z])front_panel();}
module lift_sensors(){for(b=lever_sensor_reserves)translate([b[1],b[2],b[3]])cube([b[4],b[5],b[6]]);}
if(lever_case=="geometry"){lift_bracket();lift_sweep();}
if(lever_case=="bracket_geometry")lift_bracket();
if(lever_case=="new_sweep_lid_collision")intersection(){lift_sweep();lift_panel();}
if(lever_case=="new_arm_lid_collision")intersection(){lift_arm();lift_panel();}
if(lever_case=="old_arm_new_lid_blocked_witness")intersection(){lever_arm(35);lift_panel();}
if(lever_case=="bracket_new_posts_collision")intersection(){translate([0,0,.00002])lift_bracket();retained_thermal_shell();}
if(lever_case=="new_sweep_sensor_collision")intersection(){lift_sweep();lift_sensors();}
if(lever_case=="new_bracket_sensor_collision")intersection(){lift_bracket();lift_sensors();}
if(lever_case=="bracket_positive_control")intersection(){lift_bracket();translate([309.9,69.9,15])cube([.2,.2,.2]);}
if(lever_case=="sweep_positive_control")intersection(){lift_sweep();translate([315.9,81.9,35])cube([.2,.2,.2]);}
"""
    (OUT / "checks.scad").write_text(scad)
    plan = dict(
        scope=__doc__,
        source_sha256=hashes,
        mounts=mounts,
        sensor_reserves=[r["candidate"] for r in sensor],
        pivot_mm=[316, 82, 31.6],
        bracket_bottom_z_mm=14.6,
        panel_bottom_z_mm=43.6,
        panel_thickness_mm=2,
        intended_post_seat_boolean_guard_mm=0.00002,
        old_fixed_lever_new_panel_interference_control_required=True,
        panel_transform_adopted=False,
        exact_hardware_sensor_or_physical_qualified=False,
        complete_case_and_all_electronics_integration_verified=False,
        fabrication_released=False,
    )
    (OUT / "analysis.json").write_text(json.dumps(plan, indent=2) + "\n")
    return plan


def verify(executable):
    plan = json.loads((OUT / "analysis.json").read_text())
    inputs = {str(p.relative_to(REPO)): sha(p) for p in [OUT / "analysis.json", OUT / "checks.scad"]}
    cases = {}
    names = [
        "geometry",
        "bracket_geometry",
        "new_sweep_lid_collision",
        "new_arm_lid_collision",
        "old_arm_new_lid_blocked_witness",
        "bracket_new_posts_collision",
        "new_sweep_sensor_collision",
        "new_bracket_sensor_collision",
        "bracket_positive_control",
        "sweep_positive_control",
    ]
    (OUT / "verification.json").unlink(missing_ok=True)
    for name in names:
        target = OUT / (name + ".stl")
        target.unlink(missing_ok=True)
        cmd = [str(executable), "--hardwarnings", "--backend", "Manifold", "--export-format", "binstl"]
        for key in ["part", "thermal_part", "positive_part"]:
            cmd += ["-D", key + '="lever_fit_only"']
        for key, value in dict(
            body_width=334,
            body_depth=188.4,
            shell_height=45.6,
            fasteners=FASTENERS,
            board_mounts=plan["mounts"],
            lever_case=name,
        ).items():
            cmd += ["-D", key + "=" + json.dumps(value)]
        cmd += ["-o", str(target), str(OUT / "checks.scad")]
        process = subprocess.run(cmd, capture_output=True, text=True, timeout=240)
        log = process.stdout + process.stderr
        (OUT / (name + ".log")).write_text(log)
        clean = not any(t in log for t in ["WARNING", "ERROR"])
        empty = (
            process.returncode == 1 and "Current top level object is empty." in log and not target.exists()
        )
        if name.endswith("collision") and clean and empty:
            row = dict(clear=True, empty=True)
        elif process.returncode == 0 and target.exists() and "NoError" in log and clean:
            stats = binary_stl(target)
            ok = not name.endswith("collision") and stats["volume_mm3"] > 0.001
            if name.endswith("positive_control"):
                ok &= math.isclose(stats["volume_mm3"], 0.008, abs_tol=1e-6)
            row = dict(clear=bool(ok), **stats)
        else:
            row = dict(clear=False, returncode=process.returncode)
        cases[name] = row
        print(name, row, flush=True)
    changed = [n for n, h in {**plan["source_sha256"], **inputs}.items() if sha(REPO / n) != h]
    result = dict(
        scope=__doc__,
        cases=cases,
        changed_inputs=changed,
        lifted_lever_native_geometry_checks_clear=not changed and all(r["clear"] for r in cases.values()),
        source_sha256=plan["source_sha256"],
        evidence_inputs_sha256=inputs,
        evidence_sha256={
            str(p.relative_to(REPO)): sha(p) for p in OUT.iterdir() if p.suffix in [".log", ".stl"]
        },
        full_case_or_physical_qualified=False,
        fabrication_released=False,
    )
    (OUT / "verification.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--openscad", required=True, type=Path)
    args = parser.parse_args()
    generate()
    raise SystemExit(0 if verify(args.openscad)["lifted_lever_native_geometry_checks_clear"] else 1)
