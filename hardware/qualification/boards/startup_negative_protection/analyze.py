"""NF02 conditional design region, with row conditions and unproved contracts intact."""

import json
import math
import xml.etree.ElementTree as ET
from pathlib import Path

from hardware.electronics.power_distribution.p03.bipolar import ledger
from hardware.electronics.power_distribution.p03.models import constant_power_feed, value

from .capture import P03, REPO, ROOT, sha, write


def finite_positive(*values):
    if not all(math.isfinite(v) and v > 0 for v in values):
        raise ValueError("Finite positive physical parameters required")


def bounds(nominal, fraction):
    finite_positive(nominal)
    if not math.isfinite(fraction) or not 0 <= fraction < 1:
        raise ValueError("Invalid complete effective error interval")
    return [nominal * (1 - fraction), nominal * (1 + fraction)]


def validate_parameters(p):
    def walk(node):
        if isinstance(node, dict):
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)
        elif isinstance(node, (int, float)) and not isinstance(node, bool):
            finite_positive(node)

    walk(p)
    assert set(p["rails"]) == {"N19", "N12"}, "Both actual negative stages required"
    for k in (
        "native_sources_must_remain_on_while_negative_stages_ramp",
        "protected_full_live_load_present_from_zero",
        "one_bipolar_stage_at_a_time_after_positive_5v_charge",
    ):
        assert p[k] is True, "Unproved load shedding or concurrency changes source model"
    for k in (
        "full_trajectory_ramp_current_manufacturer_guaranteed",
        "ramp_capacitor_effective_bounds_accepted",
        "hot_mosfet_and_bank_receiving_requirements_accepted",
        "bias_switch_receiving_requirements_accepted",
        "native_schematic_authored",
        "startup_qualified",
        "soa_qualified",
        "physical_qualified",
        "fabrication_released",
    ):
        assert p[k] is False, "Unsupported acceptance cannot be promoted through parameters"


def watchdog(cap, fraction):
    lo, hi = bounds(cap, fraction)
    return [0.905 * (77.4e9 * lo + 55) / 1000, 1.095 * (77.4e9 * hi + 55) / 1000]


def cuk_peak(magnitude, current, vin=9.8, eta=0.75, inductance=68e-6 * 0.8, frequency=1e6):
    finite_positive(magnitude, current, vin, eta, inductance, frequency)
    duty = (magnitude + 1) / (vin + magnitude + 1)
    return current * (1 + magnitude / (vin * eta)) + vin * duty / (inductance * frequency)


def native(path):
    t = ET.parse(path).getroot()
    parts = {c.get("ref"): c for c in t.findall("./components/comp")}
    pins, members = {}, {}
    for n in t.findall("./nets/net"):
        net = n.get("name").lstrip("/")
        members[net] = [(x.get("ref"), x.get("pin")) for x in n.findall("node")]
        for ref, pin in members[net]:
            pins.setdefault(ref, {})[pin] = net
    return parts, pins, members


