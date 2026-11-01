"""CH20 geometry, normalization, source and conservation guards; no physical pass."""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def validate(r, check_files=True):
    assert r["retained_heat_w"] == 35.43154587633119
    assert abs(r["stress_heat_w"] - 1.2 * r["retained_heat_w"]) < 1e-10
    assert r["stress_is_planning_diagnostic_not_measured_upper"]
    assert not r["prescribed_uniform_base_temperature"] and r["source_loaded_coupling_solved"]
    g = r["geometry"]
    assert abs(g["wall_remaining_area_mm2"] - 37666.88) < 1e-6 and g["wall_removed_area_mm2"] == 7886.4
    assert not g["rear_cassette_bridge_credited"] and not g["fin_radiation_extra_credit"]
    assert g["lid_sheet_graph_components"] == 1 and g["lid_nodes_with_multiple_components"] == 34
    assert (
        g["no_link_between_separate_same_cell_components"]
        and g["all_separate_cell_metal_components_separate_nodes"]
    )
    assert abs(g["native_lid_metal_area_mm2"] - g["cell_component_metal_area_mm2"]) < 1e-6
    assert abs(g["actual_fin_vertical_area_m2"] - g["distributed_fin_vertical_area_m2"]) < 1e-12
    assert len(r["decoupled_controls"]) == 4 and len(r["loaded_cases"]) == 16
    for c in r["decoupled_controls"]:
        assert abs(c["delta_c"]) < 1e-7
        v = c["decoupled"]
        assert v["decoupled_base_wall"] and v["conduction_graph_components"] == 2
        assert abs(v["lid_peak_c"] - 40) < 1e-6 and abs(v["wall_peak_c"] - 40) < 1e-6
        assert abs(v["contact_pure_conductance_w_per_k"]["base_wall"]) < 1e-12
    for item in r["loaded_cases"] + [r["double_joint_single_sensitivity"]]:
        v = item["result"]
        assert v["converged"] and v["conduction_graph_components"] == 1
        assert abs(v["energy_residual_w"]) < 1e-6 and v["max_node_balance_residual_w"] < 1e-6
        assert (
            abs(sum(v["losses_w"][k] for k in ["base", "walls", "lid_and_fins"]) - v["source_heat_w"]) < 1e-6
        )
        assert abs(v["source_heat_w"] - r["retained_heat_w"] * v["heat_scale"]) < 1e-10
        assert (
            not v["base_temperature_prescribed"]
            and not v["thermal_qualified"]
            and not v["physical_qualified"]
        )
        assert sum(v["contact_reference_r_k_per_w"]) == v["total_contact_reference_r_k_per_w"]
        for key, R in zip(["base_wall", "wall_lid"], v["contact_reference_r_k_per_w"]):
            assert abs(v["contact_pure_conductance_w_per_k"][key] - 1 / R) < 1e-8
        assert v["contact_normalization"]["actual_lid_seat_contact_area_mm2"] == g["contact_area_mm2"]
    assert r["double_joint_single_sensitivity"]["result"]["contact_reference_r_k_per_w"] == [0.2, 0.2]
    assert all(v["result"]["contact_reference_r_k_per_w"] == [0.1, 0.1] for v in r["loaded_cases"])
    assert not r["spatial_refinement_performed"] and not r["optimization_performed"]
    assert not r["new_native_metal_parts_matched"] and not r["qualified20percent_margin"]
    assert not r["thermal_qualified"] and not r["fabrication_released"] and r["physical_tests_performed"] == 0
    if check_files:
        for rel, h in r["source_sha256"].items():
            assert hashlib.sha256((ROOT / rel).read_bytes()).hexdigest() == h, rel


if __name__ == "__main__":
    validate(json.load(open(ROOT / "generated/analysis.json")))
    print("Source-loaded/geometry/contact-normalization/conservation controls pass; no thermal qualification")
