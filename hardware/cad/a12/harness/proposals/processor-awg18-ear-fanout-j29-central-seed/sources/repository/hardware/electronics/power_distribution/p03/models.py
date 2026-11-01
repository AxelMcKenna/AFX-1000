"""Independent P03 interval/nodal models; allocations are not measurements."""

import itertools
import math

import numpy as np

from ...common.netlists import number


def value(parts, ref):
    return number(parts[ref].findtext("value"))


def divider_trip(top, bottom, threshold, leakage, error=0.003):
    """Threshold plus signed input leakage; all independent endpoint corners."""
    values = [
        t * (1 + top * (1 + st * error) / (bottom * (1 + sb * error))) + i * top * (1 + st * error)
        for t, st, sb, i in itertools.product(threshold, (-1, 1), (-1, 1), (-leakage, leakage))
    ]
    return [min(values), max(values)]


def auxiliary(parts):
    # TPS7A16 full-temperature 2% reference envelope, FB bias ±100 nA.
    rtop = value(parts, "R108") + value(parts, "R130")
    interval = divider_trip(rtop, value(parts, "R109"), (1.193 * 0.98, 1.193 * 1.02), 100e-9)
    return dict(
        source_interval_v=interval,
        receiver_minimum_v=2.50,
        receiver_characterized_project_window_v=[2.50, 2.70],
        receiver_window_is_absolute_maximum_rating=False,
        maximum_cable_drop_before_receiver_minimum_v=interval[0] - 2.50,
        maximum_positive_dynamic_excursion_before_characterized_ceiling_v=2.70 - interval[1],
        divider_error_fraction=0.003,
        reference_error_fraction=0.02,
        fb_bias_bound_a=100e-9,
        receiver_interlock_measured=False,
    )


def auxiliary_current(parts):
    """Explicit source allocation; unknown dynamic/leakage loads remain holds."""
    vmax = 2.70
    # Full supply across each pullup/bleed overbounds even mutually exclusive
    # states. The comparator divider uses its actual series path.
    refs = ("R110", "R111", "R113", "R316", "R246", "R120", "R117")
    currents = {r: vmax / (value(parts, r) * 0.97) for r in refs}
    currents["R118+R119"] = vmax / ((value(parts, "R118") + value(parts, "R119")) * 0.997)
    currents["R108+R130+R109"] = vmax / (
        (value(parts, "R108") + value(parts, "R130") + value(parts, "R109")) * 0.997
    )
    total = 0.090
    low = auxiliary(parts)["source_interval_v"][0]
    return dict(
        e28_output_current_allocation_a=0.060,
        native_resistive_current_upper_allocations_a=currents,
        known_resistive_subtotal_a=sum(currents.values()),
        u25_u26_u103_static_and_dynamic_plus_leakage_reserve_a=0.003,
        active_current_reserve_manufacturer_and_waveform_verified=False,
        total_u102_output_current_allocation_a=total,
        remaining_current_after_external_resistive_and_active_reserve_a=total
        - 0.060
        - sum(currents.values())
        - 0.003,
        ldo_ground_current_allocation_a=0.0001,
        maximum_input_voltage_v=13.2,
        ldo_loss_allocation_w=(13.2 - low) * total + 13.2 * 0.0001,
        maximum_normal_input_current_allocation_used_in_quadratic_a=total,
        complete_load_transients_and_hot_leakage_bound_verified=False,
        physical_tests_performed=0,
    )


