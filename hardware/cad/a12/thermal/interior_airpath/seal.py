"""Seal scoped AP02 geometry evidence with the failed meter sensitivity explicit."""

import json

from .audit import errors
from .stage import OUT, ROOT, sha, write


def seal():
    target = ROOT / "handoff.json"
    if target.exists():
        raise RuntimeError("The sealed AP02 packet cannot be overwritten")
    bad = errors()
    if bad:
        raise RuntimeError("Cannot seal failed/stale saved evidence: " + repr(bad))
    tests = json.loads((OUT / "portable-tests.json").read_text())
    if tests["returncode"] or tests["tests_passed"] != 18:
        raise RuntimeError("Portable evidence tests did not pass")
    main = json.loads((OUT / "current-native/verification.json").read_text())
    seated = json.loads((OUT / "mating-seated/verification.json").read_text())
    pressure = json.loads((OUT / "pressure-rejection.json").read_text())
    files = {str(p.relative_to(ROOT)): sha(p) for p in ROOT.rglob("*")
             if p.is_file() and p != target and "__pycache__" not in p.parts and p.suffix != ".pyc"}
    write(target, dict(
        revision="AP02", candidate="Sunon/internal-airpath mechanical prototype; nominal125 meter pressure rejected",
        files_sha256=files, originals_modified=False,
        main_native_cases=len(main["cases"]), supplemental_native_seat_cases=len(seated["cases"]),
        all_requested_native_geometry_clear=True, portable_tests_passed=18,
        nominal125_meter_pressure_sensitivity_rejected=pressure["nominal125_base_target_rejected"],
        target_flows_m3_h=dict(total=10, interior=8.8, base=1.2),
        targets_are_requirements_not_results=True,
        installed_airflow_verified=False, airflow_target_met=False,
        physical_qualified=False, thermal_qualified=False, electrical_qualified=False,
        fabrication_released=False, structural_qualified=False, full_wiring_qualified=False,
        newer_electrical_or_wire_candidates_adopted=False,
        review_assemblies_promoted_as_manufacturable=False, adopted=False,
        strict_part_meshes_retained=True, complete_review_objects=21,
        actual_base_pins=918, actual_base_BREP_valid=True,
        parent_source_scope="HT01/FI01 captured scene: P03db83/E28fed45opens/E19central3b2a oldR1",
        history="Raw contact and float32 failures, rejected fixture trials and six no-CAD Docker failures retained",
    ))
    print(json.dumps(dict(files=len(files), handoff_sha256=sha(target))))


if __name__ == "__main__":
    seal()