def bias(source_min, source_max, resistors, p):
    finite_positive(source_min, source_max, *resistors)
    vgmin, vgmax = p["guarded_positive_input_allocation_v"]
    rzmin, rz5max = p["native_vin_shunt_5ma_table_v"]
    # Upper includes the actual 5..25mA regulator load-regulation table term.
    rzmax = rz5max + p["native_vin_load_regulation_upper_5_to_25ma_v"]
    rlo, rhi = bounds(sum(resistors), p["bias_resistor_total_fraction_requirement"])
    on_r = p["bias_switch_on_resistance_receiving_requirement_ohm"]
    minimum = (vgmin + source_min - rzmax) / (rhi + on_r)
    maximum = (vgmax + source_max - rzmin) / rlo
    startup = (vgmax + source_max) / rlo
    rbleed_lo = bounds(p["bias_vin_bleed_ohm"], p["bias_resistor_total_fraction_requirement"])[0]
    on_lo = bounds(p["on_input_pulldown_ohm"], p["bias_resistor_total_fraction_requirement"])[0]
    load = (
        p["floating_controller_maximum_supply_current_table_a"]
        + p["isolator_secondary_dc_maximum_table_a"]
        + p["optional_parallel_hardoff_driver_supply_current_requirement_a"]
        + p["floating_control_misc_current_receiving_requirement_a"]
        + 5.25 / on_lo
        + rzmax / rbleed_lo
    )
    power = (vgmax + source_max - rzmin) ** 2 / rlo
    return dict(
        input_source="guarded positive12V -> normally-OFF discrete P-channel switch -> seriesR -> VIN; VEE returns to actual after-bank negative input",
        feed_resistor_nominal_ohm=sum(resistors),
        feed_resistor_effective_interval_ohm=[rlo, rhi],
        switch_on_resistance_requirement_ohm=on_r,
        vin_shunt_voltage_table_enclosure_at5_to25ma_v=[rzmin, rzmax],
        normal_feed_current_interval_a=[minimum, maximum],
        initial_vin_zero_feed_current_upper_a=startup,
        controller_and_external_local_load_requirement_a=load,
        normal_supply_current_headroom_ratio=minimum / load,
        normal_supply_has_20percent_headroom=minimum >= 1.2 * load,
        normal_feed_within_5_to25ma_load_regulation_characterization=minimum >= 0.005 and maximum <= 0.025,
        initial_feed_has_20percent_margin_to50ma_guidance=startup * 1.2 <= 0.050,
        total_feed_resistor_power_upper_w=power,
        each_equal_series_resistor_derated_power_rating_required_w=1.2 * power / len(resistors),
        pmos_normal_off_vds_upper_v=vgmax + source_max - rzmin,
        pmos_initial_or_collapsed_vin_vds_upper_v=vgmax + source_max,
        pmos_gate_source_normal_upper_v=vgmax,
        normal_bias_feed_load_on_negative_source_a=maximum,
        both_positive_and_negative_power_accounted=True,
        table_to_complete_waveform_transfer_verified=False,
        optional_driver_1ma_is_receiving_requirement_not_a_primary_guarantee=True,
        whole_floating_bias_load_power_upper_w=rzmax * maximum,
        guarantees_established=False,
    )