def ready_interface(parts, receiver_pulldown_ohm=15000, extra_output_sink_allocation_a=2e-6):
    """External J106.4 is the LTC2910 open-drain output, not buck PG.

    The manufacturer specifies a loaded LOW, but no separate output-off
    leakage maximum. The explicit extra-sink allocation is consequently a
    requirement to validate, not a manufacturer guarantee. No internal weak
    pullup current is credited to the HIGH calculation.
    """
    if receiver_pulldown_ohm <= 0 or extra_output_sink_allocation_a < 0:
        raise ValueError("READY resistance and leakage allocation must be physical")
    low, high = auxiliary(parts)["source_interval_v"]
    pullup = value(parts, "R316")
    rp_high, rp_low = pullup * 1.03, pullup * 0.97
    rd_low, rd_high = receiver_pulldown_ohm * 0.98, receiver_pulldown_ohm * 1.02
    input_leak = 20e-6  # One E28 Schmitt input, then local buffered fanout.
    sink = input_leak + extra_output_sink_allocation_a
    vhigh = (low - rp_high * sink) / (1 + rp_high / rd_low)
    voff = input_leak * rd_high
    maximum_sink_at_vih = (low - 2.0) / rp_high - 2.0 / rd_low - input_leak
    return dict(
        external_header="J106.4",
        external_net="P03_ALL_SOURCES_READY",
        source_driver="U25 LTC2910HGN#PBF pin12 active-low RESET open-drain",
        separate_internal_buck_pg_net="P03_SOURCES_READY",
        primary_source="https://www.analog.com/media/en/technical-documentation/data-sheets/2910fc.pdf",
        pullup_native_ohm=pullup,
        pullup_total_error_allocation_fraction=0.03,
        receiver_pulldown_required_ohm=receiver_pulldown_ohm,
        receiver_pulldown_total_error_allocation_fraction=0.02,
        receiver_required="E28 SN74LVC14A Schmitt input, double inversion preserves permission polarity",
        receiver_input_count=1,
        receiver_full_temperature_leakage_allocation_a=input_leak,
        extra_source_off_leakage_and_contamination_allocation_a=extra_output_sink_allocation_a,
        extra_source_off_leakage_manufacturer_guaranteed=False,
        minimum_received_high_before_wire_and_ground_offsets_v=vhigh,
        receiver_required_high_v=2.0,
        high_remaining_offset_noise_and_uncertainty_budget_v=vhigh - 2.0,
        disconnected_harness_maximum_receiver_v=voff,
        receiver_required_low_v=0.4,
        disconnected_low_margin_v=0.4 - voff,
        asserted_low_remaining_offset_and_uncertainty_budget_v=0.4 - 0.3,
        maximum_additional_sink_before_high_threshold_a=maximum_sink_at_vih,
        maximum_asserted_source_sink_current_allocation_a=high / rp_low + input_leak,
        manufacturer_low_test_current_a=0.0025,
        manufacturer_maximum_low_v=0.3,
        manufacturer_low_test_supply_v=2.3,
        low_assertion_contract_applies_only_with_aux_at_least_2v3=True,
        below_2v3_requires_independent_e28_aux_supervisor_fail_off=True,
        harness_capacitance_rise_fall_glitch_and_partial_power_qualified=False,
        resistor_lifetime_error_and_hot_leakage_verified=False,
        physical_qualified=False,
    )


def source_valid(parts):
    def r(ref):
        return value(parts, ref)

    guard_uv_rise = divider_trip(r("R101"), r("R102"), (1.176, 1.224), 150e-9)
    guard_uv_fall = divider_trip(r("R101"), r("R102"), (1.09, 1.15), 150e-9)
    pg_rise = divider_trip(r("R105"), r("R106"), (1.176, 1.224), 150e-9)
    pg_fall = divider_trip(r("R105"), r("R106"), (1.09, 1.15), 150e-9)
    thresholds = {}
    for name, top, bottom in (
        ("DIG", "R300", "R301"),
        ("ANA", "R302", "R303"),
        ("P19", "R304", "R305"),
        ("P12", "R306", "R307"),
        ("VIN", "R308", "R309"),
    ):
        thresholds[name] = divider_trip(r(top), r(bottom), (0.492, 0.508), 30e-9, 0.001)
    return dict(
        guard_input_uv_rising_v=guard_uv_rise,
        guard_input_uv_falling_v=guard_uv_fall,
        protected_input_pg_rising_v=pg_rise,
        protected_input_pg_falling_v=pg_fall,
        pg_release_below_9v8=pg_rise[1] < 9.8,
        ltc2910_positive_presence_rising_v=thresholds,
        timer_capacitance_nominal_f=r("C300"),
        timer_capacitance_tolerance=0.05,
        minimum_presence_debounce_s=r("C300") * 0.95 * 0.997 * 6e6,
        maximum_presence_debounce_s=r("C300") * 1.05 * 1.003 * 14e6,
        timer_c0g_temperature_factor_allocation=[0.997, 1.003],
        one_nf_table_timeout_scaled_to_native_capacitance_is_unverified_allocation=True,
        timer_leakage_and_contamination_qualified=False,
        buck_pg_is_precision_rail_monitor=False,
        ready_is_permission_for_staged_disconnect_not_audio_unmute=True,
    )


