"""AX02 actual interface and pool equations; no unprovided table maximum invented."""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def analyze():
    old = json.loads((ROOT / "sources/AX01/analysis.json").read_text())
    vlo = old["POWER_RUN_value_comparisons"][0]["source_min_v"]
    # Conservative proposed joint receiving enclosure0.2ohm across2.52..2.70V,
    # -40..85C. Primary RON max0.12 at2.5V/fullT is not continuous-VIN proof.
    r_on = 0.2
    rs = 100 * 1.03
    loop = 250
    rd = 10000 * 0.97
    high = (vlo - (r_on + rs + loop) * 22e-6) / (1 + (r_on + rs + loop) / rd)
    on = (vlo / (100000 * 1.03) - (1 + 0.25 + 0.1) * 1e-6) / (1 / (100000 * 1.03) + 1 / (1000000 * 0.97))
    # The explicit pullup/pulldown replaces assumptions about internal smartPU/PD.
    por_load = 0.8 / (100000 * 0.97) + (1 + 0.1) * 1e-6
    reset_current = (2.7 - 0.25) / (100000 * 0.97) + (1 + 0.1) * 1e-6
    nonrail_extra_receiving = 0.001
    normal_bias = (
        nonrail_extra_receiving
        + 10e-6
        + 6.5e-6
        + (1 + 0.25 + 0.1) * 1e-6
        + 2.7 / (100000 * 0.97 + 1000000 * 0.97)
        + 2e-6
    )
    force_current = (2.7 + 22e-6 * rd) / (100 * 0.97 + loop + rd)
    leaf_guard = 1.2 * (normal_bias + force_current)
    leafshort_guard = 1.2 * (normal_bias + 2.7 / (100 * 0.97))
    # All three local input capacitors are explicit. CT is charged separately.
    inputmax = 10e-6 * 1.1 * 1.15 + 100e-9 * 1.1 * 1.15
    states = []
    for row in old["pool_scenarios"]:
        s = dict(row)
        if row["name"] == "fault_latched_internal_RUN_low":
            extra = 1.2 * (50e-6 + nonrail_extra_receiving)
        elif row["name"] in ["normal_steady", "positive_startup"]:
            extra = leaf_guard
        else:
            extra = leafshort_guard
        s["new_leaf_guarded_receiving_a"] = extra
        s["source_total_receiving_a"] = (
            row["E28_guarded_a"] + row["P03_guarded_a"] + row["NF_guarded_allocation_a"] + extra
        )
        s["unique_source_subtotal_a"] = (
            s["source_total_receiving_a"] - row["preserved_NF_full_reserve_headroom_a"]
        )
        s["margin_to90mA_a"] = 0.09 - s["source_total_receiving_a"]
        s["numerical_receiving_screen_inside90mA"] = s["source_total_receiving_a"] <= 0.09
        states.append(s)
    startup = next(x for x in states if x["name"] == "positive_startup")
    return dict(
        revision="AX02-integrated-voltage-RCB-leaf",
        selected_switch="TPS22913CYZVR",
        selected_controller="TPS389001DSET",
        native_switch_pin_contract={
            "A1": "SWITCHED_AUX",
            "A2": "AUX",
            "B1": "AGND",
            "B2": "RUN_GATE_COMMAND",
        },
        normal_HIGH_receiving_v=high,
        HIGH_target1p2_v=2.4,
        HIGH_margin_v=high - 2.4,
        ON_HIGH_receiving_v=on,
        primary_ON_VIH_min_v=1.1,
        ON_HIGH_target1p2_v=1.32,
        ON_LOW_primary_VIL_max_v=0.4,
        RESET_LOW_primary_VOL_max_v=0.25,
        ON_LOW_times1p2_v=0.3,
        independent_external_ON_pullup_ohm=100000,
        independent_external_ON_pulldown_ohm=1000000,
        no_internal_weak_pulldown_or_pullup_assumed=True,
        primary_ON_leak1uA_test_points="VON1.4..5.25V orGND; not guaranteed0.25V/partialVIN",
        receiving_ON_leak_at_all_intermediate_and_power_states_a=1e-6,
        POR_pull_current_times1p2_a=1.2 * por_load,
        POR_test_max_a=15e-6,
        RESET_LOW_sink_requirement_a=reset_current,
        RESET_primary_atVDDge1p5_sink_a=0.0004,
        original_internal_R113_preserved_ohm=3300,
        original_PG1mA_sink_comparison_a=old["conditional_new_leaf"]["PG_LOW_sink_current_upper_at_VOLp4_a"],
        original_PG_load_increased_by_external_E28=False,
        output_OFF_complete_leak_requirement_a=10e-6,
        output_OFF_plus_receiver_plus_board_total_a=32e-6,
        output_OFF_times1p2_v=1.2 * 32e-6 * 10300,
        primary_OFF_leak_row="IIN(max)5uA atVIN2.5,VOUT0; supply current includes device IQ, not a separately specified floating-output hotIOFF bound",
        switch_RON_receiving_max_ohm=r_on,
        primary_RON_scope="0.12ohm max atVIN2.5V/200mA/fullT; exact2.52..2.70V/lightload0.2ohm enclosure is receiving",
        primary_UVLO_rising_max_v=1.2,
        primary_UVLO_falling_min_v=0.50,
        primary_UVLO_table_test="VON0; risingIOUT-100mA/fallingRL10ohm. Do not extrapolate to every activeHIGH13C partial-power condition.",
        primary_recommended_supply_v=[1.4, 5.5],
        primary_ON_range_v=[0, 5.5],
        voltage_reverse_comparator=True,
        primary_VRCP_typical_v=0.044,
        primary_VRCP_max_v=None,
        primary_reverse_response_typical_s=10e-6,
        primary_reverse_response_max_s=None,
        primary_reverse_afterevent_leak_typical_at25C_a=0.3e-6,
        primary_reverse_afterevent_leak_max_a=None,
        primary_QOD_resistor_typical_ohm=153,
        primary_QOD_max_ohm_at3p3V25C=200,
        no_2p5V_hot_QOD_ceiling_claim=True,
        primary_switch_times_typical_only=True,
        full_loaded_cutoff_upper_s=None,
        below1p4V_all_state_OFF_leak_qualified=False,
        output_collapse_reverse_energy_and_hot_leak_qualified=False,
        discrete_common_source_bootstrap_eliminated=True,
        no_extra_regulator_or_RAW5_supply_required=True,
        normal_new_leaf_bias_raw_a=normal_bias,
        extra_nonrail_and_switching_current_receiving_a=nonrail_extra_receiving,
        extra_nonrail_and_switching_current_guaranteed=False,
        primary_IQ_enabled_condition_is_ON_equals_VIN_not_divided2p16V=True,
        normal_new_leaf_force_raw_a=force_current,
        normal_new_leaf_total_guarded_a=leaf_guard,
        short_new_leaf_total_guarded_a=leafshort_guard,
        pool_scenarios=states,
        existing_AUX_planning_pool_a=0.09,
        source_part_rating_a=0.1,
        no_source_pool_increase=True,
        full_current_temporal_correlation_qualified=False,
        input_cap=dict(
            selected_part="C3225X7R1E106K250AC",
            nominal_f=10e-6,
            required_effective_min_f=1e-6,
            actual_effective_bound_qualified=False,
            additional_supervisor_input_cap_nominal_f=100e-9,
            initial_and_positive_temperature_input_max_partial_inventory_f=inputmax,
            known_charge_to2p7_c=inputmax * 2.7,
            CT_nominal_f=10e-9,
            unknown_IC_internal_charge_and_output_capacitance=True,
            manufacturer_10to1_input_to_output_ratio_review_required=True,
            AUX_LDO_startup_slew_and_current_qualified=False,
            input_dVdt_to_fit_startup_planning_margin_v_per_s=startup["margin_to90mA_a"] / (1.2 * inputmax),
            ramp2p7_average_duration_only_diagnostic_s=1.2 * inputmax * 2.7 / startup["margin_to90mA_a"],
            diagnostic_is_NOT_full_AUXcap_or_peak_current_bound=True,
        ),
        package=dict(
            body_max_xy_mm=[0.918, 0.918],
            height_max_from_seating_plane_mm=0.5,
            ball_pitch_mm=0.5,
            physical_balls=["A1", "A2", "B1", "B2"],
            physical_ball_diameter_mm=[0.20, 0.25],
            assigned_land_diameter_mm=0.23,
            NSMD_mask_margin_mm=0.05,
            land_pattern_is_receiving_not_manufacturer_approval=True,
            C50_fabricator_and_assembly_pitch_process_approved=False,
        ),
        TPS22916_comparison_REJECTED=dict(
            reason="EnabledRCBactivation-500mAtypical;100ohm/250ohmseriespath cannot assume trip. SmartPD750ktypical has no minimum for weakpullup startup.",
            enabled_RCB_current_typical_a=-0.5,
            guaranteed_trip_upper_a=None,
        ),
        preserved_AX01_seal_sha256=sha(ROOT / "sources/AX01/handoff.json"),
        preserved_NF_full11_14mA_reserve=True,
        parent_actual_current_bound_not_promoted=True,
        schematic_implemented=True,
        PCB_implemented=False,
        adopted=False,
        partial_power_qualified=False,
        physical_qualified=False,
    )


if __name__ == "__main__":
    assert not (ROOT / "handoff.json").exists()
    a = analyze()
    (ROOT / "generated/analysis.json").write_text(json.dumps(a, indent=2) + "\n")
    print(
        json.dumps(
            {
                k: a[k]
                for k in [
                    "normal_HIGH_receiving_v",
                    "ON_HIGH_receiving_v",
                    "normal_new_leaf_total_guarded_a",
                    "pool_scenarios",
                ]
            },
            indent=2,
        )
    )
