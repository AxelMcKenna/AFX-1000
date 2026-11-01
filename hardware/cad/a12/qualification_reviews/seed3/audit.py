"""Independent read-only numerical and inventory review of the sealed Seed packet."""

import csv
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[4]
PACKET = REPO / "hardware/cad/a12/harness/proposals/processor-awg18-ear-fanout-j29-central-seed"


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def read(p):
    return json.loads(p.read_text())


def main():
    handoff = read(PACKET / "handoff.json")
    assert len(handoff["files_sha256"]) == 41
    for n, h in handoff["files_sha256"].items():
        assert sha(PACKET / n) == h, n
    endpoint = read(PACKET / "generated/endpoint-R1.json")
    mechanical = read(PACKET / "generated/Seed3-applicability.json")
    for n, h in endpoint["source_sha256"].items():
        assert sha(PACKET / n) == h, n
    for n, h in mechanical["source_sha256"].items():
        assert sha(REPO / n) == h, n
    assert endpoint["VIN_operating_v"] == [4, 17]
    assert endpoint["one_ampere_retained_not_reduced"]
    assert endpoint["complete_source_to_Seed_guaranteed_interval_v"] is None
    assert not any(
        handoff[k]
        for k in ["physical_qualified", "fabrication_released", "complete_source_to_Seed_budget_qualified"]
    )
    assert handoff["same_value_R1_manufacturer_pattern_repair_pending"]
    r = next(x for x in endpoint["R1_candidates"] if x["mpn"] == "WSLT2512R4700FEA")
    # Independent I²R and additive test-condition scenario, not a lifetime bound.
    maximum_r = 0.47 * (1 + 0.01 + 75e-6 * 125 + 0.01 + 0.005)
    assert math.isclose(maximum_r, r["resistance_scenario_ohm"][1], abs_tol=1e-12)
    assert math.isclose(maximum_r, r["resistor_max_power_scenario_w"], abs_tol=1e-12)
    p70 = 1 - 0.2 * (0.47 - 0.1) / (0.5 - 0.1)
    p125 = p70 * (275 - 125) / (275 - 70)
    assert math.isclose(
        p125 / maximum_r, r["ambient_scenarios"][-1]["power_ratio_rating_to_load"], rel_tol=1e-12
    )
    assert p125 > 1.2 * maximum_r
    lower_intercept = (
        endpoint["source_voltage_interval_v"][0]
        - endpoint["source_dynamic_allocation_v"]
        - endpoint["local_spread_allocation_v"]
        - 2.4 * math.fsum(endpoint["source_to_receiver_design_resistances_ohm"].values())
        - max(endpoint["actual_new_E19_finite_fixture_copper_loop_v"])
        - maximum_r
    )
    assert math.isclose(lower_intercept, r["conditional_VIN_intercept_v"][0], abs_tol=1e-12)
    assert len(r["unknown_drop_or_ground_terms"]) >= 6 and not r["endpoint_or_thermal_qualified"]
    c = mechanical["controls"]
    assert len(c["per_solid_checks"]) == mechanical["STEP_solid_count"] == 445
    assert math.fsum(x["outside_mm3"] for x in c["per_solid_checks"]) == 0
    assert c["outside_complete_existing_reserve_mm3"] == 0
    assert c["outside_U1_box_only_positive_witness_mm3"] > 4
    assert math.isclose(c["beyond_complete_reserve_positive_witness_mm3"], 0.008, abs_tol=1e-8)
    assert len(mechanical["pads"]) == 40
    axes = mechanical["STEP_all40_hole_axes_xy_mm"]
    assert len(axes) == len(set(tuple(p) for p in axes)) == 40
    for row in mechanical["pads"]:
        expected = [row["carrier_local_mm"][i] + 1.42875 for i in [0, 1]]
        assert max(abs(x - y) for x, y in zip(expected, row["step_hole_axis_xy_mm"])) < 0.0001
    csvrows = list(csv.DictReader((PACKET / "sources/primary/Seed3_pinout.csv").read_text().splitlines()))
    pin40 = next(x for x in csvrows if x["PINOUT"] == "40")
    assert pin40["DAISY PIN NAME*"].strip() == "PG3" and pin40["PRIMARY FUNCTION"].strip() == "GND"
    assert not mechanical["forced_reserve_extension_required_by_this_nominal_evidence"]
    assert not mechanical["socket_contact_male_pin_insertion_and_assembly_tolerances_qualified"]
    result = dict(
        scope=__doc__,
        packet_handoff_sha256=sha(PACKET / "handoff.json"),
        sealed_file_hashes_checked=41,
        endpoint_source_hashes_checked=len(endpoint["source_sha256"]),
        mechanical_source_hashes_checked=len(mechanical["source_sha256"]),
        all_445_saved_per_solid_containment_results_zero=True,
        actual_40_pad_grid_recomputed=True,
        WSLT_maximum_R_scenario_ohm=maximum_r,
        WSLT_rating_over_load_at125C_ambient=p125 / maximum_r,
        conditional_voltage_intercept_only_v=lower_intercept,
        independent_saved_evidence_review_passed=True,
        independent_native_CAD_replay_performed=False,
        primary_datasheet_dimension_and_operating_range_review="Packet retains primary source and per-page basis; this script audits numerical evidence, not a new physical or vendor guarantee.",
        full_endpoint_qualified=False,
        physical_qualified=False,
        fabrication_released=False,
        script_sha256=sha(Path(__file__)),
    )
    (ROOT / "review.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