def negative_monitor(parts):
    """Solve shared bias + both negative inputs, including independently-off REF.

    The negative regulator outputs can remain charged while the monitor supply
    disappears. This must be checked at the input pins, not at the external net.
    """
    refs = ["R310", "R311", "R312", "R313", "R314", "R315"]
    nominal = [value(parts, r) for r in refs]

    def solve(rs, reference, n19, n12, leaks=(0.0, 0.0, 0.0), ref_connected=True):
        g = [1 / x for x in rs]
        a, b, c, d, e, f = g
        # unknowns BIAS, V7, V8; ignore REF branch only when REF truly floats.
        aa = a if ref_connected else 0
        matrix = np.array([[aa + b + c + e, -c, -e], [-c, c + d, 0], [-e, 0, e + f]])
        rhs = np.array([aa * reference - leaks[0], d * n19 - leaks[1], f * n12 - leaks[2]])
        return np.linalg.solve(matrix, rhs)

    powered = []
    off = []
    threshold19 = []
    threshold12 = []
    ref_currents = []
    for signs in itertools.product((-1, 1), repeat=6):
        rs = [r * (1 + s * 0.001) for r, s in zip(nominal, signs)]
        for reference in (0.985, 1.020):
            # Receiver threshold roots, with other negative supply already on.
            for threshold, leak in itertools.product((0.492, 0.508), (-30e-9, 30e-9)):
                for target, other, out in ((1, -17.68, threshold19), (2, -22.88, threshold12)):
                    base = solve(
                        rs,
                        reference,
                        0 if target == 1 else other,
                        other if target == 1 else 0,
                        (0, leak, leak),
                    )
                    unit = solve(
                        rs,
                        reference,
                        -1 if target == 1 else other,
                        other if target == 1 else -1,
                        (0, leak, leak),
                    )
                    out.append((threshold - base[target]) / (unit[target] - base[target]))
            normal = solve(rs, reference, -22.88, -17.68, (0, -30e-9, -30e-9))
            powered.extend(normal[1:])
            ref_currents.append((reference - normal[0]) / rs[0])
        for connected in (True, False):
            for n19, n12, leak7, leak8 in itertools.product(
                (-22.88, 0), (-17.68, 0), (-30e-9, 30e-9), (-30e-9, 30e-9)
            ):
                off.extend(solve(rs, 0, n19, n12, (0, leak7, leak8), connected)[1:])
    return dict(
        powered_input_interval_v=[min(powered), max(powered)],
        negative19_presence_magnitude_v=[min(threshold19), max(threshold19)],
        negative12_presence_magnitude_v=[min(threshold12), max(threshold12)],
        ref_unpowered_or_floating_input_interval_v=[min(off), max(off)],
        input_absolute_negative_limit_v=-0.3,
        off_inputs_respect_absolute_screen=bool(min(off) > -0.3),
        maximum_reference_load_a=max(ref_currents),
        reference_source_rating_a=0.001,
        presence_is_precision_rail_acceptance=False,
        partial_power_measured=False,
    )


