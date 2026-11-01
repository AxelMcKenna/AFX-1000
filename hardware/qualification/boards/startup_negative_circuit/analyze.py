"""NF03 selected monitor/clamp/bias equations; no prototype measurements."""

import itertools
import json
from pathlib import Path

from hardware.electronics.power_distribution.p03.models import constant_power_feed, value
from hardware.qualification.boards.startup_negative_protection.analyze import native, cuk_peak
from hardware.qualification.boards.startup_negative_protection.capture import sha
from hardware.qualification.boards.startup_negative_protection.verify import validate_handoff

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[3]
PARENT = ROOT.parent / "startup_negative_protection"
WU = REPO / "hardware/cad/a12/thermal/whole_unit"


def interval(nom, fraction):
    assert nom > 0 and 0 <= fraction < 1
    return [nom * (1 - fraction), nom * (1 + fraction)]


def monitor_window(d, rail):
    m = d["absolute_monitors_per_rail"]
    w = m["windows"][rail]
    answer = {}
    for k in ("uv", "ov"):
        thresholds = []
        for vtrip, rt, rb, sensed_error in itertools.product(
            m["supervisor_threshold_table_v"],
            interval(w[k + "_top_ohm"], m["divider_total_resistor_fraction_requirement"]),
            interval(m["divider_bot_ohm"], m["divider_total_resistor_fraction_requirement"]),
            [
                -m["sensor_total_error_receiving_requirement_v"],
                m["sensor_total_error_receiving_requirement_v"],
            ],
        ):
            # Sensor error is before the divider. Bias is at the actual pin,
            # so use the divider Thevenin resistance rather than another gain.
            ib = m["supervisor_input_bias_table_a"]
            for sign in (-1, 1):
                vpin = vtrip + sign * ib * rt * rb / (rt + rb)
                thresholds.append((vpin * (1 + rt / rb) - sensed_error) / 0.1)
        answer[k + "_trip_interval_v"] = [min(thresholds), max(thresholds)]
    answer["fault_delay_maximum_applies_only_at5mv_pin_overdrive_s"] = 0.0005
    answer["precision_final_endpoint_acceptance"] = False
    answer["sensor_receiving_error_accepted"] = False
    return answer


def clamp(d):
    c = d["independent_gate_clamps"]
    series_lo, series_hi = interval(c["series_gate_clamp_r_ohm"], c["gate_clamp_r_fraction_requirement"])
    sink_min = (1 - c["clamp_error_voltage_requirement_v"]) / (
        series_hi + c["hot_ron_receiving_requirement_ohm"]
    ) - c["miller_and_pv_opposing_current_receiving_requirement_a"]
    assert sink_min > 0
    discharge = c["gate_charge_above_1v_receiving_requirement_per_clamped_node_c"] / sink_min
    # Both negative-bank MOSFETs are included in ONE common-node Q requirement.
    total = 0.001 + 0.0005 + c["close_time_receiving_requirement_s"] + discharge
    led_lo, led_hi = interval(c["led_source_resistor_ohm"], 0.03)
    shunt_lo, shunt_hi = interval(c["led_off_shunt_ohm"], 0.03)
    vf_lo, vf_hi = c["led_vf_25c_table_v"]
    led_min = (4.9 - c["driver_vol_table_enclosure_v"] - 2 * vf_hi) / led_hi - 2 * vf_hi / shunt_lo
    # This is full branch input current INCLUDING the shunt, not LED+shunt twice.
    branch_max = (5.1 - 2 * vf_lo) / led_lo
    off_v = c["driver_open_drain_leakage_requirement_a"] * shunt_hi
    return dict(
        source_gate_current_minimum_given_receiving_requirements_a=sink_min,
        above1v_gate_charge_requirement_c=c["gate_charge_above_1v_receiving_requirement_per_clamped_node_c"],
        conditional_charge_discharge_time_s=discharge,
        conditional_complete_cutoff_s=total,
        required_cutoff_enclosure_s=c["complete_loaded_cutoff_receiving_requirement_s"],
        twenty_percent_time_headroom=1.2 * total <= c["complete_loaded_cutoff_receiving_requirement_s"],
        initial_clamp_current_upper_at13v_a=13 / (series_lo + 0.0),
        led_current_lower_given25c_vf_and_receiving_driver_a=led_min,
        input_branch_current_upper_given25c_vf_a=branch_max,
        full_temperature_trigger_receiving_requirement_a=c["led_full_temp_trigger_receiving_requirement_a"],
        trigger_20percent_scenario=led_min >= 1.2 * c["led_full_temp_trigger_receiving_requirement_a"],
        driver_off_leakage_string_voltage_upper_v=off_v,
        off_string_voltage_20percent_below_two25c_min_vf=1.2 * off_v <= 2 * vf_lo,
        complete_loaded_cutoff_guaranteed=False,
        gate_charge_miller_plateau_drain_slew_hot_ron_led_and_temperature_measured=False,
        primary25c_close_2ms_not_35us100pf_Si8751_transfer=True,
    )


