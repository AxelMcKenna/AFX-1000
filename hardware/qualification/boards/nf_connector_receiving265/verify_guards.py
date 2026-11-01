"""New local contact-only comparisons; original four strict failures retained."""

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

from hardware.qualification.boards.nf_connector_receiving265 import verify_mechanics

ROOT = Path(__file__).resolve().parent
CASES = {
    "front_seats_guarded": "empty",
    "thread_and_cap_washer_guarded": "empty",
    "back_washer_guarded": "empty",
    "base_cap_guarded": "empty",
    "front_1000nm_control": "control",
    "thread_tip_1000nm_control": "control",
    "cap_washer_1000nm_control": "control",
    "back_washer_1000nm_control": "control",
    "base_cap_1000nm_control": "control",
}


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def run(out):
    if out.exists():
        raise RuntimeError("Fresh guarded run required")
    audit = json.loads((ROOT / "mechanical-v2/facet-boundary-audit.json").read_text())
    if any(c["unresolved_triangle_indices"] for c in audit["cases"].values()):
        raise ValueError("Unclassified contact triangle")
    part_files = [
        ROOT / "ports-v2.json",
        ROOT / "mechanical-v2/geometry.scad",
        ROOT / "mechanical-v2/datums.json",
        ROOT / "mechanical-v2/native-run1/base_part.stl",
        ROOT / "mechanical-v2/native-run1/cap_part.stl",
    ]
    files = part_files + [
        ROOT / "mechanical-v2/guard_checks.scad",
        ROOT / "mechanical-v2/facet-boundary-audit.json",
        ROOT / "facet_audit.py",
        Path(__file__),
        Path(verify_mechanics.__file__),
        verify_mechanics.ENGINE,
    ]
    bindings = {str(p): sha(p) for p in files}
    out.mkdir()
    records = {}
    for name, role in CASES.items():
        target = out / (name + ".stl")
        cmd = [
            str(verify_mechanics.ENGINE),
            "--backend=Manifold",
            "--hardwarnings",
            "--export-format",
            "binstl",
            "-D",
            'guard_case="' + name + '"',
            "-o",
            str(target),
            str(ROOT / "mechanical-v2/guard_checks.scad"),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        log = out / (name + ".log")
        text = result.stdout + result.stderr
        log.write_text(text)
        row = dict(
            role=role,
            command=cmd,
            returncode=result.returncode,
            log_sha256=sha(log),
            STL_sha256=sha(target) if target.exists() else None,
        )
        if role == "empty":
            row["passed"] = (
                result.returncode == 1 and "Current top level object is empty" in text and not target.exists()
            )
        elif target.exists() and result.returncode == 0:
            row["mesh"] = verify_mechanics.mesh(target)
            row["expected_volume_mm3"] = 9.8e-6
            row["passed"] = (
                row["mesh"]["valid"]
                and "Status:     NoError" in text
                and abs(row["mesh"]["volume_mm3"] - 9.8e-6) < 2e-7
                and "WARNING" not in text
                and "ERROR" not in text
            )
        else:
            row["passed"] = False
        records[name] = row
        (out / "verification.json").write_text(
            json.dumps(dict(complete=False, cases=records, source_sha256=bindings), indent=2) + "\n"
        )
        print(name, row["passed"], flush=True)
    changed = [str(p) for p in files if sha(p) != bindings[str(p)]]
    d = dict(
        revision="NC265-local-contact-guard-successor",
        complete=True,
        cases=records,
        source_sha256=bindings,
        changed_inputs=changed,
        actual_parts_ports_datums_and_prior_STL_bytes_unchanged=not changed,
        guarded_comparisons_clear=not changed and all(r["passed"] for r in records.values()),
        original_strict_native_case_count=18,
        original_strict_failed_contact_cases=4,
        original_failures_not_rewritten=True,
        normal_test_guard_mm=20e-6,
        all5finite1000nm_intrusions_required=True,
        guard_is_NOT_assembly_factory_or_seating_tolerance_approval=True,
        physical_qualified=False,
        fabrication_released=False,
    )
    (out / "verification.json").write_text(json.dumps(d, indent=2) + "\n")
    raise SystemExit(not d["guarded_comparisons_clear"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    run(parser.parse_args().output.resolve())
