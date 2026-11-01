"""Guarded fresh Linux-Manifold checks of the HT01 receiving candidate."""

import argparse
import json
import math
import subprocess
from pathlib import Path

from hardware.cad.a12.thermal.enlarged_base.verify import mesh

from .stage import FI, MODEL, OUT, ROOT, sha, write


def specifications():
    result = {}
    for name in ["old_panel_lug_collision_witness", "old_axis_flat_failure_witness", "old_bore_clearance_failure_witness"]:
        result[name] = dict(role="witness", value=name)
    for name in [
        "new_panel_lug_collision", "new_panel_lug_20percent_collision", "all_lugs_panel_collision", "thread_panel_collision",
        "new_axis_flat_collision", "new_knobs_environment_collision", "new_knobs_controls_collision",
        "body_electronics_collision", "body_controls_collision", "body_case_collision", "body_power_collision", "body_wire_collision", "pocket_void_control",
    ]:
        result[name] = dict(role="empty", value=name)
    for name in ["body_geometry", "hardware_geometry", "stack_review"]:
        result[name] = dict(role="review", value=name)
    for name in ["substrate_geometry", "panel_geometry"] + ["knob_" + str(i) for i in range(4)]:
        result[name] = dict(role="part", value=name)
    for name in ["body_positive_control", "substrate_positive_control", "lug_positive_control"]:
        result[name] = dict(role="control", value=name, expected_volume=.008)
    for i in range(4):
        for kind in ["shaft", "hardware"]:
            name = f"{kind}_knob_{i}_collision"
            result[name] = dict(role="empty", value=name)
    for i in range(10):
        for family in range(6):
            result[f"hardware_{i}_family_{family}"] = dict(role="empty", value="hardware_environment_pair", i=i, family=family)
        result[f"hardware_{i}_control"] = dict(role="control", value="hardware_index_control", i=i, expected_volume=.008)
    return result


def errors(name, row, spec, folder):
    bad = []
    target = folder / (name + ".stl")
    log = (folder / (name + ".log")).read_text()
    if "WARNING" in log or "ERROR" in log:
        bad.append("native-warning/error")
    if spec["role"] == "empty":
        if row["returncode"] != 1 or "Current top level object is empty." not in log or target.exists() or row.get("statistics") is not None:
            bad.append("not-actual-empty")
        return bad
    if row["returncode"] != 0 or "NoError" not in log or not target.exists():
        return bad + ["missing-actual-solid"]
    actual = mesh(target)
    if actual != row.get("statistics") or actual["volume_mm3"] <= .001:
        bad.append("wrong-actual-solid")
    if spec["role"] != "review" and (not actual["closed_oriented_boundary"] or actual["degenerate_triangles_excluded"]):
        bad.append("invalid-topology")
    if "expected_volume" in spec and not math.isclose(actual["volume_mm3"], spec["expected_volume"], abs_tol=2e-6):
        bad.append("wrong-control-volume")
    return bad


def run(executable, output, names=None):
    output = Path(output).resolve()
    if output.exists() or output.is_relative_to(MODEL) or ((ROOT / "handoff.json").exists() and output.is_relative_to(ROOT)):
        raise RuntimeError("Native output requires a new unsealed directory")
    specs = specifications()
    names = names or list(specs)
    assert all(n in specs for n in names)
    captured = json.loads((ROOT / "capture.json").read_text())
    assert all(sha(ROOT / n) == h for n, h in captured["captured_model_sha256"].items())
    parent = json.loads((FI / "handoff.json").read_text())
    assert all(sha(FI / n) == h for n, h in parent["files_sha256"].items())
    runner = Path(executable).resolve()
    seal_path = runner.parent / "handoff.json"
    runner_seal = json.loads(seal_path.read_text())
    assert runner_seal["fresh_controls_passed"]
    assert all(sha(runner.parent / n) == h for n, h in runner_seal["files_sha256"].items())
    files = [p for p in MODEL.rglob("*") if p.is_file()]
    files += [ROOT / n for n in ["capture.json", "contract.py", "geometry.scad", "stage.py", "verify.py"]]
    files += [OUT / n for n in ["analysis.json", "checks.scad", "config.json"]]
    files += [runner.parent / n for n in runner_seal["files_sha256"]] + [seal_path, FI / "handoff.json"]
    bindings = {str(p): sha(p) for p in files}
    cfg = json.loads((OUT / "config.json").read_text())
    output.mkdir(parents=True)
    rows = {}
    for name in names:
        spec = specs[name]
        values = {k: "cp_only" for k in ["part", "thermal_part", "positive_part", "candidate_case", "trial", "ui_case", "eb_case", "ps_case", "cp_case"]}
        values.update(fi_case="fi_only", fi_fa_case="fi_only", body_width=334, body_depth=188.4, shell_height=45.6, panel_z=43.6,
            fasteners=cfg["fasteners"], board_mounts=cfg["mounts"], rear_ports=cfg["rear_ports"], openings=cfg["openings"],
            ht_case=spec["value"], ht_i=spec.get("i", 0), ht_family=spec.get("family", 0))
        cmd = [str(runner), "--hardwarnings", "--backend", "Manifold", "--export-format", "binstl"]
        for k, v in values.items():
            cmd += ["-D", k + "=" + json.dumps(v)]
        target = output / (name + ".stl")
        cmd += ["-o", str(target), str(OUT / "checks.scad")]
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        (output / (name + ".log")).write_text(p.stdout + p.stderr)
        row = dict(returncode=p.returncode, role=spec["role"], command=cmd, statistics=mesh(target) if target.exists() else None)
        row["errors"] = errors(name, row, spec, output)
        row["clear"] = not row["errors"]
        rows[name] = row
        record = dict(cases=rows, requested_cases=names, required_cases=list(specs), complete_set=names == list(specs),
            input_sha256=bindings, changed_inputs=[n for n, h in bindings.items() if sha(Path(n)) != h],
            artifact_sha256={str(p): sha(p) for n in rows for p in [output / (n + ".log"), output / (n + ".stl")] if p.exists()},
            all_requested_clear=all(r["clear"] for r in rows.values()), runner_handoff_sha256=sha(seal_path), runner_image=runner_seal["image"],
            physical_qualified=False, thermal_qualified=False, fabrication_released=False)
        record["all_requested_clear"] &= not record["changed_inputs"]
        write(output / "verification.json", record)
        print(json.dumps(dict(case=name, clear=row["clear"], errors=row["errors"], volume=row["statistics"] and row["statistics"]["volume_mm3"])), flush=True)
    return record


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--openscad", required=True)
    parser.add_argument("--outdir", type=Path, required=True)
    parser.add_argument("--cases", nargs="+")
    args = parser.parse_args()
    raise SystemExit(not run(args.openscad, args.outdir, args.cases)["all_requested_clear"])
