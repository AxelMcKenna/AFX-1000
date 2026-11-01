"""Seal/check the NP01-P1 successor without rewriting NP01."""

import argparse
import hashlib
import json
from pathlib import Path

from hardware.qualification.boards.nf_passive_selection_portable import capture_runtime, verify

ROOT = Path(__file__).resolve().parent


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def evidence_errors():
    errors = []
    capture_runtime.check_parent()
    execution = json.loads((ROOT / "final-runs/execution.json").read_text())
    if len(execution["jobs"]) != 6:
        errors.append("Incomplete six-job cross-runtime coverage")
    for job in execution["jobs"]:
        if job["returncode"] != job["expected_returncode"] or not job["expected_status_observed"]:
            errors.append("Unexpected actual job status: " + job["name"])
        if sha(Path(job["log"])) != job["log_sha256"]:
            errors.append("Changed actual job log: " + job["name"])
    for name in ["python39", "python312"]:
        p = ROOT / "final-runs" / (name + "-verify.json")
        report = json.loads(p.read_text())
        if report["errors"] or report["parent_files_verified"] != 55:
            errors.append("Failed source-current report: " + name)
        for path, expected in report["source_sha256"].items():
            if sha(Path(path)) != expected:
                errors.append("Changed final report input: " + path)
    historical = ROOT / "diagnostics/historical-code/verify-before-import-format.py"
    for name in ["python39", "python312"]:
        d = json.loads((ROOT / "diagnostics" / ("portable-" + name + ".json")).read_text())
        if d["source_sha256"][str(ROOT / "verify.py")] != sha(historical):
            errors.append("Missing exact historical formatting source")
    errors.extend(verify.check()["errors"])
    return errors


def run(create=False):
    p = ROOT / "handoff.json"
    errors = evidence_errors()
    if p.exists():
        if create:
            raise RuntimeError("Refusing to overwrite portable seal")
        d = json.loads(p.read_text())
        for name, expected in d["files_sha256"].items():
            q = ROOT / name
            if not q.is_file() or sha(q) != expected:
                errors.append("Changed sealed portable file: " + name)
        for flag in [
            "physical_qualified",
            "electrical_qualified",
            "fabrication_released",
            "NP01_parent_edited",
        ]:
            if d.get(flag) is not False:
                errors.append("Unsupported promotion: " + flag)
    elif create:
        if errors:
            raise ValueError(errors)
        files = sorted(
            x
            for x in ROOT.rglob("*")
            if x.is_file() and "__pycache__" not in x.parts and not x.name.endswith(".pyc")
        )
        d = dict(
            revision="NP01-P1-portable-handoff",
            parent_NP01_seal_sha256=capture_runtime.EXPECTED,
            files_sha256={str(x.relative_to(ROOT)): sha(x) for x in files},
            NP01_parent_edited=False,
            physical_qualified=False,
            electrical_qualified=False,
            fabrication_released=False,
            actual_successor_tests_per_runtime=23,
            actual_original_python312_strict_failures=2,
            changed_sum_scalars=23,
            max_observed_ULP_steps=1,
            policy_max_ULP_steps=4,
            scope="Only five unchanged nonnegative float terms; exact rational-sum crosscheck; all other fields exact",
        )
        p.write_text(json.dumps(d, indent=2) + "\n")
    else:
        errors.append("No portable handoff seal")
    print(json.dumps(dict(errors=errors, handoff_sha256=sha(p) if p.exists() else None)))
    raise SystemExit(bool(errors))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--create", action="store_true")
    run(parser.parse_args().create)
