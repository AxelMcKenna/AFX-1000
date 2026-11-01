"""Native-valued bipolar source/load/startup envelopes; no physical guarantee.

The LT3471 minimum switch-current limit used here is specified at25°C; it is
not a full-temperature startup guarantee. New hot-swap IQ, dynamic/ground
budgets and external board loads remain explicitly unverified allocations.
"""

import copy
import hashlib
import itertools
import json

from ...common.netlists import netlist
from .models import raw_sources, value
from .spec import REPO, ROOT

STAGES = {
    "P19": (["R20", "R21"], "R22", "R24", 0.026),
    "P12": (["R25", "R26"], "R27", "R29", 0.151),
    "N19": (["R34", "R35"], "R36", "R38", 0.026),
    "N12": (["R39", "R40"], "R41", "R43", 0.151),
}


def negative_startup_droop(parts, external_current):
    """Conditional LT3471 screen; never promote a 25°C limit to a hot guarantee."""
    state = ledger(parts)
    row = state["raw_local_current_ledger"]["RAW_N17"]
    raw_current = row["required_raw_output_current_a"] + external_current - 0.151
    output_max = state["rails"]["N12"]["source_magnitude_v"][1]
    raw_normal = row["raw_voltage_upper_v"]

    def peak(magnitude):
        vin = 9.8
        duty = (magnitude + 1) / (vin + magnitude + 1)
        return raw_current * (1 + magnitude / (vin * 0.75)) + vin * duty / (68e-6 * 0.8 * 1e6)

    minimum_raw = output_max + 0.450 + 0.050
    lo, hi = 0.0, raw_normal
    for _ in range(80):
        mid = (lo + hi) / 2
        if peak(mid) > 0.9:
            hi = mid
        else:
            lo = mid
    return dict(
        external_total_current_a=external_current,
        raw_current_required_a=raw_current,
        source_output_upper_magnitude_v=output_max,
        ldo_dropout_allocation_v=0.450,
        additional_headroom_reserve_v=0.050,
        minimum_raw_for_allocated_headroom_v=minimum_raw,
        switch_peak_at_normal_raw_a=peak(raw_normal),
        switch_peak_at_minimum_raw_a=peak(minimum_raw),
        raw_magnitude_at_0v9_25c_switch_limit_v=lo,
        remaining_raw_excursion_before_headroom_allocation_v=lo - minimum_raw,
        nominal_frequency_allocation_hz=1e6,
        efficiency_allocation=0.75,
        inductor_minimum_allocation_h=68e-6 * 0.8,
        diode_forward_allocation_v=1,
        full_temperature_frequency_and_current_limit_guaranteed=False,
        raw_current_limit_transient_regulation_and_stability_verified=False,
        source_good_waveform_verified=False,
        startup_qualified=False,
    )


def source_corners(parts):
    result = {}
    for name, (top, bottom, bleed, load) in STAGES.items():
        negative = name.startswith("N")
        rf = sum(value(parts, r) for r in top)
        rg = value(parts, bottom)
        ldo = 0.006 if negative else 0.015 if name == "P12" else 0.012
        ref_error = 0.0035 if negative else 0.001
        vals = []
        for sr, st, sb, so, ibp, ibn, sl in itertools.product((-1, 1), repeat=7):
            ref = 2.5 * (1 + sr * ref_error)
            rt = rf * (1 + st * 0.001)
            rb = rg * (1 + sb * 0.001)
            vals.append((ref + so * 350e-6 + ibp * 5e-9 * 1000) * (1 + rt / rb) + ibn * 5e-9 * rt + sl * ldo)
        nominal = 19 if "19" in name else 12
        window = [nominal * 0.99, nominal * 1.01]
        lo, hi = min(vals), max(vals)
        result[name] = dict(
            native_top_refs=top,
            native_top_sum_ohm=rf,
            native_bottom_ref=bottom,
            source_magnitude_v=[lo, hi],
            target_magnitude_v=window,
            absolute_low_side_total_drop_budget_v=lo - window[0],
            no_load_upper_margin_v=window[1] - hi,
            external_current_allocation_a=load,
            external_current_latest_board_bom_verified=False,
            bleed_current_upper_allocation_a=hi / (value(parts, bleed) * 0.97),
            bleed_ref=bleed,
            bleed_total_resistance_error_allocation_fraction=0.03,
            dynamic_excursion_allocation_v=0.010,
            source_and_load_ground_plus_existing_harness_allocation_v=0.005,
            proposed_remaining_stage_dc_drop_budget_v=lo - window[0] - 0.015,
            complete_endpoint_and_dynamic_bound_verified=False,
        )
    return result