def raw_sources(parts, minimum_input=9.8):
    """Reference/line/load/bias/ratio corners from the actual native dividers."""

    def r(ref):
        return value(parts, ref)

    pairs = []
    for name, pr, br, nr, nb in (
        ("high", ["R1", "R2"], "R3", ["R5"], "R4"),
        ("low", ["R44"], "R45", ["R47", "R48"], "R46"),
    ):
        pvals = []
        nvals = []
        for vin, sg, offset, bias, st, sb in itertools.product(
            (minimum_input, 13.2), (-1, 1), (-0.003, 0.003), (-100e-9, 100e-9), (-1, 1), (-1, 1)
        ):
            ref = 1 + sg * (0.013 + 0.0008 * abs(vin - 3) + 0.002 * 0.68)
            rp = sum(r(x) for x in pr) * (1 + st * 0.001)
            rn = sum(r(x) for x in nr) * (1 + st * 0.001)
            rb = r(br) * (1 + sb * 0.001)
            rbn = r(nb) * (1 + sb * 0.001)
            pvals.append((ref + offset) * (1 + rp / rb) + bias * rp)
            nvals.append(ref * rn / rbn + offset * (1 + rn / rbn) + bias * rn)
        lo_p, hi_p = min(pvals) - 0.05, max(pvals) + 0.05
        lo_n, hi_n = min(nvals) - 0.05, max(nvals) + 0.05
        load = 0.05 if name == "high" else 0.20
        duty = (hi_n + 1) / (minimum_input + hi_n + 1)
        ripple = minimum_input * duty / (68e-6 * 0.8 * 1e6)
        cuk_peak = hi_n * load / (minimum_input * 0.75) + load + ripple
        # A deliberately conservative lower-diode-drop screen. 15% itself is
        # only typical: this is not promoted to a full-temperature guarantee.
        boost_min_duty = 1 - 13.2 / lo_p
        pairs.append(
            dict(
                name=name,
                positive_envelope_v=[lo_p, hi_p],
                negative_magnitude_envelope_v=[lo_n, hi_n],
                load_allocation_each_a=load,
                maximum_cuk_peak_current_a=cuk_peak,
                cuk_limit_25c_screen_a=0.9,
                cuk_limit_hot_guaranteed=False,
                positive_minimum_duty_without_diode=boost_min_duty,
                manufacturer_minimum_duty_typical=0.15,
                guaranteed_minimum_duty_specified=False,
                minimum_raw_ripple_peak_allocation_v=0.05,
                ripple_and_efficiency_measured=False,
            )
        )
    low = pairs[1]
    # Preserve 2V LT3080 VCONTROL test differential, stronger than its1.6V
    # full-temp max dropout. N12 uses450mV max LT3090 dropout.
    maximum_output = 12.08
    return dict(
        pairs=pairs,
        minimum_input_v=minimum_input,
        p12_control_headroom_v=low["positive_envelope_v"][0] - maximum_output,
        p12_control_characterization_differential_v=2.0,
        n12_input_headroom_v=low["negative_magnitude_envelope_v"][0] - maximum_output,
        n12_required_dropout_v=0.45,
        proposed_positive14v8_minimum_duty_at13v2=1 - 13.2 / (14.8 * 0.96),
        lower_positive_setpoint_rejected_for_minimum_duty=True,
        historical_RAW_N17_now_nominal_negative14v=True,
        psrr_noise_and_compensation_qualified=False,
    )


def constant_power_feed(voltage, resistance, power, aux_current=0):
    if not (voltage > 0 and resistance >= 0 and power >= 0 and aux_current >= 0):
        raise ValueError("Invalid physical input")
    if resistance == 0:
        return dict(current_a=power / voltage + aux_current, protected_voltage_v=voltage)
    v = voltage - resistance * aux_current
    disc = v * v - 4 * resistance * power
    if disc <= 0:
        raise ValueError("No stable high-voltage constant-power operating root")
    protected = (v + math.sqrt(disc)) / 2
    return dict(current_a=power / protected + aux_current, protected_voltage_v=protected)