def analyze(d=None):
    validate_handoff(PARENT / "handoff.json")
    d = d or json.loads((ROOT / "design.json").read_text())
    q = json.loads((PARENT / "generated/analysis.json").read_text())
    b = d["isolated_bias_per_rail"]
    mlo, mhi = b["source_voltage_requirement_v"]
    rlo, rhi = interval(b["local_controller_feed_series_r_ohm"], b["feed_r_complete_fraction_requirement"])
    feedlo, feedhi = (mlo - 12.4) / rhi, (mhi - 10.65) / rlo
    # Explicit MAX rows + conservative local-divider/active reserves.
    local5_load = 0.0054 + 0.003 + 2 * 0.0001 + 0.00005 + 0.00255 + 0.00025
    module_out_i = feedhi + local5_load + d["floating_5v"]["iq_receiving_requirement_a"]
    module_out_p = mhi * module_out_i
    module_input_p = module_out_p / b["minimum_efficiency_receiving_requirement"]
    cl = clamp(d)
    digital = 2 * 0.0051 + 2 * cl["input_branch_current_upper_given25c_vf_a"] + 0.0008
    pool = d["reserved_load_partition"]
    assert pool["nf_digital_is_inside_remaining_pool"]
    assert pool["retained_digital_total_a"] == 2.4
    remaining = pool["unassigned_pool_a"] - pool["dual_fan_guarded_planning_partition_a"]
    # Remove the negative and positive components of the NF02 galvanic bias.
    removed_negative_raw_p = sum(
        r["bias"]["normal_feed_current_interval_a"][1] * r["raw_voltage_upper_v"] for r in q["rails"].values()
    )
    n = q["complete_inlet_steady_diagnostic"]
    raw_p = n["new_actual_ledger_all_four_raw_output_power_w"] - removed_negative_raw_p
    # Full2.4A DIG already reserves ALL fan/NF power. No extra6mA term.
    protected_p = n["retained_other_protected_input_power_w"] + raw_p / 0.75 + 2 * module_input_p
    direct_i = 0.09  # new AUX.2mA is a declared suballocation of existing90mA.
    point = constant_power_feed(11.4, 0.36, protected_p, direct_i)
    phases = []
    for rail, r in q["rails"].items():
        delta = r["raw_voltage_upper_v"] * (
            r["protected_peak_diagnostic_a"] - r["live_protected_current_scenario_a"]
        )
        p = constant_power_feed(11.4, 0.36, protected_p + delta / 0.75, direct_i)
        phases.append(
            dict(
                rail=rail,
                **p,
                twenty_percent_input_current_margin=1.2 * p["current_a"] <= 4,
                raw_switch25c_peak_a=cuk_peak(
                    r["raw_voltage_upper_v"],
                    r["total_raw_current_diagnostic_a"] - r["bias"]["normal_feed_current_interval_a"][1],
                ),
                source_and_inlet_qualified=False,
            )
        )
    pp, pins, _ = native(PARENT / "sources/p03-fresh-netlist.xml")
    stored = []
    for rail, raw, src in [("N19", "RAW_N22", "N19_SRC"), ("N12", "RAW_N17", "N12_SRC")]:
        rows = []
        for ref, ps in pins.items():
            if not ref.startswith("C") or "AGND" not in ps.values():
                continue
            for net in (raw, src):
                if net in ps.values():
                    nominal = value(pp, ref)
                    label = pp[ref].findtext("value")
                    comparison = nominal * 1.2 * 1.15  # actual X7R positive-temperature scenario
                    v = (
                        q["rails"][rail]["raw_voltage_upper_v"]
                        if net == raw
                        else q["rails"][rail]["source_voltage_enclosure_v"][1]
                    )
                    rows.append(
                        dict(
                            ref=ref,
                            net=net,
                            actual_value=label,
                            nominal_f=nominal,
                            initial20pct_times_X7R15pct_scenario_f=comparison,
                            stored_energy_scenario_j=0.5 * comparison * v * v,
                            generic_initial_tolerance_and_hot_effective_max_accepted=False,
                        )
                    )
        stored.append(
            dict(
                rail=rail,
                actual_direct_capacitors=rows,
                direct_cap_energy_subtotal_scenario_j=sum(r["stored_energy_scenario_j"] for r in rows),
                complete_discharge_path_and_energy_upper_bound_j=None,
                missing=[
                    "cross-coupled capacitors/inductors and transformer/module storage",
                    "LT3090 reverse discharge and startup-foldback behavior",
                    "actual source current transient and bank/pass FET body diodes",
                    "original protected1.5mF/220uF possible backfeed through pass body diode",
                    "external wiring/PCB and converter switching energy",
                ],
            )
        )
    old = json.loads((WU / "generated/ledger.json").read_text())
    old_raw = old["retained_raw_current_envelopes"]
    old_total = old["total_internal_heat_screen_w"]
    evidence = ROOT / "sources/negative-after-diagnostic.json"
    assert sha(evidence) == "acdd473ea8a3062d5c2c7a08bce7e0c280980f672c570c7666e6a646f7465f0c"
    diagnostic = json.loads(evidence.read_text())
    copper = {}
    for rail in ("N19", "N12"):
        rows = [
            r
            for r in diagnostic["paths"]
            if r["grid_mm"] == 0.05 and r["net"] in (rail + "_SRC", rail + "_COMMON", rail)
        ]
        assert len(rows) == 3, (rail, [r["net"] for r in rows])
        r = q["rails"][rail]
        bank_current = (
            r["live_protected_current_scenario_a"]
            + r["new_vee_bleed_source_current_a"]
            + r["new_monitor_source_current_requirement_a"]
        )
        pass_stage_drop = r["live_protected_current_scenario_a"] * (
            r["shunt_interval_requirement_ohm"][1] + 0.020
        )
        bank_resistance_max = (
            r["retained_stage_dc_drop_allocation_v"] / 1.2 - pass_stage_drop
        ) / bank_current
        total_cu = sum(x["ohm"] for x in rows)
        copper[rail] = dict(
            actual_e28_copper_only_diagnostic_ohm=total_cu,
            bank_current_after_removing_galvanic_bias_a=bank_current,
            allowable_bank_mos_contacts_and_copper_with20pct_ohm=bank_resistance_max,
            illustrative_bank_pair10mohm_contacts5mohm_copper_allowance_ohm=bank_resistance_max - 0.015,
            actual_copper_alone_exceeds_complete20pct_bank_resistance_requirement=total_cu
            > bank_resistance_max,
            physical_routing_repair_required_for_this_NF03_region=total_cu > bank_resistance_max,
            actual_diagnostic_is_accepted_upper_bound=False,
        )
    enclosing = []
    for net, row in old_raw.items():
        required = row["retained_allocation_a"]
        if net.startswith("RAW_N"):
            rail = "N19" if net == "RAW_N22" else "N12"
            r = q["rails"][rail]
            required = (
                r["p03_internal_raw_current_excluding_new_controller_a"]
                + r["live_protected_current_scenario_a"]
                + r["new_vee_bleed_source_current_a"]
                + r["new_monitor_source_current_requirement_a"]
            )
        enclosing.append(
            dict(
                net=net,
                old_retained_a=row["retained_allocation_a"],
                new_required_scenario_a=required,
                new_capacity_enclosing_a=max(row["retained_allocation_a"], required),
                voltage_magnitude_v=row["voltage_magnitude_v"],
            )
        )
    capacity_raw_delta = (
        sum(
            r["voltage_magnitude_v"] * (r["new_capacity_enclosing_a"] - r["old_retained_a"])
            for r in enclosing
        )
        / 0.75
    )
    capacity_heat = old_total + capacity_raw_delta + 2 * module_input_p
    return dict(
        revision="NF03-component-and-power-state-candidate",
        monitors={r: monitor_window(d, r) for r in ("N19", "N12")},
        floating_bias=dict(
            module=b["part"],
            normal_controller_feed_interval_a=[feedlo, feedhi],
            controller_load_requirement_a=b["controller_feed_load_requirement_a"],
            twenty_percent_feed_headroom=feedlo >= 1.2 * b["controller_feed_load_requirement_a"],
            normal_feed_within5to25ma=feedlo >= 0.005 and feedhi <= 0.025,
            local5_current_requirement_a=local5_load,
            module_output_current_requirement_a=module_out_i,
            module_load_between10and90percent=0.1 * 0.067 <= module_out_i <= 0.9 * 0.067,
            module_output_power_requirement_w=module_out_p,
            input_power_given60pct_efficiency_requirement_w=module_input_p,
            primary_minimum_efficiency_guaranteed=False,
            isolated_bias_return_has_no_galvanic_positive_source_feed=True,
            source_collapse_capacitive_and_clamp_paths_qualified=False,
        ),
        gate_clamp=cl,
        digital_reserve=dict(
            total_target_a=2.4,
            pool_a=0.416,
            fan_planning_a=0.3768,
            remaining_a=remaining,
            nf_digital_requirement_a=digital,
            nf_with20pct_guard_a=1.2 * digital,
            fan_health_remaining_after_nf20pct_a=remaining - 1.2 * digital,
            fan_health_actual_bound_a=None,
            does_not_add_fan_or_nf_again_on_top_of2p4a=True,
            physical_branch_or_input_current_qualified=False,
        ),
        steady_inlet_scenario=dict(
            **point,
            protected_power_w=protected_p,
            direct_aux_current_a=direct_i,
            board_boundary_power_w=protected_p + point["protected_voltage_v"] * direct_i,
            complete_feed_power_w=0.36 * point["current_a"] ** 2,
            plug_boundary_power_w=11.4 * point["current_a"],
            source_power_scenario_guaranteed=False,
        ),
        negative_ramp_inlet_scenarios=phases,
        stored_source_energy_inventory=stored,
        actual_e28_voltage_budget_gap=copper,
        whole_unit_capacity_screen_comparison=dict(
            old_WU89row_internal_heat_w=old_total,
            retained_raw_current_rows=enclosing,
            raw_input_capacity_delta_w=capacity_raw_delta,
            two_isolated_bias_input_power_increment_w=2 * module_input_p,
            new_capacity_internal_heat_scenario_w=capacity_heat,
            planning1p2_heat_stress_w=1.2 * capacity_heat,
            full_digital2p4a_preserved=True,
            fan_nf_and_return_losses_not_added_twice=True,
            feed_heat_basis="Existing WU4A*.36Ohm=5.76W capacity screen retained; not the separate constant-power operating point",
            module_efficiency_input_overhead_and_AUX_partition_accepted=False,
            exterior_heat_credit_w=0,
            actual_heat_upper_bound_w=None,
        ),
        native_schematic_authored=d["native_schematic_authored"],
        pcb_implemented=False,
        hardware_state_logic_native_complete=False,
        physical_tests_performed=0,
        source_current_upper_guaranteed_a=None,
        maximum_fault_energy_guaranteed_j=None,
        startup_qualified=False,
        physical_qualified=False,
        fabrication_released=False,
        build_ready=False,
        source_sha256={
            str(f.relative_to(REPO)): sha(f)
            for f in [
                ROOT / "design.json",
                Path(__file__),
                PARENT / "handoff.json",
                PARENT / "generated/analysis.json",
                WU / "generated/ledger.json",
                evidence,
            ]
        },
    )


if __name__ == "__main__":
    q = analyze()
    (ROOT / "generated/analysis.json").write_text(json.dumps(q, indent=2) + "\n")
    print(
        json.dumps(
            {
                k: q[k]
                for k in ("digital_reserve", "steady_inlet_scenario", "whole_unit_capacity_screen_comparison")
            },
            indent=2,
        )
    )