def ledger(parts, controller_current=0.003):
    rails = source_corners(parts)
    raw = raw_sources(parts)
    hi = raw["pairs"][0]
    low = raw["pairs"][1]
    rv = {
        "RAW_P22": hi["positive_envelope_v"][1],
        "RAW_N22": hi["negative_magnitude_envelope_v"][1],
        "RAW_P17": low["positive_envelope_v"][1],
        "RAW_N17": low["negative_magnitude_envelope_v"][1],
    }
    for name, row in rails.items():
        voltage = row["source_magnitude_v"][1]
        if name.startswith("P"):
            top, bottom = ("R304", "R305") if name == "P19" else ("R306", "R307")
            mon = voltage / ((value(parts, top) + value(parts, bottom)) * 0.999) + 30e-9
        else:
            mon = (voltage + 1.020) / (value(parts, "R313" if name == "N19" else "R315") * 0.999) + 30e-9
        row["presence_monitor_current_upper_a"] = mon
        row["new_controller_source_current_reserved_a"] = controller_current
        row["new_controller_current_selected_or_guaranteed"] = False
        row["source_output_current_required_a"] = (
            row["external_current_allocation_a"]
            + row["bleed_current_upper_allocation_a"]
            + mon
            + controller_current
        )
    feedback = {
        "RAW_P22": rv["RAW_P22"] / ((value(parts, "R1") + value(parts, "R2") + value(parts, "R3")) * 0.999),
        "RAW_N22": (rv["RAW_N22"] + 0.003) / (value(parts, "R5") * 0.999),
        "RAW_P17": rv["RAW_P17"] / ((value(parts, "R44") + value(parts, "R45")) * 0.999),
        "RAW_N17": (rv["RAW_N17"] + 0.003) / ((value(parts, "R47") + value(parts, "R48")) * 0.999),
    }
    # No fictitious30mA ground load is added for LT3080 control current:
    # its pass-transistor drive current reaches OUT and is already in IOUT.
    negative_iq = 0.0225
    rows = {
        "RAW_P22": dict(
            rail="P19",
            opamp_iq_a=4 * 0.0015,
            reference_bias_a=0,
            ldo_ground_current_envelope_a=0,
            control_output_and_set_reserve_a=0.0002,
        ),
        "RAW_N22": dict(
            rail="N19",
            opamp_iq_a=2 * 0.0015,
            reference_bias_a=(rv["RAW_N22"] - 2.5 * (1 - 0.0035)) / (value(parts, "R18") * 0.97),
            ldo_ground_current_envelope_a=negative_iq,
            control_output_and_set_reserve_a=0.0002,
        ),
        "RAW_P17": dict(
            rail="P12",
            opamp_iq_a=0,
            reference_bias_a=0,
            ldo_ground_current_envelope_a=0,
            control_output_and_set_reserve_a=10.2e-6,
        ),
        "RAW_N17": dict(
            rail="N12",
            opamp_iq_a=0,
            reference_bias_a=0,
            ldo_ground_current_envelope_a=negative_iq,
            control_output_and_set_reserve_a=51e-6,
        ),
    }
    for net, row in rows.items():
        row.update(
            source_output_load_a=rails[row["rail"]]["source_output_current_required_a"],
            raw_feedback_current_a=feedback[net],
            raw_voltage_upper_v=rv[net],
        )
        row["required_raw_output_current_a"] = sum(
            row[k]
            for k in [
                "source_output_load_a",
                "opamp_iq_a",
                "reference_bias_a",
                "ldo_ground_current_envelope_a",
                "control_output_and_set_reserve_a",
                "raw_feedback_current_a",
            ]
        )
        allocation = 0.05 if net.endswith("22") else 0.20
        row["old_independent_raw_current_allocation_a"] = allocation
        row["old_allocation_current_margin_a"] = allocation - row["required_raw_output_current_a"]
    allocated_power = sum(rv[n] * (0.05 if n.endswith("22") else 0.20) for n in rows)
    steady_power = sum(
        row["raw_voltage_upper_v"] * row["required_raw_output_current_a"] for row in rows.values()
    )
    by_ic = {
        ic: sum(rows[n]["raw_voltage_upper_v"] * rows[n]["required_raw_output_current_a"] for n in nets)
        for ic, nets in {"U1": ("RAW_P22", "RAW_N22"), "U13": ("RAW_P17", "RAW_N17")}.items()
    }
    phases = []
    for rail, ceiling in [("P19", 0.050), ("N19", 0.050), ("P12", 0.210), ("N12", 0.220)]:
        net = next(n for n, r in rows.items() if r["rail"] == rail)
        phase = copy.deepcopy(rows)
        phase[net]["required_raw_output_current_a"] += ceiling - rails[rail]["external_current_allocation_a"]
        power = sum(r["raw_voltage_upper_v"] * r["required_raw_output_current_a"] for r in phase.values())
        phase_by_ic = {
            ic: sum(phase[n]["raw_voltage_upper_v"] * phase[n]["required_raw_output_current_a"] for n in nets)
            for ic, nets in {"U1": ("RAW_P22", "RAW_N22"), "U13": ("RAW_P17", "RAW_N17")}.items()
        }
        raw_current = phase[net]["required_raw_output_current_a"]
        vin = 9.8
        v = rv[net]
        if rail.startswith("N"):
            duty = (v + 1) / (vin + v + 1)
            ripple = vin * duty / (68e-6 * 0.8 * 1e6)
            peak = raw_current * (1 + v / (vin * 0.75)) + ripple
        else:
            duty = 1 - vin / (v + 1)
            ripple = vin * duty / (33e-6 * 0.8 * 1e6)
            peak = raw_current * v / (vin * 0.75) + ripple / 2
        phases.append(
            dict(
                rail=rail,
                external_total_current_ceiling_candidate_a=ceiling,
                known_source_internal_load_and_controller_current_a=raw_current - ceiling,
                required_raw_output_current_a=raw_current,
                raw_output_power_all_four_w=power,
                raw_input_power_with_75percent_allocation_w=power / 0.75,
                raw_output_power_by_converter_w=phase_by_ic,
                all_converter_loss_assigned_to_ic_screen_w={ic: p / 3 for ic, p in phase_by_ic.items()},
                difference_from_existing_coupled_raw_power_allocation_w=(power - allocated_power) / 0.75,
                switch_peak_current_25c_screen_a=peak,
                passes_0v9_25c_only_screen=peak < 0.9,
                guaranteed_full_temperature_source_current_interval_a=None,
                requires_one_bipolar_stage_at_a_time_after_positive_5v_charge=True,
                first_charge_capacitance_bound_verified=False,
                startup_thermal_and_soa_qualified=False,
            )
        )
    return dict(
        rails=rails,
        raw_local_current_ledger=rows,
        existing_coupled_raw_output_power_allocation_w=allocated_power,
        required_steady_raw_output_power_w=steady_power,
        required_steady_raw_output_power_by_converter_w=by_ic,
        steady_all_converter_loss_assigned_to_ic_screen_w={ic: p / 3 for ic, p in by_ic.items()},
        old_independent_raw_current_allocations_cover_full_ledger=all(
            r["old_allocation_current_margin_a"] >= 0 for r in rows.values()
        ),
        positive_control_current_is_added_as_ground_load=False,
        lt3090_ground_current_points_a={"at_100ma_output": 0.005, "at_600ma_output": 0.0225},
        lt3090_current_envelope_interpolation_claimed=False,
        lt3090_ground_current_envelope_scope="Conservative600mA datasheet maximum used as design allocation; actual lower-load envelope remains a qualification item",
        adc_35ma_per_sign_latest_bom_and_drive_bound_verified=False,
        staged_current_ceiling_scenarios=phases,
        unavailable_startup_guarantees=[
            "LT3471hotminimumcurrentlimit",
            "fulltemperatureminimumswitchingfrequency",
            "effectiveMLCCcapacitance/compensation",
            "completeprotectednetworkcapacitance",
            "source/outputcurrenttransients",
            "newcontrollersourceIQ",
        ],
        controller_rejection={
            "LM5067": {"manufacturer_maximum_rsense_ohm": 0.1, "nominal_minimum_trip_at_that_rsense_a": 0.5},
            "LM5069": {"manufacturer_maximum_rsense_ohm": 0.1, "nominal_minimum_trip_at_that_rsense_a": 0.55},
        },
        controller_rejection_primary_sources=[
            "https://www.ti.com/lit/ds/symlink/lm5067.pdf",
            "https://www.ti.com/lit/ds/symlink/lm5069.pdf",
        ],
        primary_local_current_sources=[
            "https://www.ti.com/lit/ds/symlink/opa192.pdf",
            "https://www.analog.com/media/en/technical-documentation/data-sheets/3080fc.pdf",
            "https://www.analog.com/media/en/technical-documentation/data-sheets/3090fa.pdf",
        ],
        full_system_startup_qualified=False,
        physical_tests_performed=0,
        build_ready=False,
    )


