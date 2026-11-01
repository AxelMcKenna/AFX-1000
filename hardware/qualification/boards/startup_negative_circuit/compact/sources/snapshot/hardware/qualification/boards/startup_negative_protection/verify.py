"""Seal the pre-native NF02 source/equation study; no physical acceptance."""

import json
import os
import subprocess
import sys

from .analyze import analyze
from .capture import REPO, ROOT, sha, write


def validate_handoff(path=None):
    path = path or ROOT / "handoff.json"
    h = json.loads(path.read_text())
    failures = [n for n, v in h["files_sha256"].items() if not (ROOT / n).is_file() or sha(ROOT / n) != v]
    assert not failures, failures
    return h


def seal():
    assert not (ROOT / "handoff.json").exists(), "Immutable handoff; use a successor"
    calculated = analyze()
    saved = json.loads((ROOT / "generated/analysis.json").read_text())
    assert calculated == saved, "Regenerate actual numerical report before sealing"
    p = subprocess.run(
        [
            sys.executable,
            "-m",
            "unittest",
            "hardware.qualification.boards.startup_negative_protection.test_nf02",
            "-v",
        ],
        cwd=REPO,
        env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONPATH=str(REPO)),
        capture_output=True,
        text=True,
        timeout=120,
    )
    log = ROOT / "generated/tests.log"
    log.write_text(p.stdout + p.stderr)
    assert p.returncode == 0, p.stdout + p.stderr
    write(
        ROOT / "generated/verification.json",
        dict(
            revision="NF02-source-bound-equations-before-native",
            scope="Analytical/source-integrity/mutation checks only; no fabricated physical evidence",
            tests_returncode=p.returncode,
            analytical_tests=15,
            test_log_sha256=sha(log),
            actual_p03_e28_native_exports=json.loads((ROOT / "sources/capture.json").read_text())[
                "native_exports"
            ],
            generated_analysis_sha256=sha(ROOT / "generated/analysis.json"),
            algebraic_normal_receiving_region=calculated["closed_algebraic_receiving_region"],
            complete_trajectory_or_fault_guarantee_established=False,
            native_new_schematic_authored=False,
            pcb_implemented=False,
            startup_qualified=False,
            soa_qualified=False,
            physical_qualified=False,
            fabrication_released=False,
            build_ready=False,
        ),
    )
    files = sorted(
        p
        for p in ROOT.rglob("*")
        if p.is_file() and p.name != "handoff.json" and "__pycache__" not in p.parts
    )
    write(
        ROOT / "handoff.json",
        dict(
            revision="NF02-pre-native-frozen",
            files_sha256={str(p.relative_to(ROOT)): sha(p) for p in files},
            total_files=len(files),
            entrypoints=[
                "README.md",
                "architecture.json",
                "PRIMARY-FACTS.md",
                "generated/analysis.json",
                "generated/verification.json",
            ],
            original_sources_changed=False,
            next_action="Parent review of equations, source/fault/partial-power requirements BEFORE any native circuit",
            native_new_schematic_authored=False,
            physical_qualified=False,
            startup_qualified=False,
            soa_qualified=False,
            fabrication_released=False,
            build_ready=False,
        ),
    )
    validate_handoff()
    print(
        "NF02 pre-native handoff sealed", len(files), "files; 15 analytical tests; physical acceptance FALSE"
    )


if __name__ == "__main__":
    seal()
