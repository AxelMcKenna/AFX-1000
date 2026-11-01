"""NF05R265 actual-native receiving comparisons, with no qualification inference."""

import hashlib
import json
import re
from pathlib import Path

from hardware.electronics.common.netlists import netlist

ROOT = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def native_values():
    actual, pins = netlist(ROOT / "generated/netlist.xml")
    resistors = {}
    for ref, c in actual.items():
        if ref.startswith("R"):
            m = re.match(r"([\d.]+)([kKM]?)", c.findtext("value"))
            resistors[ref] = float(m.group(1)) * {"": 1, "k": 1000, "K": 1000, "M": 1e6}[m.group(2)]
    return actual, pins, resistors


def analyze():
    actual, pins, r = native_values()
    assert len(actual) == 265
    parent = json.loads((ROOT / "sources/parent261/generated/analysis.json").read_text())
    old_r = parent["native_resistor_values_ohm"]
    # No divider/voltage/sense-cap change: reuse the frozen computed envelope
    # as an explicitly named receiving result, never as a manufacturer guarantee.
    assert all(r[k] == old_r[k] for k in ["R92", "R93", "R94", "R95", "R96"])
    th = parent["absolute_UV"]
    assert all("C1206C104J3GACTU" in actual[x].findtext("value") for x in ["C97", "C98", "C99"])
    leakage = 7.35e-6  # old2.35uA + U58 primary II5uA (VI5.5/GND only).
    control_high = (4.8 / (r["R95"] * 1.03) - leakage) / (1 / (r["R95"] * 1.03) + 1 / (r["R96"] * 0.97))
    control_sink = (5.2 - 0.25) / (r["R95"] * 0.97) + 2.1e-6 + 5e-6
    bleed = 5.2 / (r["R97"] * 0.97)
    branch_upper = (5.2 - 2 * 1.0) / (min(r["R4"], r["R11"]) * 0.97)
    switch_drop = 0.5 * (bleed + 2 * branch_upper)
    branch_lower = (4.8 - switch_drop - 2 * 1.4 - 0.3) / (max(r["R4"], r["R11"]) * 1.03)
    # Two separate LED shunts: subtract the current of ONE parallel shunt
    # from each LED's total series current, rather than twice the pair VF.
    led_lower = branch_lower - 1.4 / (10000 * 0.97)
    led_upper = branch_upper  # all-branch current is a conservative LED maximum.
    command_load = 2.7 / (r["R3"] * 0.97) + 3e-6
    # R17 was already covered by the parent's conservative nine-pulldown term.
    fault_signal_load = 2.7 / (r["R17"] * 0.97) + 3e-6
    c_min, c_max = 100e-9 * 0.94, 100e-9 * 1.06
    reset_delay = [(1.17 - 0.1) * c_min / 1.4e-6, 1.29 * c_max / 0.85e-6 + 0.0005]
    # This circuit needs external FAULT and READY receivers plus output monitor
    # loads; the old report omitted their explicit source current. 0.3mA would
    # not enclose two 15k pulldowns; use0.5mA receiving, not a measured bound.
    external_outputs = 0.0005
    two_host_pd = 2 * (2.7 / (15000 * 0.97) + 20e-6 + 2e-6)
    assert external_outputs >= two_host_pd
    old = parent["power"]
    new_normal_static = old["new_AUX_normal_static_a"] + external_outputs + 110e-6
    new_fault_static = old["new_AUX_fault_static_a"] + external_outputs + 510e-6
    old_branch = (5.2 - 2 * 1.1) / (min(old_r["R4"], old_r["R11"]) * 0.97)
    old_bleed = 5.2 / (old_r["R97"] * 0.97)
    nf_raw = old["complete_new_NF_RAW5_static_a"] + 2 * (branch_upper - old_branch) + bleed - old_bleed + 5e-6
    known = old["full_known_guarded_partition_a"] + 1.2 * (nf_raw - old["complete_new_NF_RAW5_static_a"])
    normal_aux, fault_aux = 1.2 * new_normal_static, 1.2 * new_fault_static
    cap_rows = []
    for ref, c in actual.items():
        if ref.startswith("C") and set(pins[ref].values()) in [
            {"DIG5_FORCE", "AGND"},
            {"CLAMP_LED_SUPPLY", "AGND"},
        ]:
            value = c.findtext("value")
            assert value.startswith("100nF"), (ref, value)
            maximum = 100e-9 * (1.10 * 1.15 if "X7R" in value else 1.06)
            cap_rows.append(
                dict(
                    ref=ref,
                    nets=pins[ref],
                    actual_native_value=value,
                    nominal_f=100e-9,
                    partial_maximum_f=maximum,
                    basis="initial10% times positiveX7Rtemperature15%"
                    if "X7R" in value
                    else "complete6% receiving (not guaranteed lifetime)",
                    full_hot_process_life_bound_accepted=False,
                )
            )
    assert {x["ref"] for x in cap_rows} == {"C39", "C55", "C97", "C98"}
    known_cap = sum(c["partial_maximum_f"] for c in cap_rows)
    return dict(
        revision="NF05R265-retained-ARM-UV-fault-and-individual-LED-shunts",
        native_parts=len(actual),
        native_resistor_values_ohm=r,
        absolute_UV=th,
        AUX_source_applicability={
            **parent["AUX_source_applicability"],
            "source_positive_drop_expression": ".014A*R_AUXplus + (.014A + I_NF_RAW5_actual)*R_sharedNF_AGND + coupledP03/E28offset + ripple + uncertainty <= .01347862986V",
            "actual_total_AUX_pool_and_shared_return_bound_accepted": False,
        },
        RAW5_supervisor_control=dict(
            complete_node_sink_leakage_receiving_a=leakage,
            new_U58_II_primary_5p5V_or_GND_a=5e-6,
            II_at_arbitrary_intermediate_input_transfer_accepted=False,
            settled_HIGH_given_requirements_v=control_high,
            settled_LOW_receiving_v=0.25,
            U58_VTplus_enclosure_receiving_v=1.87,
            U58_VTminus_enclosure_receiving_v=0.58,
            U58_discrete_rows_are_NOT_continuous_threshold_guarantee=True,
            supervisor_sink_a=control_sink,
            supervisor_4p8V_sink_test_capacity_a=0.002,
            load_switch_ON_VIH_v=1.0,
            load_switch_ON_VIL_v=0.35,
            crossing_smart_pulldown_receiving_a=0.0002,
            threshold_crossing_current_available_a=(4.8 - 1) / (r["R95"] * 1.03)
            - 1 / (r["R96"] * 0.97)
            - leakage,
            complete_delay_receiving_s=reset_delay,
            CT_full_fraction_receiving=0.06,
            CT_reset_initial_receiving_v=0.1,
            CT_reset_discharge_receiving_ohm=1000,
            CT_reset_to_p1V_RC_diagnostic_s=1000 * c_max * __import__("math").log(1.29 / 0.1),
            minimum_recognized_UV_pulse_guaranteed_s=None,
            physical_OFF_duration_guaranteed_s=None,
            dynamic_load_switch_or_U58_response_accepted=False,
        ),
        LED=dict(
            RAW5_receiving_v=[4.8, 5.2],
            AUX_receiving_v=[2.52, 2.70],
            Vf_complete_receiving_v=[1.0, 1.4],
            Vf_primary_is_25C_10mA_only=True,
            individual_LED_shunts_ohm={x: r[x] for x in ["R5", "R98", "R12", "R99"]},
            switch_complete_RON_receiving_ohm=0.5,
            switch_drop_v=switch_drop,
            series_branch_current_lower_a=branch_lower,
            full_sink_current_upper_a=branch_upper,
            guarded_sink_current_a=1.2 * branch_upper,
            LVC_2p3V_VOLp3_test_current_a=0.008,
            IF_lower_a=led_lower,
            IF_upper_a=led_upper,
            hot_trigger_max_receiving_a=0.002,
            lower_exceeds20pct_trigger_receiving=led_lower >= 1.2 * 0.002,
            complete_command_load_a=command_load,
            complete_command_load_times1p2_a=1.2 * command_load,
            AUP_VCCminusp1_continuous_primary_row_a=20e-6,
            old_RAW5_logic_supply_repair_preserved=True,
            all_hot_Vf_IFC_IFT_RON_and_OPTICAL_timing_accepted=False,
        ),
        retained_ARM_UV_fault=dict(
            U58_output_load_receiving_a=fault_signal_load,
            U58_guarded_output_load_a=1.2 * fault_signal_load,
            primary_VOH_VCCminusp1_and_VOLp1_current_a=100e-6,
            fault_capture_AUX_minimum_receiving_v=2.4,
            output_HIGH_given_requirements_v=2.4 - 0.1,
            HCS_VTplus_complete_receiving_v=2.0,
            U42p11="N19_SAFE_SOURCE",
            U51p12="N19_SAFE_SOURCE",
            U51p13="ABS_AUX_READY",
            U51p11="N19_SAFE",
            gate_equation="N19_SAFE = N19_SAFE_SOURCE AND NOT(ABS_AUX_FAULT)",
            fault_equation="N19_F_SOURCE = N19_ARM_CONDITIONED AND NOT(N19_SAFE)",
            fault_path="U58.4 -> U48.12 -> U51.11 -> U47.2 -> U35.8 -> U45.3/.6 -> U46.3/.6 -> U34.6/.4 -> J1.14 -> existing E28 retained fault latch",
            UV_or_SAFE_clears_ARM=False,
            functional_fault_latch_is_existing_E28_not_new_NF_latch=True,
            actual_E28_split_fault_wiring_and_reset_priority_implemented=False,
            minimum_UV_pulse_and_GLOBAL_OFF_interval_accepted=False,
            no_reclose_guarantee_during_deep_AUX_corruption=False,
            J1_pin7_now_monitor_output_only=True,
            external_J1p7_complete_source_load_receiving_a=1e-6,
        ),
        hardoff={
            "individual_LED_midpoint_resistive_paths_implemented": True,
            "maximum_actual_loaded_cutoff_s": None,
            "positive_leak_DC_receiving_report": "generated/LED-DC-network.json",
            "DC_comparison_does_not_bound_optical_or_transient_decay": True,
            "hot_TLP4590_return_IFC_RON_response_and_source_faultSOA_accepted": False,
            "loaded_gate_clamp_receiving_comparison_unchanged": {
                k: v
                for k, v in parent["hardoff"].items()
                if k
                in [
                    "maximum_active_gate_source_current_receiving_a",
                    "hot_clamp_RON_receiving_ohm",
                    "total_clamp_return_path_upper_ohm",
                    "clamped_VGS_equilibrium_given_requirements_v",
                    "clamp_target_VGS_v",
                    "complete_gate_charge_to_target_receiving_c",
                    "gate_discharge_time_conditional_s",
                    "MOSFET_drain_OFF_current_at_target_VGS_accepted",
                ]
            },
        },
        power=dict(
            DIG_receiving_proposal_a=2.44,
            previous261_known_guarded_a=old["full_known_guarded_partition_a"],
            complete_NF_RAW5_static_a=nf_raw,
            NF_RAW5_guarded_a=1.2 * nf_raw,
            full_known_DIG_guarded_a=known,
            DIG_remaining_unassigned_a=2.44 - known,
            old261_external_output_current_omission_corrected_a=external_outputs,
            two15k_host_pull_downs_plus_receiving_leaks_screen_a=two_host_pd,
            old_p3mA_external_aggregate_rejected=True,
            U58_normal_complete_ICC_receiving_a=110e-6,
            U58_fault_complete_ICC_receiving_a=510e-6,
            primary10uA_ICC_rail_inputs_and500uA_deltaICC_3to5p5V_rows_NOT_transfer_guarantee=True,
            AUX_normal_static_a=new_normal_static,
            AUX_fault_static_a=new_fault_static,
            AUX_normal_guarded_a=normal_aux,
            AUX_fault_guarded_a=fault_aux,
            AUX_normal_receiving_proposal_a=0.011,
            AUX_fault_receiving_proposal_a=0.014,
            total_AUX_source_pool_receiving_a=0.090,
            total_AUX_pool_partition_accepted=False,
            bleed_power_upper_w=5.2**2 / (r["R97"] * 0.97),
            bleed_power_times1p2_w=1.2 * 5.2**2 / (r["R97"] * 0.97),
            conditional_85C_TNPW1206_derated_power_w=0.25 * (155 - 85) / (155 - 70),
            actual_local_temperature_life_and_assembly_accepted=False,
            provisional_capacity_heat_w=old["provisional_capacity_heat_w"],
            normal_protected_power_w=old["normal_protected_power_w"],
            normal_feed_point=old["normal_feed_point"],
            same2p44DIG_and90mA_AUX_capacity_provisions_not_reduced=True,
            normal_feed_point_is_allocated_capacity_NOT_lower_actual_bom_load=True,
            simultaneous_fan_limit_DIG_scenario_a=old["simultaneous_fan_limit_DIG_scenario_a"],
            fault_standby_and_branch_short_ledger_complete=False,
        ),
        RAW5_branch_startup=dict(
            external_capacitor_inventory=cap_rows,
            known_external_partial_subtotal_f=known_cap,
            known_partial_charge_at5p2V_c=known_cap * 5.2,
            known_partial_energy_at5p2V_j=0.5 * known_cap * 5.2**2,
            legacy_C97_C98_total_p22uF_value_note_superseded_as_complete_C_bound=True,
            IC_internal_wire_and_opto_capacitance_upper_f=None,
            ISO_module_switching_startup_current_upper_a=None,
            branch_full_network_capacitance_upper_f=None,
            branch_inrush_current_and_fault_protection_accepted=False,
            actual_operating_feed="proposed protected force branch fromP03J23/J21; FPC_M2 not adopted; NEVER P03J3 test header",
            local_RAW5_floor_receiving_v=4.8,
        ),
        primary_return=parent["primary_return"],
        holds=[
            "shared E28 FAULT wiring/reset priority and minimum GLOBAL_OFF physical interval",
            "deep AUX corruption, RAW5 brownout/reverse-energy and CT partial-discharge recovery",
            "arbitrary-input powered/partial-power leakage and negative board injection",
            "hot TLP return/trigger/Vf/RON/loaded cutoff and real pass-FET fault SOA",
            "module settled22.8V before ARM, bounded startup/no-load/transient max25.2V",
            "complete passive drift/effective-C/service-life and local-loop layout",
            "READY loaded-drive margin, actual host Schmitt/default-LOW interface",
            "AUX OV hardgate not implemented; inherited OV behavior remains unqualified",
            "all265part PCB placement/routing/manufacturer-process/thermal and harness PDN",
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
        PCB_implemented=False,
        startup_qualified=False,
        partial_power_qualified=False,
        physical_qualified=False,
        release_approved=False,
    )


if __name__ == "__main__":
    assert not (ROOT / "handoff.json").exists(), "Preserve sealed successor"
    r = analyze()
    (ROOT / "generated/analysis.json").write_text(json.dumps(r, indent=2) + "\n")
    print(json.dumps({k: r[k] for k in ["RAW5_supervisor_control", "LED", "power"]}, indent=2))
