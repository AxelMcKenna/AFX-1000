"""Keep execution failures explicit while proving their exact distributed test."""

import hashlib
import json
from pathlib import Path

from .stage import OUT, ROOT, sha, write
from .verify import row_errors

FAILED = "ps_hardware_other_components_collision"
FAMILIES = [
    "ui_electronics(false,false)",
    "cp_other_pot_bodies(p)",
    "ui_power_only()",
    "ps_other_controls()",
    "pf_wires(.25)",
    "ui_all_joints(.25)",
]


def recovery_contract_errors(main, retry, split, plan, model):
    bad = []
    source = next(
        s for s in model.splitlines() if s.startswith('if(ps_case=="hardware_other_components_collision")')
    )
    if (
        source != plan["original_branch_exact"]
        or hashlib.sha256(source.encode()).hexdigest() != plan["original_branch_sha256"]
    ):
        bad.append("original exact failed expression differs")
    if (
        plan["obstacle_family_expressions_exact"] != FAMILIES
        or len(plan["centres"]) != 10
        or len(set(map(tuple, plan["centres"]))) != 10
    ):
        bad.append("original obstacle/point set omitted or changed")
    pairs = {(i, j) for i in range(10) for j in range(6)}
    controls = {(i, 6) for i in range(10)}
    if (
        set(map(tuple, plan["pairs"])) != pairs
        or len(plan["pairs"]) != 60
        or set(map(tuple, plan["nonempty_HW_controls"])) != controls
        or len(plan["nonempty_HW_controls"]) != 10
    ):
        bad.append("plan lacks exact60pairs/10controls")
    got = {(r["pot_index"], r["family_index"]) for r in split["cases"].values()}
    if (
        got != pairs | controls
        or len(split["cases"]) != 70
        or not split["complete_distributive_coverage"]
        or not split["all_requested_clear"]
        or split["changed_inputs"]
    ):
        bad.append("recovery actual evidence coverage incomplete/failed/stale")
    if (
        set(n for n, r in main["cases"].items() if not r["clear"]) != {FAILED}
        or main["cases"][FAILED]["returncode"] != 137
    ):
        bad.append("main source failure record changed")
    if retry["cases"][FAILED]["returncode"] != 137 or retry["cases"][FAILED]["clear"]:
        bad.append("rejected unchanged retry relabeled")
    if main["input_sha256"] != retry["input_sha256"] or any(
        split["input_sha256"].get(n) != h for n, h in main["input_sha256"].items()
    ):
        bad.append("recovery does not use exact original inputs")
    if split["original_union_native_execution_completed"] is not False:
        bad.append("failed native union falsely claimed complete")
    base = main["cases"][FAILED]["command"][:-3]
    base[base.index('ps_case="hardware_other_components_collision"')] = 'ps_case="cp_only"'
    for name, row in split["cases"].items():
        i, j = row["pot_index"], row["family_index"]
        if (
            name != f"pot{i:02d}_family{j}"
            or row["centre"] != plan["centres"][i]
            or row["expected_empty"] != (j < 6)
        ):
            bad.append("pair metadata mismatch:" + name)
        expected = base + [
            "-D",
            "fi_hw_index=" + str(i),
            "-D",
            "fi_hw_family=" + str(j),
            "-o",
            str(OUT / "hardware-split-v2" / (name + ".stl")),
            str(ROOT / "hardware-split-v2.scad"),
        ]
        if row["command"] != expected:
            bad.append("original command/position/clearance changed:" + name)
        if j == 6:
            stat = row["statistics"]
            px, py = plan["centres"][i]
            if (
                stat is None
                or any(abs(a - b) > 1e-4 for a, b in zip(stat["min_mm"], [px + 3.9, py - 0.1, 47]))
                or any(abs(a - b) > 1e-4 for a, b in zip(stat["max_mm"], [px + 4.1, py + 0.1, 47.2]))
            ):
                bad.append("actual index-specific control bounds mismatch:" + name)
    return bad


def audit():
    main = json.loads((OUT / "verification.json").read_text())
    retry = json.loads((OUT / "retry-ps-hardware/verification.json").read_text())
    split = json.loads((OUT / "hardware-split-v2/verification.json").read_text())
    plan = json.loads((OUT / "hardware-split-plan-v2.json").read_text())
    specs = json.loads((OUT / "cases.json").read_text())
    bad = recovery_contract_errors(main, retry, split, plan, (OUT / "context-derived.scad").read_text())
    if len(main["cases"]) != 162 or not main["complete_required_set"] or main["changed_inputs"]:
        bad.append("original full attempt incomplete/stale")
    for report in [main, retry, split]:
        for group in ["input_sha256", "artifact_sha256"]:
            for n, h in report[group].items():
                if sha(Path(n)) != h:
                    bad.append("native bound file changed:" + n)
    for name, row in main["cases"].items():
        if name != FAILED:
            bad += row_errors(name, row, specs[name], OUT)
    for folder, report in [(OUT, main), (OUT / "retry-ps-hardware", retry)]:
        if (folder / (FAILED + ".stl")).exists() or (folder / (FAILED + ".log")).read_bytes():
            bad.append("137diagnostic altered")
    for name, row in split["cases"].items():
        spec = dict(
            role="empty" if row["family_index"] < 6 else "control",
            expected_volume=None if row["family_index"] < 6 else 0.008,
        )
        bad += row_errors(name, row, spec, OUT / "hardware-split-v2")
    return bad


def record():
    if (ROOT / "handoff.json").exists():
        raise RuntimeError("Sealed coverage is read-only; use audit()")
    errors = audit()
    result = dict(
        scope=__doc__,
        errors=errors,
        original_full_attempt_native_records=162,
        original_native_checks_passed=161,
        original_union_native_execution_completed=False,
        exact_native_retry_completed=False,
        original_union_137_records_preserved=True,
        source_exact_pairs=60,
        index_specific_HW_controls=10,
        complete_162_geometry_conditions_established_by_native_and_distributivity=not errors,
        same_physical_geometry_and_clearance_modules=True,
        OOM_cause_proven=False,
        tool_resource_observations="generated/daemon-diagnostic",
        evidence_sha256={
            str(p.relative_to(ROOT)): sha(p)
            for p in [
                Path(__file__),
                OUT / "verification.json",
                OUT / "retry-ps-hardware/verification.json",
                OUT / "hardware-split-v2/verification.json",
                OUT / "hardware-split-plan-v2.json",
                ROOT / "hardware-split-v2.scad",
            ]
        },
        physical_qualified=False,
        thermal_qualified=False,
        fabrication_released=False,
    )
    write(OUT / "effective-coverage.json", result)
    print(json.dumps(dict(errors=errors, geometry_conditions_established=not errors)))
    return result


if __name__ == "__main__":
    raise SystemExit(0 if not record()["errors"] else 1)