def stage(rail, r, p, source_state, eparts, epins, members):
    s = source_state["rails"][rail]
    source_lo, source_hi = s["source_magnitude_v"]
    cap, bleed = r["cap_ref"], r["bleed_ref"]
    assert epins[cap] == {"1": "AGND", "2": rail}, (rail, epins[cap])
    assert set(epins[bleed].values()) == {rail, "AGND"}
    cap_nom, bleed_nom = value(eparts, cap), value(eparts, bleed)
    local_initial = cap_nom * 1.2
    post_test_comparison = local_initial * 1.25
    live = (
        s["external_current_allocation_a"]
        + source_hi / (bleed_nom * 0.97)
        + p["additional_protected_leakage_and_crossrail_current_receiving_requirement_a"]
    )
    cap_net = r["new_full_network_capacitance_receiving_requirement_f"]
    cr = r["ramp_100nf_array_count"] * p["ramp_capacitor_array_unit_nominal_f"]
    crlo, crhi = bounds(cr, p["effective_ramp_capacitor_total_fraction_requirement"])
    cflo, cfhi = bounds(
        r["ramp_filter_cf_nominal_f"], p["effective_ramp_capacitor_total_fraction_requirement"]
    )
    # Manufacturer table is at VSS2.56. Scaling by clamp bounds follows the
    # application proportional model; an additional +/-20% is a diagnostic,
    # never a newly invented manufacturer full-trajectory limit.
    rowlo, rowhi = p["ramp_table_current_at_ss_2p56_v_a"]
    sslo, sshi = p["ss_clamp_table_v"]
    excursion = p["linear_ss_transfer_additional_excursion_diagnostic_fraction"]
    irlo = rowlo * sslo / 2.56 * (1 - excursion)
    irhi = rowhi * sshi / 2.56 * (1 + excursion)
    slewlo, slewhi = irlo / crhi, irhi / crlo
    peak_load = live + cap_net * slewhi + irhi
    shunt_lo, shunt_hi = bounds(r["fault_shunt_nominal_ohm"], p["shunt_total_fraction_requirement"])
    limitlo, limithi = 0.045 / shunt_hi, 0.055 / shunt_lo
    b = bias(source_lo, source_hi, r["bias_series_resistors_ohm"], p)
    veebleeder_lo = bounds(p["after_bank_to_agnd_bleed_ohm"], p["bias_resistor_total_fraction_requirement"])[
        0
    ]
    veeleak = source_hi / veebleeder_lo
    uvcurrent = r["new_absolute_monitor_divider_current_receiving_requirement_a"]
    raw = source_state["raw_local_current_ledger"][r["source_raw_net"]]
    internal = raw["required_raw_output_current_a"] - s["external_current_allocation_a"]
    required_raw = internal + peak_load + b["normal_feed_current_interval_a"][1] + veeleak + uvcurrent
    peak_sw = cuk_peak(raw["raw_voltage_upper_v"], required_raw)
    fault_raw = internal + limithi + b["normal_feed_current_interval_a"][1] + veeleak + uvcurrent
    cap_charge_time = source_hi / slewlo
    # Explicitly include CR's extra swing and the large CF charge at RAMP.
    filter_extra = (crhi + cfhi) * p["ramp_pin_voltage_upper_receiving_requirement_v"] / irlo
    ready_time = (
        cap_charge_time
        + filter_extra
        + p["gate_full_charge_time_receiving_requirement_s"]
        + p["absolute_ready_debounce_and_propagation_receiving_requirement_s"]
        + p["initial_logic_and_native_delay_receiving_requirement_s"]
    )
    wdlo, wdhi = watchdog(r["watchdog_cwd_nominal_f"], p["watchdog_cap_effective_total_fraction_requirement"])
    rfhi = r["ramp_filter_rf_ohm"] * 1.03
    bank_i = live + b["normal_feed_current_interval_a"][1] + veeleak + uvcurrent
    dc = (
        live * (shunt_hi + p["pass_mosfet_on_resistance_receiving_requirement_ohm"])
        + bank_i * p["bank_pair_and_force_copper_receiving_requirement_ohm"]
    )
    cap_energy = 0.5 * cap_net * source_hi**2
    load_energy = 0.5 * live * source_hi * cap_charge_time
    return dict(
        actual_rail=rail,
        source_voltage_enclosure_v=s["source_magnitude_v"],
        target_voltage_v=s["target_magnitude_v"],
        external_live_allocation_a=s["external_current_allocation_a"],
        external_current_verified=False,
        e28_actual_connected_nodes=[
            dict(ref=a, pin=b, value=eparts[a].findtext("value")) for a, b in members[rail]
        ],
        actual_bulk_ref=cap,
        actual_bulk_value=eparts[cap].findtext("value"),
        actual_bulk_nominal_f=cap_nom,
        local_initial20pct_only_f=local_initial,
        local_endurance_restored20c_comparison_f=post_test_comparison,
        post_endurance_comparison_is_full_temperature_or_lifetime_bound=False,
        additional_unverified_protected_leakage_and_crossrail_requirement_a=p[
            "additional_protected_leakage_and_crossrail_current_receiving_requirement_a"
        ],
        live_protected_current_scenario_a=live,
        full_network_capacitance_requirement_f=cap_net,
        full_network_capacitance_verified=False,
        capacitance_requirement_over_known_post_test_subtotal_ratio=cap_net / post_test_comparison,
        capacitance_allocation_has20pct_over_known_post_test_comparison=cap_net >= 1.2 * post_test_comparison,
        ramp_capacitor_nominal_f=cr,
        ramp_capacitor_effective_requirement_interval_f=[crlo, crhi],
        filter_cf_effective_requirement_interval_f=[cflo, cfhi],
        filter_cf_min_to_cr_max_ratio=cflo / crhi,
        rf_cr_upper_s=rfhi * crhi,
        rf_cr_has20pct_margin_to50us=1.2 * rfhi * crhi <= 50e-6,
        ramp_current_extended_diagnostic_a=[irlo, irhi],
        full_trajectory_current_guaranteed=False,
        output_slew_diagnostic_v_per_s=[slewlo, slewhi],
        protected_peak_diagnostic_a=peak_load,
        bias=b,
        shunt_interval_requirement_ohm=[shunt_lo, shunt_hi],
        native_current_limit_table_interval_a=[limitlo, limithi],
        native_limit_has20pct_over_normal_start_diagnostic=limitlo >= 1.2 * peak_load,
        raw_voltage_upper_v=raw["raw_voltage_upper_v"],
        p03_internal_raw_current_excluding_new_controller_a=internal,
        new_vee_bleed_source_current_a=veeleak,
        new_monitor_source_current_requirement_a=uvcurrent,
        total_raw_current_diagnostic_a=required_raw,
        switching_peak_25c_diagnostic_a=peak_sw,
        cold0p9_screen_headroom_ratio=0.9 / peak_sw,
        cold_screen_has20pct_headroom=0.9 >= 1.2 * peak_sw,
        hot_current_guarantee_a=None,
        frequency_and_efficiency_guaranteed=False,
        output_ramp_only_diagnostic_s=cap_charge_time,
        additional_ramp_filter_charge_diagnostic_s=filter_extra,
        complete_stage_diagnostic_s=ready_time,
        guaranteed_complete_stage_s=None,
        watchdog_interval_given_receiving_cap_s=[wdlo, wdhi],
        watchdog_minimum_has20pct_over_diagnostic=wdlo >= 1.2 * ready_time,
        steady_bank_force_current_diagnostic_a=bank_i,
        proposed_stage_dc_loss_diagnostic_v=dc,
        retained_stage_dc_drop_allocation_v=s["proposed_remaining_stage_dc_drop_budget_v"],
        stage_dc_drop_has20pct_headroom=1.2 * dc <= s["proposed_remaining_stage_dc_drop_budget_v"],
        native_source_dynamic10mv_ground_harness5mv_allocations_preserved=True,
        proposed_remaining_extra_dc_drop_v=s["proposed_remaining_stage_dc_drop_budget_v"] / 1.2 - dc,
        capacitor_charge_energy_diagnostic_j=cap_energy,
        live_load_pass_energy_diagnostic_j=load_energy,
        normal_cap_plus_live_pass_energy_diagnostic_j=cap_energy + load_energy,
        entire_watchdog_rectangular_currentlimit_energy_diagnostic_j=source_hi * limithi * wdhi,
        native620us_rectangular_currentlimit_energy_diagnostic_j=source_hi * limithi * 620e-6,
        guaranteed_fault_energy_j=None,
        currentlimit_fault_raw_current_diagnostic_a=fault_raw,
        currentlimit_fault_cold_switch_peak_diagnostic_a=cuk_peak(raw["raw_voltage_upper_v"], fault_raw),
        continuous_fault_source_regulation_guaranteed=False,
        guaranteed_hot_soa=False,
        fault_peak_and_source_capacitor_inductive_energy_unbounded=True,
        sense_250mv_fast_threshold_only_typical_not_guaranteed=True,
    )


