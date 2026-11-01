"""Seal immutable candidate packet without promoting a physical qualification."""

import json

from hardware.cad.a12.thermal.generate import REPO, sha

from .generate import OUT, ROOT


def main():
    analysis = json.loads((OUT / "analysis.json").read_text())
    native = json.loads((OUT / "verification.json").read_text())
    diagnostic = json.loads((ROOT / "sources/current-native.json").read_text())
    assert diagnostic["pcb_sha256"] == analysis["native_candidate_pcb_sha256"]
    assert diagnostic["diagnostic_sha256"] == sha(ROOT / "sources/route-drc.json")
    assert native["accepted_native_evidence"] and not native["failed_cases"]
    assert not analysis["whole_path_acceptance"]["guardbanded110c_accepted"]
    sources = [p for p in ROOT.iterdir() if p.is_file() and p.suffix in {".py", ".md"}] + list(
        (ROOT / "sources").iterdir()
    )
    evidence = [p for p in OUT.iterdir() if p.is_file()]
    report = dict(
        revision="U102-nine-via-wider-packet",
        source_sha256={str(p.relative_to(REPO)): sha(p) for p in sorted(sources)},
        evidence_sha256={str(p.relative_to(REPO)): sha(p) for p in sorted(evidence)},
        actual_native_geometry_cases=5,
        native_geometry_cases_passed=5,
        pcb_only_drc_violations=diagnostic["native_drc_violations"],
        pcb_open_connections=diagnostic["native_open_connections"],
        fresh_candidate_erc_and_parity=False,
        authoritative_reports=[
            "generated/analysis.json",
            "generated/verification.json",
            "sources/current-native.json",
        ],
        exploratory_history_is_not_an_acceptance_record=True,
        physical_tests_performed=0,
        physical_fit_verified=False,
        thermal_path_qualified=False,
        guardbanded110c_accepted=False,
        canonical_pcb_modified=False,
        frozen_heat_kit_modified=False,
        fabrication_released=False,
        build_ready=False,
    )
    (ROOT / "handoff.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
