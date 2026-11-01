"""Portable, independently source-bound verification successor to NP01."""

import argparse
import hashlib
import json
import platform
import tempfile
from pathlib import Path

from hardware.qualification.boards.nf_passive_selection import (
    audit,
    lifetime,
    selection,
)
from hardware.qualification.boards.nf_passive_selection import (
    verify as old_verify,
)
from hardware.qualification.boards.nf_passive_selection_portable import capture_runtime, policy

ROOT = Path(__file__).resolve().parent
PARENT = ROOT.parent / "nf_passive_selection"


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def reference():
    d = json.loads((PARENT / "analyses/analysis.json").read_text())
    life = json.loads((PARENT / "analyses/lifetime-scenarios.json").read_text())
    return dict(
        selection=d["selections"],
        lifetime={k: v for k, v in life.items() if k != "source_sha256"},
        monitor=d["monitor_scenarios"],
        power=d["DC_power_screens"],
    )


def runtime_payload():
    with tempfile.TemporaryDirectory(prefix="np01-portable-") as tmp:
        p = Path(tmp) / "selection"
        selection.build(p)
        selected = json.loads((p / "selections.json").read_text())
    parts = json.loads((PARENT / "sources/NF261/components.json").read_text())
    parameters = json.loads((PARENT / "sources/reference-baseline/parameters.json").read_text())
    return dict(
        selection=selected,
        lifetime=lifetime.analysis(),
        monitor=audit.monitor_scenarios(parts, parameters),
        power=audit.dc_power_screens(),
    )


def check():
    parent = capture_runtime.check_parent()
    errors, accepted = policy.compare(reference(), runtime_payload())
    inherited = old_verify.saved_errors()
    # Only this known legacy exact-float message can be superseded, and only
    # after the complete four-model payload independently passes this policy.
    allowed_legacy = {"Saved additional life scenarios disagree with recalculation"} if not errors else set()
    other = [s for s in inherited if s not in allowed_legacy]
    errors += [dict(reason=s) for s in other]
    capture_runtime.check_parent()
    return dict(
        revision="NP01-P1-portable-replay",
        runtime=platform.python_version(),
        original_parent_seal_sha256=capture_runtime.EXPECTED,
        parent_files_verified=len(parent["files_sha256"]),
        policy_MAX_ULP_steps=policy.MAX_ULP_STEPS,
        structural_inputs_geometry_hashes_and_flags_exact=True,
        accepted_computed_sum_differences=accepted,
        errors=errors,
        legacy_exact_comparison_failures_preserved=inherited,
        physical_qualified=False,
        electrical_qualified=False,
        fabrication_released=False,
        source_sha256={
            str(p): sha(p) for p in [Path(__file__), Path(policy.__file__), Path(capture_runtime.__file__)]
        },
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.output and args.output.exists():
        raise RuntimeError("Fresh report required")
    report = check()
    if args.output:
        args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(
        json.dumps(
            dict(
                runtime=report["runtime"],
                errors=report["errors"],
                accepted_computed_sum_differences=len(report["accepted_computed_sum_differences"]),
            )
        )
    )
    raise SystemExit(bool(report["errors"]))