def analyze(p=None):
    p = p or json.loads((ROOT / "parameters.json").read_text())
    validate_parameters(p)
    capture = json.loads((ROOT / "sources/capture.json").read_text())
    assert all(sha(REPO / n) == h for n, h in capture["original_source_sha256"].items()), (
        "Runtime sources differ from captured source"
    )
    pp, _, _ = native(ROOT / "sources/p03-fresh-netlist.xml")
    ep, en, members = native(ROOT / "sources/e28-fresh-netlist.xml")
    state = ledger(pp, controller_current=0)
    result = {rail: stage(rail, r, p, state, ep, en, members) for rail, r in p["rails"].items()}
    # Real missing-source interlock requirement; no ideal phantom negative feed.
    rbleed_hi = p["after_bank_to_agnd_bleed_ohm"] * (1 + p["bias_resistor_total_fraction_requirement"])
    off_dc = p["bias_switch_complete_off_leakage_receiving_requirement_a"] * rbleed_hi
    worst_feed = max(r["bias"]["initial_vin_zero_feed_current_upper_a"] for r in result.values())
    injection = (
        worst_feed
        * p["bias_switch_full_path_disable_receiving_requirement_s"]
        / p["after_bank_to_agnd_effective_cap_minimum_requirement_f"]
    )
    gate_lo = bounds(p["bias_gate_source_pullup_ohm"], p["bias_resistor_total_fraction_requirement"])[0]
    direct_guard_current = (
        sum(r["bias"]["normal_feed_current_interval_a"][1] for r in result.values())
        + 2 * p["guarded_positive_input_allocation_v"][1] / gate_lo
    )
    # Negative output power contribution from the guarded-positive bias loops is real.
    added_raw_power = sum(
        (
            r["live_protected_current_scenario_a"]
            - r["external_live_allocation_a"]
            + r["bias"]["normal_feed_current_interval_a"][1]
            + r["new_vee_bleed_source_current_a"]
            + r["new_monitor_source_current_requirement_a"]
        )
        * r["raw_voltage_upper_v"]
        for r in result.values()
    )
    baseline = json.loads(
        (ROOT / "sources/snapshot" / (P03 / "generated/analysis.json").relative_to(REPO)).read_text()
    )
    base_power = baseline["operating_budget"]["protected_input_power_w"]
    extra_digital_power = 5.1 * p["new_digital_5v_primary_current_receiving_requirement_a"] / 0.85
    # Replace, rather than add to, the old independent RAW_*/50/200mA budget.
    # Retain the old 3mA reserve on each POSITIVE controller, since this packet
    # does not select or validate those channels. No old negative 3mA is added.
    positive_controller_reserve_raw_power = sum(
        r["raw_voltage_upper_v"] * 0.003
        for n, r in state["raw_local_current_ledger"].items()
        if n.startswith("RAW_P")
    )
    steady_raw_power = (
        state["required_steady_raw_output_power_w"] + added_raw_power + positive_controller_reserve_raw_power
    )
    old_raw_power = state["existing_coupled_raw_output_power_allocation_w"]
    other_protected_power = base_power - old_raw_power / 0.75
    steady_protected_power = other_protected_power + steady_raw_power / 0.75 + extra_digital_power
    direct_current = 0.09 + direct_guard_current + p["new_aux_primary_current_receiving_requirement_a"]
    point = constant_power_feed(
        11.4,
        0.36,
        steady_protected_power,
        direct_current,
    )
    phases = []
    for name, r in result.items():
        delta = r["raw_voltage_upper_v"] * (
            r["protected_peak_diagnostic_a"] - r["live_protected_current_scenario_a"]
        )
        phase_point = constant_power_feed(11.4, 0.36, steady_protected_power + delta / 0.75, direct_current)
        ic = "U1" if name == "N19" else "U13"
        pair_nets = ("RAW_P22", "RAW_N22") if ic == "U1" else ("RAW_P17", "RAW_N17")
        pair_power = sum(
            state["raw_local_current_ledger"][n]["raw_voltage_upper_v"]
            * state["raw_local_current_ledger"][n]["required_raw_output_current_a"]
            for n in pair_nets
        )
        pair_power += state["raw_local_current_ledger"][pair_nets[0]]["raw_voltage_upper_v"] * 0.003
        pair_power += r["raw_voltage_upper_v"] * (
            r["total_raw_current_diagnostic_a"]
            - state["raw_local_current_ledger"][pair_nets[1]]["required_raw_output_current_a"]
        )
        phases.append(
            dict(
                single_active_negative_stage=name,
                other_negative_rail_and_all_live_loads_remain_powered=True,
                all_four_raw_output_power_w=steady_raw_power + delta,
                affected_dual_converter=ic,
                affected_dual_converter_total_output_power_w=pair_power,
                affected_dual_converter_all_loss_assigned_to_ic_at75pct_w=pair_power / 3,
                full_protected_input_power_diagnostic_w=steady_protected_power + delta / 0.75,
                **phase_point,
                source_voltage_stays_above9p8_diagnostic=phase_point["protected_voltage_v"] >= 9.8,
                input_current_has20pct_headroom_to4a_profile=phase_point["current_a"] * 1.2 <= 4,
                adapter_source_and_current_waveform_guaranteed=False,
            )
        )
    # Fixed LTC4214 ACL/CB cannot achieve the actual cold-source20% headroom.
    n12 = result["N12"]
    perfect_fixed_rmax = 0.044 / (1.2 * n12["live_protected_current_scenario_a"])
    fixed_acl_minimum_ceiling = 0.080 / perfect_fixed_rmax
    check_names = [
        "capacitance_allocation_has20pct_over_known_post_test_comparison",
        "rf_cr_has20pct_margin_to50us",
        "native_limit_has20pct_over_normal_start_diagnostic",
        "cold_screen_has20pct_headroom",
        "watchdog_minimum_has20pct_over_diagnostic",
        "stage_dc_drop_has20pct_headroom",
    ]
    report = dict(
        revision="NF02-primary-conditioned-pre-native",
        scope=__doc__,
        rails=result,
        rail_algebraic_checks=all(
            all(r[k] for k in check_names)
            and r["bias"]["normal_supply_has_20percent_headroom"]
            and r["bias"]["normal_feed_within_5_to25ma_load_regulation_characterization"]
            and r["bias"]["initial_feed_has_20percent_margin_to50ma_guidance"]
            and r["filter_cf_min_to_cr_max_ratio"] >= 3
            for r in result.values()
        ),
        closed_algebraic_region_is_a_physical_guarantee=False,
        fixed_ltc4214_rejection=dict(
            maximum_shunt_with20pct_live_cb_margin_ohm=perfect_fixed_rmax,
            minimum_acl_maximum_even_with_perfect_shunt_a=fixed_acl_minimum_ceiling,
            raw_cold_peak_with_that_external_current_a=cuk_peak(
                n12["raw_voltage_upper_v"],
                n12["p03_internal_raw_current_excluding_new_controller_a"] + fixed_acl_minimum_ceiling,
            ),
            lower_voltage_supply_range_solves_bias_but_not_this_source_mismatch=True,
        ),
        partial_power=dict(
            required_normally_off_bias_switch=True,
            bias_enable_requires_independent_actual_after_bank_absolute_UV_and_AUX_valid_and_bank_permit=True,
            gate_driver_or_controller_VIN_UV_is_not_an_absolute_rail_monitor=True,
            off_dc_positive_vee_requirement_v=off_dc,
            worst_injection_additional_v=injection,
            dc_plus_collapse_positive_vee_requirement_v=off_dc + injection,
            has20pct_margin_to0p3v_pin_floor=1.2 * (off_dc + injection) <= 0.3,
            leakage_timing_effective_cap_requirements_verified=False,
            charged_load_reverse_blocking_retained_upstream_B2B=True,
            charged_load_discharge_reverse_peak_and_partial_power_qualified=False,
        ),
        new_bias_power=dict(
            guarded_positive_direct_current_upper_requirement_a=direct_guard_current,
            guarded_positive_direct_power_at13p2_w=13.2 * direct_guard_current,
            negative_raw_output_power_increment_w=added_raw_power,
            negative_raw_input_power_increment_at75pct_w=added_raw_power / 0.75,
            additional_primary_5v_current_requirement_a=p[
                "new_digital_5v_primary_current_receiving_requirement_a"
            ],
            additional_AUX_current_requirement_a=p["new_aux_primary_current_receiving_requirement_a"],
            complete_new_input_power_bound_guaranteed=False,
            negative_source_return_and_positive_guard_draw_both_counted=True,
        ),
        complete_inlet_steady_diagnostic=dict(
            **point,
            base_protected_input_power_w=base_power,
            removed_old_independent_raw_input_power_w=old_raw_power / 0.75,
            retained_other_protected_input_power_w=other_protected_power,
            new_actual_ledger_all_four_raw_output_power_w=steady_raw_power,
            positive_only_existing_controller_reserve_raw_power_w=positive_controller_reserve_raw_power,
            recomposed_protected_input_power_w=steady_protected_power,
            guard_aux_direct_input_current_requirement_a=direct_current,
            old_negative_controller_reserve_double_counted=False,
            complete_feed0p36ohm_is_accepted=False,
            adapter_dynamics_and_initial_concurrency_bounded=False,
        ),
        single_negative_phase_input_diagnostics=phases,
        capacitor_specification_erratum=dict(
            old1800uf_and264uf_are_initial_tolerance_only=True,
            initial_times_post_endurance25pct_is_restored20c_comparison_not_field_lifetime_upper=True,
            old_NF01_and_SC02_unchanged=True,
        ),
        actual_p03_native_values_ledger=state,
        primary_row_condition_transfer_established=False,
        actual_controller_peak_current_a=None,
        native_new_schematic_authored=False,
        pcb_implemented=False,
        physical_tests_performed=0,
        startup_qualified=False,
        soa_qualified=False,
        reverse_current_qualified=False,
        physical_qualified=False,
        fabrication_released=False,
        build_ready=False,
    )
    report["closed_algebraic_receiving_region"] = (
        report["rail_algebraic_checks"]
        and report["partial_power"]["has20pct_margin_to0p3v_pin_floor"]
        and all(
            r["source_voltage_stays_above9p8_diagnostic"]
            and r["input_current_has20pct_headroom_to4a_profile"]
            for r in phases
        )
    )
    paths = [
        ROOT / "parameters.json",
        ROOT / "architecture.json",
        ROOT / "PRIMARY-FACTS.md",
        ROOT / "sources/capture.json",
        ROOT / "sources/p03-fresh-netlist.xml",
        ROOT / "sources/e28-fresh-netlist.xml",
        ROOT / "sources/primary-sources.json",
        Path(__file__),
        P03 / "bipolar.py",
        P03 / "models.py",
        P03 / "spec.py",
        REPO / "hardware/electronics/common/netlists.py",
    ]
    report["source_sha256"] = {str(f.relative_to(REPO)): sha(f) for f in paths}
    return report


if __name__ == "__main__":
    q = analyze()
    write(ROOT / "generated/analysis.json", q)
    print("Conditional algebraic receiving region:", q["closed_algebraic_receiving_region"])
    for rail, r in q["rails"].items():
        print(
            rail,
            "peak",
            r["protected_peak_diagnostic_a"],
            "coldswitch",
            r["switching_peak_25c_diagnostic_a"],
            "ready",
            r["complete_stage_diagnostic_s"],
            "watchdog",
            r["watchdog_interval_given_receiving_cap_s"],
        )
