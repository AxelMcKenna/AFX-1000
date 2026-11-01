"""Source-bound native scene checks; any collision/missing solid exits nonzero."""

import argparse
import json
import math
import subprocess
from pathlib import Path

from hardware.cad.a12.thermal.verify import binary_stl

from .stage import OUT, REPO, sha

SOLIDS = [
    "whole_geometry",
    "electronics_geometry",
    "controls_geometry",
    "receiver_PCB_geometry",
    "wire_geometry",
    "all_ports_geometry",
]
COLLISIONS = [
    "case_electronics_collision",
    "controls_electronics_collision",
    "power_electronics_collision",
    "power_controls_collision",
    "power_case_collision",
    "wire_electronics_collision",
    "joint_electronics_collision",
    "wire_controls_case_collision",
    "joint_controls_case_collision",
    "wire_power_collision",
    "trill_other_electronics_collision",
    "trill_power_collision",
    "trill_controls_collision",
    "joint_power_collision",
    "receiver_joints_mutual_collision",
    "all_receiver_bores_collision",
    "H9_tool_ports_collision",
    "H9_head_post_ports_collision",
    "source_bore_collision",
    "receiver_bore_collision",
    "wire_pair_collision",
]
CONTROLS = [
    "receiver_PCB_positive_control",
    "wire_positive_control",
    "trill_mount_positive_control",
    "raised_switch_positive_control",
    "front_case_positive_control",
    "all_ports_positive_control",
    "H9_tool_positive_control",
]


def run(executable, names=None):
    report = json.loads((OUT / "analysis.json").read_text())
    scene = json.loads((OUT / "scene.json").read_text())
    inputs = {
        str(p.relative_to(REPO)): sha(p)
        for p in [
            OUT / "analysis.json",
            OUT / "scene.json",
            OUT / "checks.scad",
            OUT / "trill-derived.scad",
            Path(__file__),
        ]
    }
    bindings = {**report["source_sha256"], **inputs}
    assert not [name for name, h in bindings.items() if sha(REPO / name) != h], "Stale before native run"
    chosen = names or SOLIDS + COLLISIONS + CONTROLS
    assert all(n in SOLIDS + COLLISIONS + CONTROLS for n in chosen)
    cases = {}
    for name in chosen:
        role = "empty" if name in COLLISIONS else "control" if name in CONTROLS else "solid"
        target = OUT / (name + ".stl")
        target.unlink(missing_ok=True)
        cmd = [str(executable), "--hardwarnings", "--backend", "Manifold", "--export-format", "binstl"]
        values = dict(
            part="integration_only",
            thermal_part="integration_only",
            positive_part="integration_only",
            candidate_case="integration_only",
            trial="integration_only",
            body_width=334,
            body_depth=188.4,
            shell_height=45.6,
            panel_z=43.6,
            fasteners=report["nine_lid_boss_positions_mm"],
            board_mounts=scene["mounts"],
            ui_case=name,
        )
        for key, value in values.items():
            cmd += ["-D", key + "=" + json.dumps(value)]
        cmd += ["-o", str(target), str(OUT / "checks.scad")]
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=240)
        log = p.stdout + p.stderr
        (OUT / (name + ".log")).write_text(log)
        empty = p.returncode == 1 and "Current top level object is empty." in log and not target.exists()
        clean = not any(t in log for t in ["WARNING", "ERROR"])
        stats = binary_stl(target) if p.returncode == 0 and target.exists() else None
        success = clean and (
            (role == "empty" and empty)
            or (role == "solid" and stats and stats["volume_mm3"] > 0.001)
            or (role == "control" and stats and math.isclose(stats["volume_mm3"], 0.008, abs_tol=1e-6))
        )
        cases[name] = dict(
            role=role,
            clear=bool(success),
            empty=empty,
            returncode=p.returncode,
            statistics=stats,
            command=cmd,
        )
        print(
            json.dumps(
                dict(case=name, clear=bool(success), volume_mm3=stats["volume_mm3"] if stats else None)
            ),
            flush=True,
        )
        changed = [n for n, h in bindings.items() if sha(REPO / n) != h]
        result = dict(
            scope=__doc__,
            cases=cases,
            requested_cases=chosen,
            complete_required_case_set=chosen == SOLIDS + COLLISIONS + CONTROLS,
            changed_inputs=changed,
            all_requested_native_geometry_checks_clear=all(c["clear"] for c in cases.values())
            and not changed,
            source_sha256=report["source_sha256"],
            evidence_inputs_sha256=inputs,
            artifact_sha256={
                str(p.relative_to(REPO)): sha(p)
                for n in cases
                for suffix in [".log", ".stl"]
                for p in [OUT / (n + suffix)]
                if p.is_file()
            },
            physical_qualified=False,
            thermal_qualified=False,
            complete_wiring_qualified=False,
            fabrication_released=False,
        )
        (OUT / "verification.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--openscad", required=True, type=Path)
    p.add_argument("--cases", nargs="*")
    a = p.parse_args()
    raise SystemExit(not run(a.openscad, a.cases)["all_requested_native_geometry_checks_clear"])
