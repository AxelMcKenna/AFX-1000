"""Bounded actual-selectedR1 MCAD roles with immutable inputs and negative controls."""

import argparse
import json
import math
import subprocess
from pathlib import Path

from hardware.cad.a12.thermal.enlarged_base.verify import mesh

from .stage import OUT, REPO, ROOT, seal, sha, write

EMPTY = [
    "external_electronics_collision",
    "controls_collision",
    "case_base_interfaces_collision",
    "power_collision",
    "wire_joints_collision",
    "mount_tool_collision",
    *[f"own_PCB_correlated_seat_{i}" for i in range(3)],
    "only_old_R1_exclusion_control",
]
CONTROLS = [
    "new_R1_positive_control",
    "retained_other_component_positive_control",
    "old_R1_presence_positive_control",
    "uncorrelated_seat_shift_positive_control",
]
SOLID = ["receiving_geometry"]
ALL = SOLID + EMPTY + CONTROLS


def inputs():
    capture = json.loads((ROOT / "capture.json").read_text())
    paths = [ROOT / n for n in capture["derived_context_sha256"]]
    paths += [
        ROOT / "capture.json",
        ROOT / "stage.py",
        Path(__file__),
        ROOT / "README.md",
        OUT / "checks.scad",
        OUT / "config.json",
        REPO / "hardware/cad/a12/thermal/enlarged_base/verify.py",
    ]
    proof = ROOT / "linux_runner"
    h = seal(proof)
    paths += [proof / "handoff.json", *[proof / n for n in h["files_sha256"]]]
    return {str(p.relative_to(REPO)): sha(p) for p in paths}


def row_errors(name, row, output=OUT):
    if name not in ALL:
        return ["undeclared native case"]
    log = (output / (name + ".log")).read_text()
    p = output / (name + ".stl")
    bad = []
    if "WARNING" in log or "ERROR" in log:
        bad.append("native warning or error")
    if name in EMPTY:
        if not (
            row["returncode"] == 1
            and "Current top level object is empty." in log
            and not p.exists()
            and row["statistics"] is None
        ):
            bad.append("required empty collision is not empty")
    else:
        if row["returncode"] != 0 or "NoError" not in log or not p.exists():
            return bad + ["missing actual NoError solid"]
        m = mesh(p)
        if m != row["statistics"]:
            bad.append("raw STL disagrees with receipt")
        if (
            not m["closed_oriented_boundary"]
            or m["degenerate_triangles_excluded"]
            or m["volume_mm3"] <= 0.001
        ):
            bad.append("invalid/degenerate closed boundary")
        expected = 0.008 if name in CONTROLS else 4.18 * 7.86
        if not math.isclose(m["volume_mm3"], expected, abs_tol=2e-6 if name in CONTROLS else 2e-4):
            bad.append("incorrect witness/receiving volume")
    return bad


def run(executable):
    assert not (ROOT / "handoff.json").exists(), "Frozenoutputs are read-only; replay in a newcandidate"
    assert not (OUT / "verification.json").exists(), "Preserve original evidence; do not overwrite"
    assert executable.resolve() == ROOT / "linux_runner/openscad.py", (
        "Only the freshly proved pinned runner is applicable"
    )
    tool = seal(executable.parent)
    assert tool["fresh_controls_passed"] and tool["status"] == "READY_PINNED_LINUX_MANIFOLD_CONTROLS_ONLY"
    c = json.loads((ROOT / "capture.json").read_text())
    cfg = json.loads((OUT / "config.json").read_text())
    assert all(sha(REPO / n) == h for n, h in c["original_source_sha256"].items()), "originalinputchanged"
    assert all(sha(ROOT / n) == h for n, h in c["derived_context_sha256"].items()), "derivedcontextchanged"
    bindings = inputs()
    executable_sha256 = sha(executable)
    cases = {}
    for name in ALL:
        target = OUT / (name + ".stl")
        assert not target.exists()
        values = dict(
            part="r1_only",
            thermal_part="r1_only",
            positive_part="r1_only",
            candidate_case="r1_only",
            trial="r1_only",
            ui_case="r1_only",
            eb_case="r1_only",
            ps_case="r1_only",
            cp_case="r1_only",
            r1_case=name,
            body_width=334,
            body_depth=188.4,
            shell_height=45.6,
            panel_z=43.6,
            fasteners=cfg["fasteners"],
            board_mounts=cfg["mounts"],
            rear_ports=cfg["rear_ports"],
            openings=cfg["openings"],
        )
        cmd = [str(executable), "--hardwarnings", "--backend", "Manifold", "--export-format", "binstl"]
        for key, value in values.items():
            cmd += ["-D", key + "=" + json.dumps(value)]
        cmd += ["-o", str(target), str(OUT / "checks.scad")]
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        (OUT / (name + ".log")).write_text(p.stdout + p.stderr)
        row = dict(
            returncode=p.returncode,
            statistics=mesh(target) if p.returncode == 0 and target.exists() else None,
            command=cmd,
            role="empty" if name in EMPTY else "control" if name in CONTROLS else "receiving-requirement",
        )
        row["errors"] = row_errors(name, row)
        row["clear"] = not row["errors"]
        cases[name] = row
        changed = [n for n, h in bindings.items() if sha(REPO / n) != h] + [
            n for n, h in c["original_source_sha256"].items() if sha(REPO / n) != h
        ]
        report = dict(
            scope=__doc__,
            requested_cases=ALL,
            cases=cases,
            complete_required_case_set=len(cases) == len(ALL),
            source_sha256=bindings,
            original_inputs_sha256=c["original_source_sha256"],
            changed_inputs=changed,
            executable_sha256=executable_sha256,
            executable_changed=sha(executable) != executable_sha256,
            tool_image=tool["image"],
            tool_binary_sha256=tool["binary_sha256"],
            tool_measured_version=tool["version"],
            all_native_local_checks_clear=not changed
            and sha(executable) == executable_sha256
            and all(r["clear"] for r in cases.values()),
            artifact_sha256={
                str(p.relative_to(REPO)): sha(p)
                for n in cases
                for p in [OUT / (n + ".log"), OUT / (n + ".stl")]
                if p.exists()
            },
            all_other87_FP_proof=True,
            only_old_R1_row_excluded=True,
            external_clearance_mm=0.25,
            PCB_Z_sweep_mm=0.2,
            only_own_E19_PCB_excluded_from_external_margin=True,
            correlated_own_PCB_seat_cases=[-0.2, 0, 0.2],
            new_whole_unit_source_or_assembly_qualified=False,
            physical_qualified=False,
            thermal_qualified=False,
            fabrication_released=False,
        )
        write(OUT / "verification.json", report)
        print(
            name,
            row["clear"],
            row["statistics"]["volume_mm3"] if row["statistics"] else None,
            row["errors"],
            flush=True,
        )
        if p.returncode < 0 or not (p.stdout + p.stderr).strip():
            print("Native execution failed before usable geometry; no further app launches.", flush=True)
            break
    return report


if __name__ == "__main__":
    a = argparse.ArgumentParser()
    a.add_argument("--openscad", required=True, type=Path)
    args = a.parse_args()
    q = run(args.openscad)
    raise SystemExit(0 if q["all_native_local_checks_clear"] and q["complete_required_case_set"] else 1)
