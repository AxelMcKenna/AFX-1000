"""Seal CP01 only after independent native/artifact/rebind audits pass."""

import json

from .audit import errors
from .stage import OUT, ROOT, sha, write


def seal():
    if (ROOT / "handoff.json").exists():
        raise RuntimeError("A sealed handoff cannot be overwritten")
    assert errors() == []
    report = json.loads((OUT / "verification.json").read_text())
    manifest = json.loads((OUT / "assembly-manifest.json").read_text())
    cap = json.loads((ROOT / "capture.json").read_text())
    files = {
        str(p.relative_to(ROOT)): sha(p)
        for p in ROOT.rglob("*")
        if p.is_file() and p != ROOT / "handoff.json" and "__pycache__" not in p.parts and p.suffix != ".pyc"
    }
    record = dict(
        revision="CP01",
        files_sha256=files,
        parents=cap["parents"],
        parent_originals_modified=False,
        full_literal_declared_source_closure_captured=True,
        captured_context_files=len(cap["derived_context_sha256"]),
        native_case_count=len(report["cases"]),
        native_counts={role: sum(row["role"] == role for row in report["cases"].values()) for role in ["part", "empty", "control", "review"]},
        all_main_native_checks_clear=report["all_native_checks_clear"],
        native_receipt_sha256=sha(OUT / "verification.json"),
        source_captured_rebound_native_cases=3,
        actual_overlap_annulus_and_void_native_witnesses=2,
        supplemental_native_proofs_checked=True,
        complete_component_review_objects=len(manifest["objects"]),
        complete_component_review_source_triangles=sum(o["triangles"] for o in manifest["objects"].values()),
        deleted_repaired_or_decimated_faces=0,
        whole_fused_model_promoted_as_manufacturable=False,
        EB01_thread_interval_and_replay_errata_bound=True,
        capture_refuses_sealed_or_existing_destination=True,
        captured_replay_rebind_supported=True,
        sealed_original_output_overwrites_refused=True,
        source_board_or_wire_replacements_adopted=False,
        forced_air_or_metal_walls_adopted=False,
        whole_unit_electrical_qualified=False,
        full_wiring_qualified=False,
        structural_qualified=False,
        physical_qualified=False,
        thermal_qualified=False,
        fabrication_released=False,
    )
    write(ROOT / "handoff.json", record)
    print(json.dumps(dict(files=len(files), native_cases=len(report["cases"]), handoff_sha256=sha(ROOT / "handoff.json"))))


if __name__ == "__main__":
    seal()
