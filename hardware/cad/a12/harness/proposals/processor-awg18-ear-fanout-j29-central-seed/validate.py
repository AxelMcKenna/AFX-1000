"""Guards for the specific source-bound Seed3 diagnostics and unaccepted terms."""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[5]


def validate(e, m, files=True):
    assert e["selected_module"] == "DaisySeed3" and e["VIN_operating_v"] == [4, 17]
    assert "Table3" in e["VIN_operating_basis"] and "NOT" in e["VIN_operating_basis"]
    assert e["one_ampere_retained_not_reduced"]
    assert e["complete_source_to_Seed_guaranteed_interval_v"] is None
    assert (
        not e["complete_endpoint_and_R1_thermal_qualified"]
        and not e["physical_qualified"]
        and not e["fabrication_released"]
    )
    assert len(e["unknown_signed_ground_socket_and_network_terms"]) >= 6
    wslt = next(r for r in e["R1_candidates"] if r["mpn"] == "WSLT2512R4700FEA")
    assert wslt["load_a"] == 1 and wslt["nominal_ohm"] == 0.47
    assert abs(wslt["manufacturer_P70_after_high_R_derating_w"] - 0.815) < 1e-12
    assert 4.39 < wslt["conditional_VIN_intercept_v"][0] < 4.40
    assert wslt["total_drift_is_not_mission_life_guarantee"] and not wslt["endpoint_or_thermal_qualified"]
    assert wslt["ambient_scenarios"][-1]["power_ratio_rating_to_load"] >= 1.2
    assert e["recommendation"]["same_nominal_R_preserves_RC"]
    assert not e["recommendation"]["manufacturer_pad_to_existing_alternate_assembly_approval"]
    st = e["startup"]
    assert {c["ref"] for c in st["actual_local_capacitors"]} == {"C1", "C2"}
    assert not st["capacitor_MPNs_effective_C_ESR_and_maximums_accepted"]
    assert st["complete_module_input_capacitance_and_internal_regulator_part_unverified"]
    assert (
        st["late_closure_unlimited_R1_peak_w"] > 50
        and st["whole_source_startup_guard_feed_and_module_boot_not_qualified"]
    )
    assert (
        m["STEP_solid_count"] == 445 and len(m["pads"]) == 40 and len(m["STEP_all40_hole_axes_xy_mm"]) == 40
    )
    assert max(r["step_nominal_grid_difference_mm"] for r in m["pads"]) < 0.0001
    assert m["receiving_plane_is_not_approved_assembly_max"] and not m["physical_qualified"]
    assert (
        m["prior_U1_only_gap_claim_superseded"]
        and not m["forced_reserve_extension_required_by_this_nominal_evidence"]
    )
    c = m["controls"]
    assert len(c["per_solid_checks"]) == 445
    assert (
        c["outside_complete_existing_reserve_mm3"] < 1e-6
        and c["outside_U1_box_only_positive_witness_mm3"] > 4
    )
    assert c["beyond_complete_reserve_positive_witness_mm3"] > 0.0079
    assert m["CSV_pin40_DAISY_name_PG3_disagrees_with_PDF_DGND_but_primary_function_GND"]
    if files:
        for rel, h in e["source_sha256"].items():
            assert hashlib.sha256((ROOT / rel).read_bytes()).hexdigest() == h, rel
        for rel, h in m["source_sha256"].items():
            assert hashlib.sha256((REPO / rel).read_bytes()).hexdigest() == h, rel


if __name__ == "__main__":
    validate(
        json.loads((ROOT / "generated/endpoint-R1.json").read_text()),
        json.loads((ROOT / "generated/Seed3-applicability.json").read_text()),
    )
    print("Seed3source/current/geometry/conditionalqualification guards clear")
