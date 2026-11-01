"""Seal strict native geometry evidence; never promote the parent or physics."""

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[5]
PARENT = ROOT.parent / "aux-u10-combined"


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    assert not (ROOT / "handoff.json").exists()
    original = {
        str(p.relative_to(PARENT)): sha(p)
        for p in sorted(PARENT.rglob("*"))
        if p.is_file() and "__pycache__" not in p.parts
    }
    assert (
        sha(PARENT / "power_p03.kicad_pcb")
        == "db83a26f98e3638d7b1a723be5d54f71c4e3aaa5418021e5b9003afea810283d"
    )
    commands = []
    for name, cmd in [
        ("native", [sys.executable, str(ROOT / "verify.py")]),
        ("front-paths", [sys.executable, str(ROOT / "front_paths.py")]),
        ("tests", [sys.executable, str(ROOT / "test_contract.py"), "-v"]),
        ("reproduction", [sys.executable, str(ROOT / "reproduce.py")]),
        (
            "ruff",
            [
                "/Users/axelmckrnna/.cache/uv/archive-v0/4FxQ2rYyAjvgsfLW/bin/ruff",
                "check",
                *[
                    str(ROOT / n)
                    for n in ["verify.py", "front_paths.py", "reproduce.py", "test_contract.py", "seal.py"]
                ],
            ],
        ),
    ]:
        p = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True)
        (ROOT / "generated" / f"{name}-final.log").write_text(p.stdout + p.stderr)
        commands.append(dict(name=name, command=cmd, returncode=p.returncode))
        assert p.returncode == 0, (name, p.stderr)
    for n, d in original.items():
        assert sha(PARENT / n) == d, n
    (ROOT / "generated/parent-unchanged.json").write_text(
        json.dumps(
            dict(
                parent=str(PARENT.relative_to(REPO)),
                all_original_files_sha256=original,
                all_reverified_unchanged=True,
            ),
            indent=2,
        )
        + "\n"
    )
    files = {
        str(p.relative_to(ROOT)): sha(p)
        for p in sorted(ROOT.rglob("*"))
        if p.is_file() and "__pycache__" not in p.parts and p.name != "handoff.json"
    }
    h = dict(
        status="READY_PRIVATE_STRICT_NATIVE_GEOMETRY_NOT_RELEASED",
        source_parent_pcb_sha256=original["power_p03.kicad_pcb"],
        candidate_pcb_sha256=sha(ROOT / "power_p03.kicad_pcb"),
        files_sha256=files,
        commands=commands,
        strict_native_counts=dict(ERC=0, DRC=0, warnings=0, parity=0, opens=0, uncapped_opens=0),
        ignored_checks=[],
        all_original256parts_266FPs_1254vias_preserved=True,
        all16_original_buck_direct_links_exact=True,
        six_actual_front_authored_paths_present=True,
        old_AUXliteral_checker_failure_preserved=True,
        explicit_P19_two_0p6mm_neck_proposal=True,
        eight_portable_tests=True,
        AX02_not_integrated_POWER_RUN_threshold_unrepaired=True,
        source_ground_thermal_and_endpoint_results_not_inherited=True,
        process_metadata_and_physical_acceptance_unresolved=True,
        physical_qualified=False,
        fabrication_released=False,
        adopted=False,
    )
    (ROOT / "handoff.json").write_text(json.dumps(h, indent=2) + "\n")
    for n, d in files.items():
        assert sha(ROOT / n) == d, n
    print(
        json.dumps(
            dict(
                files=len(files),
                handoff_sha256=sha(ROOT / "handoff.json"),
                candidate_pcb_sha256=h["candidate_pcb_sha256"],
            )
        )
    )


if __name__ == "__main__":
    main()
