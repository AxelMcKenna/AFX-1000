"""Numerical/source controls; none establishes an installed thermal bound."""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def validate(r, check_files=True):
    assert abs(r["heat_target_w"] - 35.43154587633119) < 1e-10
    assert len(r["baseline_replay_controls"]) == 2
    assert max(abs(x["delta_to_sealed_WU01_c"]) for x in r["baseline_replay_controls"]) < 1e-8
    assert abs(r["FF02_baseline_lid_replay_delta_w"]) < 1e-8
    for row in r["enlarged_base_cases"]:
        v = row["result"]
        assert v["converged"] and abs(v["energy_balance_residual_w"]) < 1e-6
        assert abs(v["total_w"] - r["heat_target_w"]) < 1e-6
        assert not v["convection_or_assembly_qualified"]
    assert len(r["enlarged_base_refinement"]) == 2
    assert max(abs(x["peak_delta_c"]) for x in r["enlarged_base_refinement"]) < 0.15
    for row in r["new_metal_shell_prescribed_base_cases"]:
        v = row["result"]
        a = row["actual_captured_fin_projection"]
        assert v["converged"] and abs(v["conduction_and_surface_energy_residual_w"]) < 1e-6
        assert v["wall_height_mm"] == 43.6 and not v["installed_guarantee"]
        assert abs(a["vertical_area_residual_m2"]) < 1e-12
        assert abs(a["root_area_residual_m2"]) < 1e-12
        assert row["old_FF02_fins_XY_unchanged_no_front_fins"]
        assert not row["new_native_fin_geometry_or_control_clearance_pass"]
    assert not r["complete_new_geometry_or_conjugate_cooling_solution"]
    assert r["actual_thermal_capacity_upper_or_lower_w"] is None
    assert r["installed_h_lower_bound"] is None
    assert r["material_contact_or_model_uncertainty_bound"] is None
    assert not r["thermal_qualified"] and not r["fabrication_released"]
    assert r["physical_tests_performed"] == 0
    assert len(r["pin_centres_extended_proposal_mm"]) == 1037
    if check_files:
        for path, h in r["source_sha256"].items():
            assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == h, path


def main():
    r = json.loads((ROOT / "generated/thermal.json").read_text())
    validate(r)
    cap = json.loads((ROOT / "capture.json").read_text())
    for path, h in cap["source_sha256"].items():
        assert hashlib.sha256((ROOT / "sources" / path).read_bytes()).hexdigest() == h, path
    print(
        "All source, conservation, baseline and refinement controls pass; physical thermal release remains false"
    )


if __name__ == "__main__":
    main()
