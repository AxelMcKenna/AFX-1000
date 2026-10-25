"""Reproduce bench-plan/parser checks, recording zero physical measurements."""

import datetime
import json
import re
import subprocess
import sys

from .check import evaluate
from .generate import main as generate
from .spec import REPO, digest


def main():
    generate()
    generated = REPO / "hardware/qualification/generated"
    out = REPO / "hardware/validation/bench-plan"
    out.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "unittest",
            "discover",
            "-s",
            "tests/tooling",
            "-p",
            "test_qualification.py",
            "-v",
        ],
        cwd=REPO,
        capture_output=True,
        text=True,
    )
    log = result.stdout + result.stderr
    (out / "parser-tests.txt").write_text(log)
    if result.returncode:
        raise RuntimeError(log)
    match = re.search(r"Ran (\d+) tests", log)
    assert match and "OK" in log and "skipped=" not in log
    plan = json.loads((generated / "plan.json").read_text())
    capture = json.loads((generated / "capture-template.json").read_text())
    checked = evaluate(plan, capture, generated)
    assert not checked["physical_measurements_claimed"] and "measured_pass" not in checked["state_counts"]
    (out / "unmeasured-template-check.json").write_text(json.dumps(checked, indent=2) + "\n")
    evidence = [
        generated / "plan.json",
        generated / "capture-template.json",
        out / "parser-tests.txt",
        out / "unmeasured-template-check.json",
    ]
    sources = dict(plan["source_sha256"])
    test = REPO / "tests/tooling/test_qualification.py"
    sources[str(test.relative_to(REPO))] = digest(test)
    report = dict(
        revision="Q01",
        checked_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        scope="Source-bound bench plan, empty capture template and synthetic-only parser regressions; no physical test",
        source_base_commit=plan["source_base_commit"],
        plan_sha256=plan["plan_sha256"],
        planned_case_count=len(plan["cases"]),
        parser_tests_passed=int(match.group(1)),
        unmeasured_template_states=checked["state_counts"],
        source_sha256=sources,
        evidence_sha256={str(p.relative_to(REPO)): digest(p) for p in evidence},
        actual_measurements_performed=False,
        actual_measurement_cases_passed=0,
        full_unit_power_up_released=False,
        physical_power_verified=False,
        fabrication_or_compliance_released=False,
        build_ready=False,
        limitations=[
            "No assembled hardware or instruments have been confirmed; all physical cases are unrun or blocked",
            "Current E25, source redesign, downstream harness, peripheral and remaining-board holds remain",
            "Unqualified timing, analog dynamic, temperature and EMI limits cannot become measured_pass",
            "Raw artifact hashes protect integrity, not authenticity or waveform interpretation",
            "Firmware build/source linkage and actual flashed image remain operator attestations unless independently rebuilt/read back",
        ],
    )
    (out / "verification.json").write_text(json.dumps(report, indent=2) + "\n")
    print(
        f"Q01: {len(plan['cases'])} unmeasured cases; {report['parser_tests_passed']} parser regressions pass; physical release: false."
    )


if __name__ == "__main__":
    main()
