"""Seal FI01 after artifact, captured-source and distributed-coverage audit."""

import json

from .audit import errors
from .stage import OUT, ROOT, sha, write


def seal():
    if (ROOT / "handoff.json").exists():
        raise RuntimeError("A sealed handoff cannot be overwritten")
    bad = errors()
    if bad:
        raise RuntimeError("Cannot seal failed evidence: " + repr(bad))
    main = json.loads((OUT / "verification.json").read_text())
    coverage = json.loads((OUT / "effective-coverage.json").read_text())
    manifest = json.loads((OUT / "assembly-manifest.json").read_text())
    capture = json.loads((ROOT / "capture.json").read_text())
    files = {
        str(p.relative_to(ROOT)): sha(p)
        for p in ROOT.rglob("*")
        if p.is_file() and p != ROOT / "handoff.json" and "__pycache__" not in p.parts and p.suffix != ".pyc"
    }
    record = dict(
        revision="FI01",
        files_sha256=files,
        parents=capture["parents"],
        parent_originals_modified=False,
        captured_context_files=len(capture["derived_context_sha256"]),
        full_literal_declared_source_closure_captured=True,
        original_native_records=len(main["cases"]),
        original_native_checks_passed=161,
        original_native_attempt_all_passed=False,
        original_union_native_execution_completed=False,
        exact_union_retry_completed=False,
        two_exit_137_diagnostics_preserved=True,
        OOM_cause_proven=False,
        exact_distributive_pairs=60,
        index_specific_positive_controls=10,
        all_162_geometry_conditions_established=coverage[
            "complete_162_geometry_conditions_established_by_native_and_distributivity"
        ],
        direct_native_counts={
            role: sum(row["role"] == role for row in main["cases"].values())
            for role in ["part", "empty", "control", "review"]
        },
        nominal_seated_interface_native_cases=17,
        captured_rebound_native_cases=3,
        native_receipt_sha256=sha(OUT / "verification.json"),
        effective_coverage_sha256=sha(OUT / "effective-coverage.json"),
        portable_regression_tests=17,
        complete_component_review_objects=len(manifest["objects"]),
        complete_component_review_source_triangles=sum(o["triangles"] for o in manifest["objects"].values()),
        deleted_repaired_or_decimated_faces=0,
        whole_fused_model_promoted_as_manufacturable=False,
        actual_retained_pins=960,
        actual_removed_whole_pins=77,
        foot_screw="Accu SPK-M3-20-A2",
        nominal_foot_thread_engagement_mm=5.8,
        nominal_overall_height_mm=104.0,
        source_board_or_wire_replacements_adopted=False,
        FV01_5V_fan_or_higher_pressure_fan_adopted=False,
        internal_forced_air_path_implemented=False,
        installed_airflow_or_h_bound_established=False,
        whole_unit_electrical_qualified=False,
        full_wiring_qualified=False,
        structural_qualified=False,
        physical_qualified=False,
        thermal_qualified=False,
        fabrication_released=False,
    )
    write(ROOT / "handoff.json", record)
    print(json.dumps(dict(files=len(files), handoff_sha256=sha(ROOT / "handoff.json"))))


if __name__ == "__main__":
    seal()
