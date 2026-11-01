"""Freeze AX02 source-backed schematic receiving proposal without parent edits."""

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
    parent = ROOT.parent / "aux_current_partition"
    h = json.loads((parent / "handoff.json").read_text())
    assert (parent / "handoff.json").read_bytes() == (ROOT / "sources/AX01/handoff.json").read_bytes()
    for p, d in h["files_sha256"].items():
        assert sha(parent / p) == d, p
    commands = []
    for name, cmd in [
        (
            "native",
            [sys.executable, "-m", "hardware.qualification.boards.aux_current_partition_followup.design"],
        ),
        (
            "analysis",
            [sys.executable, "-m", "hardware.qualification.boards.aux_current_partition_followup.analyze"],
        ),
        (
            "tests",
            [
                sys.executable,
                "-m",
                "unittest",
                "hardware.qualification.boards.aux_current_partition_followup.test_followup",
                "-v",
            ],
        ),
        (
            "ruff",
            [
                "/Users/axelmckrnna/.cache/uv/archive-v0/4FxQ2rYyAjvgsfLW/bin/ruff",
                "check",
                str(ROOT / "analyze.py"),
                str(ROOT / "design.py"),
                str(ROOT / "test_followup.py"),
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
    report = dict(
        revision="AX02",
        status="SEALED_SCHEMATIC_RECEIVING_SUCCESSOR_NOT_ADOPTED",
        files_sha256=files,
        commands=commands,
        parent_AX01_handoff_sha256=sha(parent / "handoff.json"),
        parent78files_reverified_unchanged=True,
        actual_native_schematic_parts=10,
        integrated_proposed_additions=8,
        native_ERC=0,
        native_pin_value_mismatches=0,
        portable_tests=9,
        no_original_PCB_changed=True,
        no_AUX_pool_increase=True,
        normal_guarded_source_a=0.08209733817623263,
        startup_guarded_source_a=0.08540154436179964,
        failed_short_transient_and_overlap_preserved=True,
        loaded_cutoff_upper_s=None,
        full_current_hot_partial_power_reverse_qualified=False,
        PCB_implemented=False,
        physical_qualified=False,
        fabrication_released=False,
        adopted=False,
    )
    (ROOT / "handoff.json").write_text(json.dumps(report, indent=2) + "\n")
    for p, d in files.items():
        assert sha(ROOT / p) == d, p
    print(
        json.dumps(
            dict(
                files=len(files), handoff_sha256=sha(ROOT / "handoff.json"), native_parts=10, portable_tests=9
            )
        )
    )


if __name__ == "__main__":
    main()
