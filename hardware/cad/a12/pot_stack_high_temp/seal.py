"""Immutable HT01 receiving-study handoff, with all approval holds retained."""

import json

from .audit import errors
from .stage import FI, OUT, ROOT, sha, write


def seal():
    if (ROOT / "handoff.json").exists():
        raise RuntimeError("The sealed receiving-study handoff cannot be overwritten")
    bad=errors()
    if bad:
        raise RuntimeError("Cannot seal failed/stale evidence: "+repr(bad))
    proof=json.loads((OUT / "full/verification.json").read_text())
    captured=json.loads((ROOT / "capture.json").read_text())
    files={str(p.relative_to(ROOT)):sha(p) for p in ROOT.rglob("*")
        if p.is_file() and p!=ROOT/"handoff.json" and "__pycache__" not in p.parts and p.suffix!=".pyc"}
    write(ROOT / "handoff.json",dict(
        revision="HT01",candidate="Alps RK09L1140A5L receiving study",files_sha256=files,
        parent_folder=str(FI),parent_handoff_sha256=captured["parent_handoff_sha256"],parent_files=620,parent_originals_modified=False,
        full_native_case_count=len(proof["cases"]),all_requested_native_clear=True,source_changes_during_native_run=[],
        native_role_counts={role:sum(r["role"]==role for r in proof["cases"].values()) for role in ["empty","part","review","witness","control"]},
        native_receipt_sha256=sha(OUT/"full/verification.json"),separate_preflight_case_count=16,
        portable_regression_tests=15,hardware_environment_pairs=60,actual_index_controls=10,
        round_panel_bores_mm=9.5,knob_base_mm=49.2,knob_outer_surfaces_changed=False,
        knob_blind_bore_depth_mm=10.8,knob_grub_axis_local_mm=5,
        new_named_blind_lug_pocket_mm=[2.4,1.8,1.1],minimum_nominal_own_bore_web_mm=.35,nominal_pocket_roof_mm=.9,
        required_local_substrate_mm=[16,16,1.6],substrate_top_z_mm=33.6,
        supplier_formal_drawing_and_unlabeled_tolerances_approved=False,
        supplied_washer_fit_and_nut_engagement_approved=False,substrate_lands_routes_strength_and_harness_complete=False,
        actual_control_calibration_and_electrical_compatibility_approved=False,
        installed_pot_temperature_verified=False,later_board_wire_fan_or_airpath_candidates_adopted=False,
        review_reserve_assemblies_promoted_as_manufacturable=False,
        whole_unit_electrical_qualified=False,full_wiring_qualified=False,structural_qualified=False,
        physical_qualified=False,thermal_qualified=False,fabrication_released=False,adopted=False,
    ))
    print(json.dumps(dict(files=len(files),handoff_sha256=sha(ROOT/"handoff.json"))))


if __name__=="__main__":
    seal()
