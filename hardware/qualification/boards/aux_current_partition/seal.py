"""Freeze AX01 evidence after actual native export and portable checks."""

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[3]


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    assert not (ROOT / "handoff.json").exists()
    commands = []
    for name, cmd in [
        ("native", [sys.executable, "-m", "hardware.qualification.boards.aux_current_partition.leaf.design"]),
        ("analysis", [sys.executable, "-m", "hardware.qualification.boards.aux_current_partition.analyze"]),
        (
            "tests",
            [
                sys.executable,
                "-m",
                "unittest",
                "hardware.qualification.boards.aux_current_partition.test_partition",
                "-v",
            ],
        ),
        (
            "ruff",
            [
                "/Users/axelmckrnna/.cache/uv/archive-v0/4FxQ2rYyAjvgsfLW/bin/ruff",
                "check",
                str(ROOT / "analyze.py"),
                str(ROOT / "test_partition.py"),
                str(ROOT / "leaf/design.py"),
                str(ROOT / "seal.py"),
            ],
        ),
    ]:
        result = subprocess.run(cmd, cwd=REPO, env=os.environ.copy(), capture_output=True, text=True)
        (ROOT / "generated" / (name + "-final.log")).write_text(result.stdout + result.stderr)
        commands.append(dict(name=name, command=cmd, returncode=result.returncode))
        if result.returncode:
            raise RuntimeError((name, result.returncode))
    files = {
        str(p.relative_to(ROOT)): sha(p)
        for p in sorted(ROOT.rglob("*"))
        if p.is_file()
        and "__pycache__" not in p.parts
        and p.name != "handoff.json"
        and not p.name.endswith(".lck")
    }
    result = dict(
        revision="AX01",
        status="SEALED_RECEIVING_EVIDENCE_NOT_ADOPTED",
        files_sha256=files,
        commands=commands,
        actual_native_schematic_parts=14,
        integrated_additions_proposed=12,
        portable_tests=10,
        native_ERC_findings=0,
        native_pin_value_mismatches=0,
        value_only_R113_repair_rejected=True,
        P03_PCB_unchanged=True,
        actual_current_upper_bound_a=None,
        bootstrap_and_partial_power_qualified=False,
        physical_qualified=False,
        fabrication_released=False,
    )
    (ROOT / "handoff.json").write_text(json.dumps(result, indent=2) + "\n")
    for p, h in files.items():
        assert sha(ROOT / p) == h, p
    print(
        json.dumps(
            dict(
                files=len(files),
                handoff_sha256=sha(ROOT / "handoff.json"),
                native_parts=14,
                portable_tests=10,
            )
        )
    )


if __name__ == "__main__":
    main()
