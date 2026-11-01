"""One-shot UA01 snapshot seal after actual saved-artifact/mutation validation."""

import json
from pathlib import Path

from . import audit
from .ground_route import ROOT, sha, write


def seal():
    target = ROOT / "handoff.json"
    if target.exists():
        raise RuntimeError("The UA01 snapshot is immutable")
    errors = audit.errors()
    if errors:
        raise RuntimeError(errors)
    tests = (ROOT / "generated/portable-tests.log").read_text()
    if "Ran 15 tests" not in tests or not tests.rstrip().endswith("OK"):
        raise RuntimeError("The complete15-test terminal result is required")
    files = {
        str(p.relative_to(ROOT)): sha(p)
        for p in sorted(ROOT.rglob("*"))
        if p.is_file() and "__pycache__" not in p.parts and p.name != ".DS_Store"
    }
    data = dict(
        revision="UA01-R04-PB27-source32-captured-review",
        files_sha256=files,
        files=len(files),
        main_native_42=dict(passed=41, failed=1, failed_case=audit.BLOCKED),
        failed_guide_case_preserved=True,
        new_service_state_native=8,
        all_new_service_state_checks_pass=True,
        fresh_review_native_exports=2,
        portable_tests=15,
        assembly_objects=70,
        assembly_triangles=856846,
        assembly_is_separate_object_review=True,
        whole_as_one_manufacturable_part=False,
        actual_CAD_part_shapes=49,
        collision_receiving_meshes=3,
        E28=dict(identity="sealed32/dd6a6f5a", electrical_opens=32, latest_development_adopted=False),
        P03_identity="aux-u10-combined/db83",
        E19_identity="central-r1/dc559bd9",
        ground_source_world_mm=[161, 129.5, 6.62],
        ground_receiver_world_mm=[188, 104, 8.1],
        service_state="lid plus guide/control cohort removed; other-controls-present conservative fixture clear; physical removal path and harness slack unqualified",
        NF03P_FPC01_U35_later_routing_or_new_J8wire_adopted=False,
        source_is_captured_snapshot_not_latest_whole_unit=True,
        physical_qualified=False,
        electrical_qualified=False,
        thermal_qualified=False,
        installed_airflow_qualified=False,
        full_wiring_qualified=False,
        fabrication_released=False,
        production_adopted=False,
    )
    write(target, data)
    assert all(sha(ROOT / n) == h for n, h in files.items())
    print(json.dumps(dict(files=len(files), handoff_sha256=sha(target), main42="41 pass,1 blocked guide", service8="all pass", release=False)))


if __name__ == "__main__":
    seal()
