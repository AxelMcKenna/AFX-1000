"""Portable saved-artifact audit; rejected geometry is retained as rejected."""

import argparse
import json
from pathlib import Path

from .capture import ROOT, sha, write
from .native_variant import supplemental_specs
from .verify import errors, specs

REPORTS = [
    "generated/preflight01/verification.json",
    "generated/full-receiving01/verification.json",
    "generated/tail-shape-native01/verification.json",
    "generated/supplement-native01/verification.json",
]


def report_errors(path):
    data = json.loads(path.read_text())
    bad = []
    for group in ["input_sha256", "artifact_sha256"]:
        for n, h in data[group].items():
            p = Path(n)
            if not p.is_file() or sha(p) != h:
                bad.append("stale-or-missing:" + n)
    if data["changed_inputs"]:
        bad.append("changed-inputs-recorded")
    definitions = supplemental_specs() if data.get("variant") == "supplement" else specs()
    if set(data["cases"]) != set(data["required_cases"]):
        bad.append("case-coverage-incomplete")
    for n, row in data["cases"].items():
        if n not in definitions:
            bad.append("unknown-case:" + n)
            continue
        actual = errors(n, row, definitions[n], path.parent)
        if row["errors"] != actual or row["clear"] != (not actual):
            bad.append("forged-or-stale-evidence-state:" + n)
        for suffix in [".log", ".stl"]:
            p = path.parent / (n + suffix)
            if p.exists() and str(p) not in data["artifact_sha256"]:
                bad.append("unbound-native-artifact:" + str(p))
    actual_all = (
        len(data["cases"]) == len(data["required_cases"])
        and all(r["clear"] for r in data["cases"].values())
        and not data["changed_inputs"]
    )
    if data["all_requested_clear"] != actual_all:
        bad.append("forged-all-clear")
    return bad


def check():
    cap = json.loads((ROOT / "capture.json").read_text())
    bad = []
    for n, h in cap["copied_input_sha256"].items():
        if sha(ROOT / n) != h:
            bad.append("captured-input-changed:" + n)
    rows = {}
    for n in REPORTS:
        path = ROOT / n
        bad += [n + ":" + e for e in report_errors(path)]
        data = json.loads(path.read_text())
        rows[n] = dict(
            cases=len(data["cases"]),
            clear=sum(r["clear"] for r in data["cases"].values()),
            rejected=[c for c, r in data["cases"].items() if not r["clear"]],
        )
    initial = [json.loads((ROOT / n).read_text()) for n in REPORTS[:2]]
    names = [n for d in initial for n in d["cases"]]
    if len(names) != 47 or set(names) != set(specs()):
        bad.append("initial47-incomplete-or-duplicated")
    model = json.loads((ROOT / "generated/model.json").read_text())
    if len(model["component_records"]) != 356 or model["total_native_FPs"] != 358:
        bad.append("wrong-current-component-count")
    if len(model["rear_named1p9"]) != 14:
        bad.append("missing-named-rear-exception")
    if any(
        model[n]
        for n in ["physical_qualified", "full_harness_qualified", "unknown_PROJECT_receivers_accepted"]
    ):
        bad.append("false-qualification")
    return dict(
        saved_evidence_integrity_clear=not bad,
        errors=bad,
        reports=rows,
        all_receiving_geometry_clear=False,
        physical_qualified=False,
        electrical_qualified=False,
        thermal_qualified=False,
        full_harness_qualified=False,
        fabrication_released=False,
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--out", type=Path)
    a = p.parse_args()
    report = check()
    if a.out:
        if a.out.exists():
            raise RuntimeError("Fresh audit output required")
        write(a.out, report)
    print(json.dumps(report, indent=2))
    raise SystemExit(not report["saved_evidence_integrity_clear"])