def capacitors(parts, pins, net):
    rows = []
    for ref, ns in pins.items():
        if ref.startswith("C") and set(ns.values()) == {net, "AGND"}:
            text = parts[ref].findtext("value")
            tolerance = 0.05 if "C0G" in text and "5%" in text else 0.20
            nominal = value(parts, ref)
            # Dielectric class temperature excursion is independent of initial
            # capacitance tolerance. Generic/electrolytic parts have no inferred
            # complete temperature/lifetime bound from their value string.
            factor = 1.003 if "C0G" in text else 1.15 if "X7R" in text else 1.22 if "X7S" in text else None
            initial = nominal * (1 + tolerance)
            rows.append(
                dict(
                    ref=ref,
                    value=text,
                    nominal_f=nominal,
                    max_tolerance=tolerance,
                    initial_tolerance_only_maximum_f=initial,
                    declared_dielectric_positive_temperature_factor=factor,
                    known_initial_and_dielectric_temperature_maximum_f=initial * factor if factor else None,
                    exact_mpn_bias_aging_lifetime_bound_verified=False,
                )
            )
    initial = sum(x["initial_tolerance_only_maximum_f"] for x in rows)
    return dict(
        net=net,
        components=rows,
        maximum_known_direct_f=initial,
        maximum_known_direct_f_basis="INITIAL TOLERANCE ONLY; partial direct inventory, not full-temperature maximum",
        initial_tolerance_only_direct_subtotal_f=initial,
        known_dielectric_temperature_adjusted_subtotal_f=sum(
            x["known_initial_and_dielectric_temperature_maximum_f"] or 0 for x in rows
        ),
        positive_temperature_bound_missing_refs=[
            x["ref"] for x in rows if x["declared_dielectric_positive_temperature_factor"] is None
        ],
        complete_full_temperature_maximum_f=None,
        complete_network_inventory_verified=False,
    )


def disconnect_startup():
    # E28 retained known bulk + explicit unverified complete-network reserves.
    result = {}
    for name, n, cap, cdvdt, load, local, ilim in (
        ("DIG", 4, 0.0071, 47e-9, 2.4, 0.024, [7.2, 8.7]),
        ("ANA", 3, 0.0022, 100e-9, 0.251, 0.008, [1.75, 2.25]),
    ):
        slew = 9e-6 / (cdvdt * 0.95 * 0.997)
        cap_current = cap * slew
        duration = 5.1 / slew
        # Constant full load throughout ramp. Output-cap energy is½CV²;
        # switch energy includes½CV² plus constant-load ramp dissipation.
        energy = 0.5 * cap * 5.1**2 + 0.5 * 5.1 * (load + local) * duration
        result[name] = dict(
            parallel_count=n,
            steady_internal_ron_max_each_ohm=0.020,
            steady_parallel_ron_max_ohm=0.020 / n,
            all_on_required=True,
            master_alone_charges_full_bulk=True,
            complete_capacitance_scenario_f=cap,
            complete_capacitance_verified=False,
            dvdt_nominal_f=cdvdt,
            dvdt_tolerance=0.05,
            dvdt_c0g_temperature_minimum_factor=0.997,
            maximum_slew_v_per_s=slew,
            maximum_capacitor_current_a=cap_current,
            full_load_present_during_startup_a=load,
            source_total_startup_current_a=load + local + cap_current,
            ilim_native_test_point_a=ilim,
            one_master_energy_screen_j=energy,
            worst_energy_needs_minimum_slew_and_thermal_network=True,
            startup_soa_measured=False,
        )
    result["sequence"] = (
        "All-six-source presence debounce, then digital master/followers; only fourth digital SPLYGD permits analog master."
    )
    result["OV_recovery"] = "Explicit EN reset/fault latch required; autonomous OV recovery can bypass dVdt."
    return result


