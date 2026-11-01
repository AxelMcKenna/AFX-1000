"""Actual NF05H261 conditional cutoff/load calculations with provenance.

Primary test points are kept separate from complete prototype requirements.
An unaccepted receiving limit never becomes a measured/manufacturer bound.
"""

import hashlib
import itertools
import json
import math
import re
from pathlib import Path

from hardware.electronics.common.netlists import netlist
from hardware.electronics.power_distribution.p03.models import auxiliary, constant_power_feed

ROOT = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def corners(x, f):
    return [x * (1 - f), x * (1 + f)]


def native_resistors():
    actual, pins = netlist(ROOT / "generated/netlist.xml")

    def ohm(s):
        m = re.match(r"([\d.]+)([kKM]?)", s)
        return float(m.group(1)) * {"": 1, "k": 1000, "K": 1000, "M": 1000000}[m.group(2)]

    values = {
        r: ohm(c.findtext("value"))
        for r, c in actual.items()
        if r
        in ["R3", "R10", "R4", "R11", "R23", "R24", "R40", "R41", "R92", "R93", "R94", "R95", "R96", "R97"]
    }
    return actual, pins, values


def thresholds(r):
    rows = []
    for top1, top2, bottom, ref, bias, hyst in itertools.product(
        corners(r["R92"], 0.0035),
        corners(r["R93"], 0.007),
        corners(r["R94"], 0.0035),
        corners(1.15, 0.01),
        [-100e-9, 100e-9],
        [0.00325, 0.00825],
    ):
        top = top1 + top2
        rows.append(
            (ref * (1 + top / bottom) + bias * top, ref * (1 + hyst) * (1 + top / bottom) + bias * top)
        )
    return dict(
        falling_trip_v=[min(x[0] for x in rows), max(x[0] for x in rows)],
        rising_release_v=[min(x[1] for x in rows), max(x[1] for x in rows)],
        divider_complete_error_receiving_fraction=0.0035,
        R93_trim_complete_error_receiving_fraction=0.007,
        installed_temperature_life_solder_humidity_bounds_accepted=False,
        finite_service_life_requirement_selected=False,
        sense_complete_bias_receiving_a=100e-9,
        primary_SENSE_bias_test_is_5V_not_actual1p15V=True,
        AUX_operating_receiving_v=[2.52, 2.70],
        actual_source_distribution_and_dynamic_margin_accepted=False,
    )


def off_discharge(r, bleed=None):
    rb = (bleed or r["R97"]) * 1.03
    # Independent complete positive SOURCE leakage requirements. The old
    # LVC1G06 Ioff test is VCC=0 only; it supplies no powered-output IOZ row.
    positive = 2 * 5e-6 + 1e-6 + 0.2e-6
    floor = positive * rb
    target = 0.003
    ctotal = 0.22e-6
    # Do not assume all retained charge is on the directly bled rail. The
    # bound includes charge behind an original LED shunt plus series resistor.
    rpath = rb + max(r["R4"], r["R11"]) * 1.03 + 10000 * 1.03
    t = math.inf if floor >= target else rpath * ctotal * math.log((5.2 - floor) / (target - floor))
    return dict(
        complete_positive_source_receiving_a=positive,
        components_a=dict(
            two_powered_OD_positive_leaks=10e-6, switch_output_off_source=1e-6, board_surface_source=0.2e-6
        ),
        powered_OD_leak_guaranteed_by_Ioff=False,
        switch_output_leak_guaranteed_by_ISD_VOUT_GND=False,
        bleed_upper_ohm=rb,
        steady_rail_voltage_upper_given_requirements_v=floor,
        total_all_nodes_capacitance_receiving_f=ctotal,
        worst_charge_path_upper_ohm=rpath,
        zero_LED_forward_drop_credit=True,
        target_rail_voltage_v=target,
        max_one_string_forward_current_at_target_a=target / (min(r["R4"], r["R11"]) * 0.97),
        guarded_steady_string_current_a=1.2 * floor / (min(r["R4"], r["R11"]) * 0.97),
        relay_return_current_minimum_receiving_a=10e-6,
        relay_return_primary_condition="25C,ION1200mA; NOT a hot low-current clamp guarantee",
        RC_path_decay_diagnostic_s=None if not math.isfinite(t) else t,
        floating_LED_midpoint_nodes=["N19_CLAMP_LED_MID", "N12_CLAMP_LED_MID"],
        explicit_per_LED_midpoint_resistive_paths_present=False,
        full_distributed_electrical_LED_current_decay_upper_s=None,
        all_node_initial_energy_upper_given_C_v_w_requirement_j=0.5 * ctotal * 5.2**2,
        measured_node_capacitance_and_backfeed_accepted=False,
    )


