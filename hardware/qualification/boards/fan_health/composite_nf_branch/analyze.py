"""Source-bound third-branch/current/inrush/voltage receiving comparisons."""

import hashlib
import json
import re

from hardware.electronics.common.netlists import netlist

from .circuit import ROOT


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def current_interval(ohm, tolerance):
    if not 15000 <= ohm * (1 - tolerance) <= ohm * (1 + tolerance) <= 232000:
        raise ValueError("Actual complete resistor leaves primary15..232k stable region")
    return [
        25230 / (ohm * (1 + tolerance) / 1000) ** 1.016 / 1000,
        22980 / (ohm * (1 - tolerance) / 1000) ** 0.94 / 1000,
    ]


def analyze():
    actual, pins = netlist(ROOT / "generated/netlist.xml")
    assert len(actual) == 91
    raw = actual["R401"].findtext("value")
    m = re.match(r"([\d.]+)k", raw)
    r = float(m.group(1)) * 1000
    interval = current_interval(r, 0.01)
    assert pins["U401"] == {
        "1": "FAN5V_IN",
        "2": "GND",
        "3": "FAN5V_IN",
        "4": pins["U401"]["4"],
        "5": "NF_RAW5_ILIM",
        "6": "NF_RAW5",
    }
    assert pins["U401"]["4"].startswith("unconnected-")
    nf = json.loads((ROOT / "sources/NF05R/generated/analysis.json").read_text())
    load = nf["power"]["NF_RAW5_guarded_a"]
    # This is a conservative receiving provision, not an unsupported transfer
    # of the6.5V/210k120uA primary IQ row to220k/arbitraryhot/local voltage.
    iq = 0.000150
    en = 0.0000005
    cap_board_leak = 0.000005
    extra = 1.2 * (iq + en + cap_board_leak)
    known = nf["power"]["full_known_DIG_guarded_a"] + extra
    fpc_input = known - 1.984
    cap_rows = []
    for ref in ["C401", "C402", "C403", "C404"]:
        assert "C0603C104K5RACTU" in actual[ref].findtext("value")
        cap_rows.append(
            dict(
                ref=ref,
                native_value=actual[ref].findtext("value"),
                nets=pins[ref],
                effective_minimum_receiving_f=60e-9,
                initial_plus_positive_temp_partial_max_f=100e-9 * 1.10 * 1.15,
            )
        )
    nf_cap = nf["RAW5_branch_startup"]["known_external_partial_subtotal_f"]
    new_in = sum(c["initial_plus_positive_temp_partial_max_f"] for c in cap_rows[:2])
    new_out = sum(c["initial_plus_positive_temp_partial_max_f"] for c in cap_rows[2:])
    # Input caps charge upstream of the limiter; keep them OUT of its charge
    # time, but IN the source input-capacitance/inrush inventory.
    known_limited_cap = new_out + nf_cap
    all_cap = new_in + known_limited_cap
    reserve = interval[0] - load
    short_power = 5.2 * interval[1]
    return dict(
        revision="FPC_M2-actual91part-third-protected-NF-leaf",
        native_parts=91,
        ILIM=dict(
            actual_resistor_ohm=r,
            complete_receiving_fraction=0.01,
            actual_resistor_interval_ohm=[r * 0.99, r * 1.01],
            primary_stable_region_ohm=[15000, 232000],
            full_temp_process_equation1_interval_a=interval,
            source_primary="sources/primary/tps2553.pdf p15§9.5.1Equation1",
            lower_over_guarded_load_ratio=interval[0] / load,
            resistor_complete_life_and_ILIM_layout_error_accepted=False,
        ),
        normal=dict(
            NF_RAW5_static_receiving_a=nf["power"]["complete_NF_RAW5_static_a"],
            NF_RAW5_guarded_a=load,
            added_IQ_receiving_a=iq,
            EN_input_primary_endpoint_max_a=en,
            added_board_cap_leak_receiving_a=cap_board_leak,
            extra_branch_guarded_a=extra,
            full_known_DIG_guarded_a=known,
            DIG_source_proposal_a=2.44,
            DIG_remaining_a=2.44 - known,
            FPC_input_total_guarded_a=fpc_input,
            NF_shared_AGND_arithmetic_receiving_a=load + 0.014,
            FPC_shared_return_arithmetic_receiving_a=fpc_input + 0.014,
            AGND_receiving_adds_NF_AUX_return_NOT_zero_or_equal_RAW5_only=True,
            NF_load_counted_once=True,
            all_existing_fan_health_provisions_retained=True,
            complete_hot_current_and_DIG_PDN_accepted=False,
        ),
        voltage=dict(
            operating_P03_force_feed="J23/J21 operating force branch; NEVER J3test",
            conditional_local_FPC_J201_input_receiving_v=[4.90, 5.20],
            NF_required_local_receiving_v=[4.80, 5.20],
            switch_DBV_fulltemp_primary_RON_ohm=0.135,
            NF_switch_drop_at_guarded_load_v=0.135 * load,
            physical_paths_and_load_step_accepted=False,
            distribution_drop_with20pct_receiving_v=(4.90 - 4.80) / 1.2 - 0.135 * load,
            required_drop_expression="I_FPC_RAW5*R_FPCplus + I_FPC_GND*R_FPCreturn + I_NF_RAW5*R_NFplus + I_NF_GND*R_NFreturn + signedP03/E28coupling + dynamic + U <= receivingdrop",
            NF_AUX_downward_drop_expression=".014A*R_AUXplus + I_NF_GND*R_NFreturn + I_FPC_GND*R_FPCreturn + signedP03/E28coupling + ripple + U <= .01347862986V",
            NF_AUX_source_minimum_downward_allowance_v=0.01347862986,
            any_other_AGND_wire_is_parallel_return_not_ideal_isolation=True,
            perfect_pad_via_ground_or_connector_resistance_assumed=False,
            PH_catalog_contact_initial_max_ohm=0.010,
            PH_catalog_after_environment_max_ohm=0.020,
            PH_mating_interfaces_two_pin_pair_scenario_ohm=0.040,
            catalog_contact_is_NOT_hot_EOL_guarantee=True,
            selected_wire_Alpha3049_DCR_nominal_ohm_per_m=41 / 304.8,
            nominal_DCR_is_NOT_hot_maximum=True,
            body_ground_loop_and_AUX_reference_error_accepted=False,
        ),
        startup=dict(
            external_new_capacitors=cap_rows,
            local_input_effective_minimum_receiving_f=120e-9,
            primary_minimum_input_bypass_f=100e-9,
            input_cap_initial_temp_partial_subtotal_f=new_in,
            limited_output_cap_known_partial_subtotal_f=known_limited_cap,
            whole_source_known_external_partial_subtotal_f=all_cap,
            limited_output_known_partial_charge_c=known_limited_cap * 5.2,
            output_constant_current_charge_diagnostic_s=known_limited_cap * 5.2 / reserve,
            constant_current_diagnostic_assumes_bounded_load_at_every_voltage=True,
            input_caps_charge_BEFORE_current_limiter=True,
            full_external_internal_wire_hot_capacitance_upper_f=None,
            ISO_startup_current_or_input_burst_guaranteed_a=None,
            receiving_total_output_startup_peak_target_a=0.080,
            target_with20pct_a=0.080 * 1.2,
            target_is_NOT_characterized_ISO_bound=True,
            FAULT_overcurrent_primary_deglitch_s=[0.005, 0.010],
            primary_turnon3ms_test_is1uF100ohm_NOT_our_load_bound=True,
            typical_short_response2us_NOT_upper_bound=True,
            no_false_latch_or_thermal_retry_qualification=False,
        ),
        fault=dict(
            current_limit_upper_a=interval[1],
            current_limit_not_initial_peak_bound=True,
            limited_DC_power_scenario_w=short_power,
            limited_DC_energy_in10ms_diagnostic_j=short_power * 0.010,
            known_external_output_storage_partial_j=0.5 * known_limited_cap * 5.2**2,
            full_fault_energy_upper_j=None,
            reverse_current_before_comparator_or_partial_power_upper_a=None,
            sustained_fault_thermal_cycle_and_RESET_rearm_accepted=False,
            guaranteed_loaded_cutoff_upper_s=None,
            all_fans_current_limit_plus_NF_limit_DIG_scenario_a=2.44
            + 0.2348217726021618
            + interval[1]
            - load,
            postfault_standby_heat_and_global_guard_analysis_accepted=False,
        ),
        thermal=dict(
            added_IC_IQ_plus_conduction_receiving_w=5.2 * extra + 0.135 * load**2,
            primary_DBV_JEDEC_thetaJA_K_per_W=182.6,
            JEDEC_thetaJA_NOT_actual_PCB_temperature_proof=True,
            capacity_heat_screen_retained_w=nf["power"]["provisional_capacity_heat_w"],
            normal_I2R_not_added_twice=True,
            source_capacity_not_reduced_to_known_subtotal=True,
            local_junction_and_installed_cooling_qualified=False,
        ),
        connector=dict(
            part="B2B-PH-K-S / PHR-2 / SPH-002T-P0.5S",
            wire="Alpha3049AWG26",
            native_pins=pins["J401"],
            manufacturer_AWG_contact_range=[30, 24],
            wire_nominal_conductor_diameter_mm=0.019 * 25.4,
            wire_insulation_OD_mm=[0.049 * 25.4, 0.053 * 25.4],
            primary_current_2A_rating_test_AWG=24,
            AWG26_hot_current_accepted=False,
            primary_PCB_thickness_mm=[0.8, 1.6],
            native_PCB_nominal_mm=1.6,
            inherited_receiving_maximum_PCB_mm=1.76,
            inherited1p76_PCB_scenario_status="FAILED:outside PHmanufacturer1.6maximum",
            actual_max1p6_stack_or_alternate_connector_required=True,
            primary_PH_mated_height_nominal_mm=8.0,
            max_mated_and_wire_exit_geometry_accepted=False,
            solder_crimp_retention_and_strain_process_accepted=False,
        ),
        package_receiving=dict(
            U401_primary_outline_page=41,
            U401_land_pattern_page=42,
            U401_primary_max_body_xy_excluding_flash_mm=[1.75, 3.05],
            U401_primary_max_flash_per_side_mm=0.25,
            U401_conservative_body_xy_including_flash_mm=[2.25, 3.55],
            U401_max_height_from_seating_plane_mm=1.45,
            U401_added_solder_seating_receiving_mm=0.10,
            U401_courtyard_mm=[4.2, 3.8],
            C401_to_C404_primary_max_body_height_mm=0.95,
            C401_to_C404_added_seat_receiving_mm=0.10,
            complete_rear_projection_receiving_mm=1.05,
            inherited_rear_SMD_allowance_receiving_mm=1.2,
            all_receiving_geometry_and_material_accepted=False,
        ),
        source_sha256={
            str(p.relative_to(ROOT)): sha(p)
            for p in [
                ROOT / "analyze.py",
                ROOT / "components.json",
                ROOT / "generated/netlist.xml",
                ROOT / "fan_power_health.kicad_pcb",
                ROOT / "sources/NF05R/generated/analysis.json",
                ROOT / "sources/primary/tps2553.pdf",
            ]
        },
        whole_unit_native_geometry_adopted=False,
        PDN_qualified=False,
        noise_qualified=False,
        startup_qualified=False,
        partial_power_qualified=False,
        physical_qualified=False,
        fabrication_released=False,
    )


if __name__ == "__main__":
    assert not (ROOT / "handoff.json").exists()
    r = analyze()
    (ROOT / "generated/analysis.json").write_text(json.dumps(r, indent=2) + "\n")
    print(json.dumps({k: r[k] for k in ["ILIM", "normal", "startup", "fault", "connector"]}, indent=2))