def complete_input_chain(parts, protected_power_w, startup_power_w):
    """Bind the selected inlet/harness boundary without inventing hot contacts.

    The adapter voltage is specified at the plug: its captive cable is already
    inside that boundary. Resistance entries below retain their catalog/screen/
    measured-allocation distinction. Unknown hot lifetime terms are never zero.
    """
    import hashlib
    import json

    from .spec import REPO

    path = REPO / "hardware/cad/a12/harness/input-feed.json"
    contract = json.loads(path.read_text())
    adapter = contract["adapter"]
    jack = contract["jack"]
    vh = contract["internal_connectors"]
    wire = contract["wire"]
    span = max(
        abs(t - adapter["reference_temperature_c"])
        for t in adapter["temperature_coefficient_applicable_range_c"]
    )
    error = (
        adapter["nominal_v"]
        * (adapter["voltage_tolerance_fraction"] + span * adapter["temperature_coefficient_fraction_per_c"])
        + adapter["ripple_maximum_peak_to_peak_v"]
    )
    plug = [adapter["nominal_v"] - error, adapter["nominal_v"] + error]
    allocations = {
        "jack_catalog_initial_contact_pair": jack["contact_maximum_ohm_catalog"] * jack["series_contacts"],
        "vh_catalog_environmental_four_interfaces": vh["contact_environmental_maximum_ohm_catalog"]
        * vh["series_contacts_in_complete_loop"],
        "wire_pair_measured_acceptance_requirement": wire[
            "wire_pair_hot_resistance_acceptance_allocation_ohm"
        ],
        "inlet_native_copper_conditional_screen": 0.00905,
        "q101_hot_rds_engineering_allocation": 0.040,
        "tps2663_hot_ron_allocation": 0.053,
    }
    total = contract["project"]["complete_feed_scenario_ohm"]
    guard_internal = (
        allocations["q101_hot_rds_engineering_allocation"] + allocations["tps2663_hot_ron_allocation"]
    )
    points = {}
    uv = source_valid(parts)
    for name, power in (("steady", protected_power_w), ("digital_master_charge_full_load", startup_power_w)):
        point = constant_power_feed(plug[0], total, power, 0.09)
        point["dc_in_before_guard_voltage_v"] = (
            point["protected_voltage_v"] + guard_internal * point["current_a"]
        )
        point["protected_9v8_floor_margin_v"] = point["protected_voltage_v"] - 9.8
        point["guard_uv_falling_margin_at_dc_in_v"] = (
            point["dc_in_before_guard_voltage_v"] - uv["guard_input_uv_falling_v"][1]
        )
        point["guard_pg_rising_margin_at_protected_node_v"] = (
            point["protected_voltage_v"] - uv["protected_input_pg_rising_v"][1]
        )
        point["adapter_startup_dynamic_droop_included"] = False
        points[name] = point
    return dict(
        selected_contract=str(path.relative_to(REPO)),
        selected_contract_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        static_plug_terminal_interval_v=plug,
        adapter_captive_cable_counted_again=False,
        resistance_entries_ohm=allocations,
        catalog_and_screen_subtotal_ohm=sum(allocations.values()),
        total_conditional_feed_allocation_ohm=total,
        unproved_remainder_for_rear_fuse_and_p03_copper_ohm=total - sum(allocations.values()),
        remainder_is_established_upper_bound=False,
        all_contact_hot_lifetime_bounds_established=False,
        mandatory_rear_fuse="0451006.MRL 6A",
        redundant_p03_series_fuse_present=False,
        maximum_feed_resistance_at_9v8_startup_floor_ohm=(plug[0] - 9.8) / (startup_power_w / 9.8 + 0.09),
        conditional_operating_points=points,
        initial_raw_and_buck_startup_overlap_bounded=False,
        complete_feed_and_dynamic_startup_qualified=False,
        physical_tests_performed=0,
    )
