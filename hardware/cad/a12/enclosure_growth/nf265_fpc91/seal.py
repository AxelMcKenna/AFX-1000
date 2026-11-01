"""Seal an explicit rejected milestone; no all-clear or qualification promotion."""

import json
from pathlib import Path

from .audit import check
from .capture import ROOT, sha, write


def seal():
    target = ROOT / "handoff.json"
    if target.exists():
        raise RuntimeError("Never overwrite sealed handoff")
    audit = check()
    assert audit["saved_evidence_integrity_clear"], audit["errors"]
    for n in ["generated/tests-python39-seal.log", "generated/tests-python312-seal.log"]:
        text = (ROOT / n).read_text()
        assert "Ran 13 tests" in text and "\nOK\n" in text and "FAILED" not in text
    write(ROOT / "generated/integrity-at-seal.json", audit)
    files = {
        str(p.relative_to(ROOT)): sha(p)
        for p in sorted(ROOT.rglob("*"))
        if p.is_file() and "__pycache__" not in p.parts and p.name != ".DS_Store"
    }
    write(
        target,
        dict(
            revision="NR01-NF265-FPC91-rejected-receiving-milestone",
            files_sha256=files,
            files=len(files),
            electrical_parts=356,
            native_FPs=358,
            source_NF_PCB_sha256="2b64a1502e4fac8623aaf4caed92b27c8b7313b6b93e0a8e927f3630dbced9d5",
            source_FPC_PCB_sha256="f8ecaee75e789ef53c28b2b347babefab16fff9297b2a6849666a90fed360e74",
            initial_native_unique_cases=47,
            initial_clear=42,
            initial_rejected=5,
            exact_rectangular_tail_replay_cases=47,
            exact_tail_replay_clear=42,
            exact_tail_replay_rejected=5,
            actual_source_primary_body_supplements=6,
            supplements_clear=6,
            portable_tests_per_runtime=13,
            portable_runtimes=["3.9.6", "3.12.13"],
            source_NF_uncapped_native_opens=750,
            source_NF_capped_JSON_opens=499,
            old_E28_snapshot_opens=32,
            source_is_captured_snapshot_not_latest_whole_unit=True,
            all_receiving_geometry_clear=False,
            selected_C401_C402_actual_body_tail_margin_clear=True,
            selected_connectors_and_process_accepted=False,
            PH1p76_board_applicability="FAILED",
            physical_qualified=False,
            electrical_qualified=False,
            thermal_qualified=False,
            full_harness_qualified=False,
            fabrication_released=False,
            production_adopted=False,
            parent_seals_or_boards_edited=False,
        ),
    )
    assert all(sha(ROOT / n) == h for n, h in files.items())
    print(json.dumps(dict(files=len(files), handoff_sha256=sha(target), all_receiving_geometry_clear=False)))


if __name__ == "__main__":
    seal()