def generate():
    parts, _ = netlist(ROOT / "generated/netlist.xml")
    base = ledger(parts)
    trial = copy.deepcopy(parts)
    trial["R40"].find("value").text = "181k 0.01% 5ppm"
    recenter = ledger(trial)
    shunts = []
    for resistance in (0.287, 0.292, 0.295):
        cb_min = 0.045 / (resistance * 1.001)
        acl_max = 0.055 * 1.38 / (resistance * 0.999)
        acl_min = 0.045 * 1.05 / (resistance * 1.001)
        known_external = 0.151 + 12.12 / (47000 * 0.99)
        shunts.append(
            dict(
                shunt_nominal_comparison_ohm=resistance,
                shunt_total_error_assumed_fraction=0.001,
                shunt_exact_mpn_selected=False,
                shunt_total_temperature_aging_assembly_error_verified=False,
                circuit_breaker_current_minimum_a=cb_min,
                active_current_limit_minimum_a=acl_min,
                active_current_limit_maximum_a=acl_max,
                external_151ma_plus_known_e28_bleed_a=known_external,
                remaining_cb_margin_before_unbounded_hot_leaks_a=cb_min - known_external,
                shunt_steady_drop_at_known_external_upper_r_v=known_external * resistance * 1.001,
                known_220uf_plus_initial20percent_charge_time_constant_full_load_at_acl_min_s=220e-6
                * 1.2
                * 12.12
                / (acl_min - known_external),
                complete_capacitance_and_circuit_breaker_timer_acceptance_verified=False,
                raw_droop=negative_startup_droop(trial, acl_max),
                controller_primary_source="https://www.analog.com/media/en/technical-documentation/data-sheets/4252fa.pdf",
                physical_qualified=False,
            )
        )
    report = dict(
        revision="P03-bipolar-ledger-development",
        base_native=base,
        n12_r40_181k_recenter_unimplemented=recenter,
        n12_264v73ma_ltc4252a_candidate_droop_unimplemented=negative_startup_droop(trial, 0.26473),
        n12_253v3ma_comparison_droop_unimplemented=negative_startup_droop(trial, 0.2533),
        n12_ltc4252a_shunt_comparisons_unimplemented=shunts,
        source_sha256={
            str(p.relative_to(REPO)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in [ROOT / "power_p03.kicad_sch", ROOT / "generated/netlist.xml", ROOT / "bipolar.py"]
        },
    )
    (ROOT / "generated/bipolar-ledger.json").write_text(json.dumps(report, indent=2) + "\n")
    for r, x in base["raw_local_current_ledger"].items():
        print(r, x["required_raw_output_current_a"], x["old_allocation_current_margin_a"])
    for phase in base["staged_current_ceiling_scenarios"]:
        print(phase)
    return report


if __name__ == "__main__":
    generate()