def analyze():
    actual, pins, r = native_resistors()
    assert len(actual) == 261
    th = thresholds(r)
    p03_parts, _ = netlist(ROOT / "sources/p03-frozen-netlist.xml")
    p03_aux = auxiliary(p03_parts)["source_interval_v"]
    assert (
        p03_aux
        == json.loads((ROOT / "sources/p03-source-analysis.json").read_text())["auxiliary"][
            "source_interval_v"
        ]
    )
    # Control loading: 47k external pull-down is retained, plus the switch's
    # 100nA ION and independent 2uA board leakage. Internal smart-pulldown has
    # only typical resistance; its threshold-crossing load is separately held.
    high = (4.8 / (r["R95"] * 1.03) - 2.35e-6) / (1 / (r["R95"] * 1.03) + 1 / (r["R96"] * 0.97))
    sink = (5.2 - 0.25) / (r["R95"] * 0.97) + 2.1e-6
    bleed_current = 5.2 / (r["R97"] * 0.97)
    branch_upper = (5.2 - 2 * 1.1) / (min(r["R4"], r["R11"]) * 0.97)
    complete_switch_ron = 0.5
    swdrop = complete_switch_ron * (bleed_current + 2 * branch_upper)
    branch_lower = (4.8 - swdrop - 2 * 1.4 - 0.3) / (max(r["R4"], r["R11"]) * 1.03)
    LED_lower = branch_lower - 2 * 1.4 / (10000 * 0.97)
    LED_upper = branch_upper - 2 * 1.1 / (10000 * 1.03)
    off = off_discharge(r)
    # Real closed-clamp gate-loop constraints, not logic-only safety.
    clamped_R = 220 * 1.03 + 20
    active_source = 0.001
    equilibrium = active_source * clamped_R
    remaining_sink = 0.3 / clamped_R - active_source
    gate_discharge = 1e-6 / remaining_sink if remaining_sink > 0 else None
    # Replace two 383ohm branch current provisions with actual402ohm values;
    # no credit for moving the two sinks' quiescent current off RAW5 because
    # the old digital-other provision was aggregate/incomplete.
    old = json.loads((ROOT / "sources/sequence249/generated/analysis.json").read_text())
    nf03 = json.loads((ROOT / "sources/nf03c-parameters.json").read_text())
    source_fpc = json.loads((ROOT / "sources/sealed-FPC340-power-analysis.json").read_text())
    control_raw = 5.2 / (r["R95"] * 0.97) + 6.5e-6 + 20e-6 + 1.4e-6 + 2e-6
    new_nf_raw = (
        2 * nf03["iso_primary_dc_max_table_a"]
        + 2 * branch_upper
        + nf03["digital_other_current_requirement_a"]
        + bleed_current
        + control_raw
    )
    old_nf_guard = 1.2 * (
        2 * nf03["iso_primary_dc_max_table_a"]
        + 2 * (5.1 - 2 * 1.1) / (383 * 0.97)
        + nf03["digital_other_current_requirement_a"]
    )
    known = (
        source_fpc["normal_receiving"]["full_known_partitions_with_FHguard_a"]
        - old_nf_guard
        + 1.2 * new_nf_raw
    )
    aux_div = 2.7 / ((r["R92"] + r["R93"] + r["R94"]) * 0.995) + 100e-9
    old_aux = old["AUX"]
    old_clamp_pulldown = 2 * 2.7 / (47000 * 0.97)
    new_clamp_pulldown = 2 * 2.7 / (r["R3"] * 0.97)
    opamp_output_DC_receiving = 0.0004
    # Actual passive output-feedback paths, not only the OPA's supply IQ.
    # Output can be anywhere0..AUX under the accepted negative-rail envelope;
    # this does NOT bound an invalid overvoltage or capacitive transient.
    output_feedback_DC = (
        (2.7 + 19.38) / ((r["R23"] + r["R24"]) * 0.97)
        + (2.7 + 12.12) / ((r["R40"] + r["R41"]) * 0.97)
        + 4 * 1.2e-9
        + 2 * 0.2e-9
    )
    aux_normal = (
        old_aux["normal_static_receiving_a"] + aux_div + 2 * 110e-6 - old_clamp_pulldown + new_clamp_pulldown
    )
    aux_fault = (
        old_aux["nonrail_fault_static_receiving_a"]
        + aux_div
        + 2 * 510e-6
        - old_clamp_pulldown
        + new_clamp_pulldown
    )
    aux_normal += opamp_output_DC_receiving
    aux_fault += opamp_output_DC_receiving
    capacity = old["power"]["guarded_capacity_heat_screen_w"] + 0.120
    protected = old["power"]["normal_protected_constant_power_w"] + 0.120
    point = constant_power_feed(11.4, 0.36, protected, 0.090)
    return dict(
        revision="NF05H261-unaccepted-hardgate-proposal",
        native_parts=len(actual),
        native_resistor_values_ohm=r,
        absolute_UV=th,
        AUX_source_applicability=dict(
            source_P03_corner_v=p03_aux,
            old_NF_min2p548_shortfall_even_at_source_v=2.548 - p03_aux[0],
            new_NF_local_receiving_v=[2.52, 2.70],
            maximum_downward_distribution_and_reference_allowance_v=p03_aux[0] - 2.52,
            maximum_positive_overshoot_allowance_v=2.70 - p03_aux[1],
            UV_release_to_new_receiving_minimum_margin_v=2.52 - th["rising_release_v"][1],
            source_positive_drop_expression=".013A*R_AUXplus + (.013A+.055067682A)*R_sharedNF_AGND + coupledP03/E28offset + ripple + uncertainty <= .01347862986V",
            all_physical_paths_and_dynamic_bounds_accepted=False,
        ),
        control=dict(
            normal_OFF_Volts_table_max=0.25,
            guarded_LOW_v=0.25 * 1.2,
            switch_VIL_max_v=0.35,
            ON_HIGH_conditional_v=high,
            switch_VIH_min_v=1.0,
            supervisor_sink_current_a=sink,
            used_fulltemp_VOL_row="VDD>=2.7V,IRESET2mA; below2.7V use.4mA/.25V row only",
            ON_threshold_crossing_smart_pull_down_maximum_load_receiving_a=0.0002,
            ON_crossing_external_current_available_a=(4.8 - 1) / (r["R95"] * 1.03)
            - 1 / (r["R96"] * 0.97)
            - 2.35e-6,
            continuous_RAW5_LOW_drive_and_startup_load_accepted=False,
        ),
        LED=dict(
            RAW5_receiving_v=[4.8, 5.2],
            AUX_receiving_v=[2.52, 2.70],
            sink_VCC_repaired_to_AUX=True,
            old_RAW5_VIH_requirement_v=[0.7 * 4.8, 0.7 * 5.2],
            new_LVC_VIH_primary_v=1.7,
            new_AUP_VOH_20uA_row_lower_v=2.52 - 0.1,
            AUP_primary_continuous_current_row_a=20e-6,
            new_command_pulldown_ohm=r["R3"],
            AUP_max_loaded_current_requirement_a=2.70 / (r["R3"] * 0.97) + 3e-6,
            AUP_20pct_loaded_current_a=1.2 * (2.70 / (r["R3"] * 0.97) + 3e-6),
            powered_off_connected_default_LOW20pct_v=1.2 * r["R3"] * 1.03 * (0.6e-6 + 1e-6 + 1e-6),
            default_LOW_extrapolated_to_intermediate_AUX=False,
            external_header_load_requirement_a=1e-6,
            complete_LVC_input_and_board_each_receiving_a=1e-6,
            sink_VOL_primary_2p3V_8mA_v=0.3,
            full_sink_current_upper_a=branch_upper,
            switch_RON_complete_receiving_ohm=complete_switch_ron,
            switch_RON_0p5_enclosure_is_not_continuous_RAW5_manufacturer_guarantee=True,
            switch_drop_upper_given_requirements_v=swdrop,
            LED_IF_lower_a=LED_lower,
            LED_IF_upper_a=LED_upper,
            Vf_complete_receiving_v=[1.1, 1.4],
            Vf_primary_test="25C,IF10mA",
            trigger_max_receiving_a=0.002,
            trigger_has20pct_conditionally=LED_lower >= 1.2 * 0.002,
            LED_absolute_IF_at85C_a=0.020 - (85 - 58) * 0.0003,
            LED_20pct_current_screen_inside_derated_absmax=1.2 * LED_upper < 0.020 - (85 - 58) * 0.0003,
            absolute_maximum_comparison_is_NOT_functional_qualification=True,
            complete_hot_Vf_trigger_and_Vol_accepted=False,
        ),
        hardoff=dict(
            **off,
            sum_RC_path_diagnostic_and_receiving_delays_s=(
                off["RC_path_decay_diagnostic_s"] + 0.0005 + 0.0001 + 0.002 + gate_discharge
            ),
            conditional_off_sum_is_NOT_a_manufacturer_timing_bound=True,
            actual_loaded_cutoff_upper_s=None,
            minimum_recognized_UV_glitch_pulse_s=None,
            independent_fault_latched_UV_recovery_implemented=False,
            AUX_assert_response_receiving_s=0.0005,
            switch_OFF_response_receiving_s=0.0001,
            typical_6us_switch_OFF_and_24ohm_QOD_NOT_upper_bounds=True,
            relay_close_response_receiving_s=0.002,
            relay_primary_turn_ON_2ms_condition="25C,RL200ohm,VDD20V,IF5mA; NOT IF=0 hot NC closure guarantee",
            maximum_active_gate_source_current_receiving_a=active_source,
            primary_LTC_gate_UP_max15p5uA_condition="VGATE4V, not clamped0.3V; bankSi8751source max unbounded",
            hot_clamp_RON_receiving_ohm=20,
            total_clamp_return_path_upper_ohm=clamped_R,
            clamped_VGS_equilibrium_given_requirements_v=equilibrium,
            clamp_target_VGS_v=0.3,
            complete_gate_charge_to_target_receiving_c=1e-6,
            gate_discharge_time_conditional_s=gate_discharge,
            MOSFET_drain_OFF_current_at_target_VGS_accepted=False,
            clamp_load_SOAfault_max_current_and_energy_accepted=False,
        ),
        rejected_1kohm_bleed=off_discharge(r, 1000),
        power=dict(
            DIG_receiving_proposal_a=2.44,
            previous_receiving_a=2.42,
            complete_new_NF_RAW5_static_a=new_nf_raw,
            new_NF_with20pct_a=1.2 * new_nf_raw,
            full_known_guarded_partition_a=known,
            remaining_unallocated_a=2.44 - known,
            opamp_feedback_output_DC_receiving_a=opamp_output_DC_receiving,
            actual_feedback_network_DC_screen_a=output_feedback_DC,
            feedback_resistor_complete_error_fraction_for_current_screen=0.03,
            negative_voltage_receiving_magnitude_for_DC_screen_v=[19.38, 12.12],
            invalid_negative_OV_and_internal_short_AUX_current_bound_a=None,
            output_capacitor_charging_and_dynamic_AUX_peaks_accepted=False,
            new_AUX_normal_static_a=aux_normal,
            new_AUX_normal20pct_a=1.2 * aux_normal,
            AUX_normal_receiving_proposal_a=0.010,
            new_AUX_fault_static_a=aux_fault,
            new_AUX_fault20pct_a=1.2 * aux_fault,
            AUX_fault_receiving_proposal_a=0.013,
            AUX_stays_inside_existing90mA_pool=True,
            AUX_total_pool_partition_accepted=False,
            bleed_power_upper_w=5.2**2 / (r["R97"] * 0.97),
            bleed_power_with20pct_w=1.2 * 5.2**2 / (r["R97"] * 0.97),
            resistor_1206_nominal_70C_rating_w=0.25,
            conditional_linear_85C_derated_rating_w=0.25 * (155 - 85) / (155 - 70),
            resistor_local_temperature_and_lifetime_qualified=False,
            additional20mA_source_power_screen_w=0.12,
            provisional_capacity_heat_w=capacity,
            normal_protected_power_w=protected,
            normal_feed_point=point,
            no_normal_I2R_added_to_capacity_twice=True,
            simultaneous_fan_limit_DIG_scenario_a=2.44 + 0.2348217726021618,
            fault_standby_ledger_complete=False,
        ),
        primary_return=dict(
            port="J6",
            input_positive="GUARDED_12V_FORCE",
            return_net="MODULE_INPUT_GND",
            normal_current_screen_a=old["module_feed"]["both_module_input_power_requirement_w"] / 9,
            module_input_capacitance_initial_nominal_f=20e-6,
            full_hot_capacitance_and_input_inrush_bound_a=None,
            J1_pin4_now_physical_NC=True,
            board_AGND_tie_permitted=False,
            P03_operating_ground_return_required=True,
            input_loop_and_connector_contact_ground_accepted=False,
        ),
        source_states=[
            dict(
                RAW5="4.8..5.2",
                AUX="0.8..2.0",
                action="independent UV asserts; LED-energy cutoff after stated finite receiving delay; do not trust AUX logic",
                qualified=False,
            ),
            dict(
                RAW5="normal",
                AUX="valid after UV recovery",
                action="delay before energy restored; stale ARM/PERMIT/global-reset recovery remains unverified",
                qualified=False,
            ),
            dict(
                RAW5="falling below1.5",
                AUX="any or independently charged",
                action="supervisor/loadswitch behavior may be undefined; LED stored charge, cathode backfeed and source-node reverse energy require prototype waveform bounds",
                qualified=False,
            ),
            dict(
                RAW5="0",
                AUX="charged",
                action="no Ioff-to-intermediate-power transfer; hot gate leakage and reverse switch-body-diode injection remain held",
                qualified=False,
            ),
        ],
        holds=[
            "AUX_OV_hardgate_not_implemented",
            "actual_source_GLOBAL_OFF_interval",
            "module_SETTLED22p8_before_ARM",
            "LTC_and_Si8751_loaded_clamp_source_current",
            "hot_LED_return_trigger_Vf_and_NC_response",
            "RAW5_brownout_and_reverse_energy",
            "complete_powered_OD_and_switch_output_positive_leak",
            "finite_cap_network_and_input_inrush",
            "all_source_PDN_force_contact_noise_and_thermal_bounds",
            "actual261part_PCB_fit_and_routing",
        ],
        source_sha256={
            str(p.relative_to(ROOT)): sha(p)
            for p in [
                ROOT / "analyze.py",
                ROOT / "circuit.py",
                ROOT / "components.json",
                ROOT / "generated/netlist.xml",
                ROOT / "generated/native-review.json",
                ROOT / "sources/manifest.json",
            ]
        },
        model_dependency_sha256={
            name: sha(ROOT.parents[4] / name)
            for name in [
                "hardware/electronics/power_distribution/p03/models.py",
                "hardware/electronics/common/netlists.py",
            ]
        },
        PCB_implemented=False,
        partial_power_qualified=False,
        startup_qualified=False,
        physical_qualified=False,
        release_approved=False,
    )


if __name__ == "__main__":
    assert not (ROOT / "handoff.json").exists(), "Preserve sealed diagnostic; replay a copy"
    result = analyze()
    (ROOT / "generated/analysis.json").write_text(json.dumps(result, indent=2) + "\n")
    print(
        json.dumps(
            {k: result[k] for k in ["absolute_UV", "LED", "hardoff", "power", "primary_return"]}, indent=2
        )
    )
