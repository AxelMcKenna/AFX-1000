"""Freeze EB01 files only after strict artifact and assembly checks succeed."""

import json

from .audit import errors
from .stage import OUT, REPO, ROOT, sha, write


def seal():
    assert errors() == [], "Cannot seal stale/failed/incomplete evidence"
    native = json.loads((OUT / "verification.json").read_text())
    assembly = json.loads((OUT / "assembly-manifest.json").read_text())
    cad = json.loads((OUT / "cad-verification.json").read_text())
    capture = json.loads((ROOT / "capture.json").read_text())
    files = {
        str(p.relative_to(ROOT)): sha(p)
        for p in ROOT.rglob("*")
        if p.is_file()
        and p != ROOT / "handoff.json"
        and "__pycache__" not in p.parts
        and p.suffix != ".pyc"
    }
    live_changed = [
        n
        for n, h in capture["original_sha256"].items()
        if not (REPO / n).exists() or sha(REPO / n) != h
    ]
    result = dict(
        revision="EB01",
        files_sha256=files,
        source_original_capture_count=len(capture["original_sha256"]),
        derived_context_count=len(capture["derived_context_sha256"]),
        original_live_changes_at_seal=live_changed,
        native_case_count=len(native["cases"]),
        all_required_native_checks_clear=native["all_requested_native_checks_clear"],
        native_receipt_sha256=sha(OUT / "verification.json"),
        complete_ten_object_review_assembly=assembly["complete_component_review_present"],
        all_source_faces_preserved=assembly["deleted_or_decimated_or_repaired_faces"] == 0,
        new_production_meshes_closed_oriented_nonzero=True,
        exact_STEP_roundtrip_valid=cad["step_roundtrip_valid"],
        whole_fused_STL_OFF_3MF_valid=False,
        fused_failure_history_preserved=True,
        whole_unit_is_one_fabricable_part=False,
        interface_seating_scope="Nominal P03bottom6.5, matched.2shim and1.22compressed TIM; wider range/process unqualified",
        other_candidates_PS01_FA01_adopted=False,
        whole_unit_electrical_source_closed=False,
        full_wiring_qualified=False,
        thermal_qualified=False,
        structural_qualified=False,
        physical_qualified=False,
        fabrication_released=False,
    )
    write(ROOT / "handoff.json", result)
    print(json.dumps(dict(files=len(files), native_cases=len(native["cases"]), live_changes=live_changed, handoff_sha256=sha(ROOT / "handoff.json"))))


if __name__ == "__main__":
    seal()
