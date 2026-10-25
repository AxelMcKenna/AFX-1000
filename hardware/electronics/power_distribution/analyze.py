"""Reproduce P01 corners, including shared returns and unreleased loss budgets."""

import argparse
import hashlib
import itertools
import json
import math
from pathlib import Path

from .spec import SOURCES, candidate, circuit

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[2]
BASE = ROOT.parent
TARGETS = {"V5_REG": [4.975, 5.025], "5V_DIG": [4.9, 5.1]}


def finite_nonnegative(value):
    assert isinstance(value, (int, float)) and math.isfinite(value) and value >= 0
    return value


def validate_circuit(c):
    """Independent critical manufacturer-pin and protection-boundary checks."""
    d = c["devices"]
    assert d["U2_NEW"]["part"] == "TPS62903RPJR"
    assert d["U2_NEW"]["pins"] == {
        "1": None,
        "2": "DIG_SW_NEW",
        "3": "5V_DIG_SRC",
        "4": "AGND",
        "5": "SUPPLY_ENABLE",
        "6": "VIN_PROTECTED",
        "7": "DIG_MODE_NEW",
        "8": "DIG_SS_NEW",
        "9": "DIG_FB_NEW",
    }
    assert d["U9_NEW"]["part"] == "LT3045IDD#PBF"
    assert d["U9_NEW"]["pins"] == {
        "1": "V5_PRE",
        "2": "V5_PRE",
        "3": "V5_PRE",
        "4": None,
        "5": "AGND",
        "6": "V5_PRE",
        "7": "V5_REG_SET",
        "8": "AGND",
        "9": "V5_REG_SRC",
        "10": "V5_REG_SRC",
        "11": "AGND",
    }, "LT3045 ground EP and local OUTS must not inherit LT3080 OUT/EP"
    assert d["U14_NEW"]["pins"] == {
        "1": None,
        "2": "V5_PRE",
        "3": None,
        "4": "AGND",
        "5": None,
        "6": "PREF_5V_NEW",
        "7": None,
        "8": None,
    }
    assert d["U5C_REUSED"]["pins"] == {
        "4": "RAW_P22",
        "11": "AGND",
        "10": "PREF_5V_FILTER_NEW",
        "9": "V5_REG_FB",
        "8": "V5_REG_DRIVE",
    }
    assert not c["feedback_crosses_disconnect"]
    assert c["analog_output_sense_net"] == "V5_REG_SRC"
    assert c["digital_feedback_top_net"] == "5V_DIG_SRC"
    components = {r[0]: r[1:] for r in c["passive_connections"]}
    assert len(components) == len(c["passive_connections"])
    for ref, row in {
        "R_DIG_TOP_A": [14700, "5V_DIG_SRC", "DIG_TOP_MID_NEW"],
        "R_DIG_TOP_B": [33, "DIG_TOP_MID_NEW", "DIG_FB_NEW"],
        "R_DIG_BOTTOM": [2000, "DIG_FB_NEW", "AGND"],
        "R_DIG_MODE": [21000, "DIG_MODE_NEW", "AGND"],
        "R_SET_LIMIT": [6800, "V5_REG_DRIVE", "V5_REG_SET"],
        "R_SET_FB": [100000, "V5_REG_SET", "V5_REG_FB"],
        "C_SET_COMP": [47e-9, "V5_REG_DRIVE", "V5_REG_FB"],
    }.items():
        assert components[ref] == row, ("Changed replacement circuit", ref)
    assert not c["native_erc_verified"] and not c["native_pcb_layout_implemented"]
    assert not c["build_ready"] and not c["physical_fit_verified"]


def source_corners(config):
    """Use independent worst-case signs; do not RSS unrelated error terms."""
    a = config["analog_reference"]
    reference_terms = {
        "initial_v": a["initial_error_v"],
        "full_box_temperature_range_v": 5
        * a["box_temperature_coefficient_per_c"]
        * a["box_temperature_span_c"],
        "line_full_input_range_v": 5 * a["line_regulation_per_v"] * a["line_input_span_v"],
        "reference_load_v": 5 * a["load_regulation_per_ma"] * a["reference_load_max_a"] * 1000,
        "assembly_aging_humidity_hysteresis_allocation_v": a["assembly_hysteresis_humidity_aging_reserve_v"],
        "buffer_offset_v": a["buffer_offset_v"],
        "buffer_input_bias_v": a["buffer_bias_abs_a"] * a["input_filter_ohm"],
        "buffer_feedback_bias_v": a["buffer_bias_abs_a"] * a["set_feedback_ohm"],
        "ldo_offset_v": a["ldo_offset_v"],
        "extra_ldo_load_v": a["ldo_extra_load_error_v"],
        "extra_ldo_voltage_v": a["ldo_extra_voltage_error_v"],
        "extra_ldo_line_v": a["ldo_extra_line_error_v"],
    }
    for v in reference_terms.values():
        finite_nonnegative(v)
    # Each affine error can independently reach its positive or negative bound.
    av = [
        5 + sum(s * v for s, v in zip(signs, reference_terms.values()))
        for signs in itertools.product((-1, 1), repeat=len(reference_terms))
    ]
    b = config["digital_feedback"]
    rt = sum(b["top_series_ohm"])
    rb = b["bottom_ohm"]
    assert rt > 0 and rb > 0
    dv = []
    for refsign, topsign, botsign, leak in itertools.product((-1, 1), repeat=4):
        top = rt * (1 + topsign * b["total_resistor_fraction"])
        bottom = rb * (1 + botsign * b["total_resistor_fraction"])
        ref = b["reference_v"] * (1 + refsign * b["full_temperature_reference_fraction"])
        dv.append(ref * (1 + top / bottom) + leak * b["input_leakage_abs_a"] * top)
    assert b["full_temperature_reference_fraction"] >= 0.009
    assert b["input_leakage_abs_a"] >= 70e-9
    assert a["ldo_offset_v"] >= 0.002 and a["initial_error_v"] >= 0.001
    return {
        "V5_REG": dict(dc_v=[min(av), max(av)], corners=len(av), error_terms=reference_terms),
        "5V_DIG": dict(dc_v=[min(dv), max(dv)], corners=len(dv), nominal_v=0.6 * (1 + rt / rb)),
    }


def path_budget(config, normal):
    """Both directions include copper/contact losses; analog returns are shared."""
    currents = {r["name"]: r["maximum_current_screen_a"] for r in normal}
    analog_return_abs = sum(currents[n] for n in ("P19", "N19", "P12", "N12", "V5_REG"))
    common_return_abs = analog_return_abs + currents["5V_DIG"]
    result = {}
    for name in TARGETS:
        d = config["rails"][name]["distribution"]
        for value in d.values():
            finite_nonnegative(value)
        assert d["conductor_area_mm2"] > 0 and d["copper_maximum_c"] >= 20
        multiplier = 1 + d["copper_temperature_coefficient_per_c"] * (d["copper_maximum_c"] - 20)
        terms = {}
        for direction in ("supply", "return"):
            terms[direction] = dict(
                wire_ohm=d["copper_resistivity_20c_ohm_m"]
                * d[direction + "_length_m"]
                / (d["conductor_area_mm2"] * 1e-6)
                * multiplier,
                contacts_ohm=d["mated_contacts_per_conductor"]
                * d["contact_resistance_hot_end_of_life_max_ohm"],
                source_pcb_ohm=d[f"source_pcb_{direction}_max_ohm"],
                e25_pcb_ohm=d[f"e25_pcb_{direction}_max_ohm"],
                destination_pcb_ohm=d[f"destination_pcb_{direction}_max_ohm"],
            )
        old = next(r for r in normal if r["name"] == name)
        fet = 2 * old["hot_resistance_each_fet_allocation_ohm"] / old["parallel_devices_per_side"]
        ir = analog_return_abs if name == "V5_REG" else currents[name]
        ip = currents[name]
        cross = common_return_abs * d["shared_ground_transfer_resistance_max_ohm"]
        supply_drop = ip * (sum(terms["supply"].values()) + fet)
        return_drop = ir * sum(terms["return"].values())
        # Negative-rail return flow can raise an analog rail relative to the load
        # ground. The magnitude bound deliberately does not assume cancellation.
        upper_ground_rise = return_drop + cross if name == "V5_REG" else cross
        result[name] = dict(
            supply_current_a=ip,
            shared_analog_return_magnitude_bound_a=analog_return_abs,
            own_return_current_bound_a=ir,
            common_ground_transfer_current_bound_a=common_return_abs,
            resistance_terms=terms,
            fet_path_allocation_ohm=fet,
            supply_drop_v=supply_drop,
            return_drop_or_rise_bound_v=return_drop,
            common_ground_transfer_error_v=cross,
            maximum_low_side_loss_v=supply_drop + return_drop + cross,
            maximum_high_side_ground_rise_v=upper_ground_rise,
            contact_and_copper_requirements_verified=False,
            wire_gauge_and_routing_selected=False,
        )
    return result


def analyze(config=None):
    config = candidate() if config is None else config
    c = circuit()
    validate_circuit(c)
    supply = json.loads((BASE / "power_supply/generated/electrical-screens.json").read_text())
    old = json.loads((BASE / "rail_disconnect/generated/electrical-screens.json").read_text())
    disconnect_parts = {
        p["ref"]: p for p in json.loads((BASE / "rail_disconnect/components.json").read_text())
    }
    bulk_part = disconnect_parts["C24"]
    assert bulk_part["pins"][0]["net"] == "5V_DIG" and "20%" in bulk_part["part"]
    digital_bulk_nominal_f = float(bulk_part["part"].split("uF", 1)[0]) * 1e-6
    normal = old["normal_drop"]
    for n, target in TARGETS.items():
        assert next(r for r in normal if r["name"] == n)["target_at_integrated_board_star_v"] == target
    src = source_corners(config)
    losses = path_budget(config, normal)
    rails = {}
    for n, target in TARGETS.items():
        settings = config["rails"][n]
        reserve = finite_nonnegative(settings["ripple_reserve_v"]) + finite_nonnegative(
            settings["load_step_reserve_v"]
        )
        path = losses[n]
        low = src[n]["dc_v"][0] - path["maximum_low_side_loss_v"] - reserve
        high = src[n]["dc_v"][1] + path["maximum_high_side_ground_rise_v"] + reserve
        baseline = next(r for r in normal if r["name"] == n)["source_dc_v"]
        rails[n] = dict(
            target_v=target,
            source=src[n],
            path=path,
            ripple_and_load_step_allocation_v=reserve,
            candidate_at_e25_protected_star_v=[low, high],
            low_side_margin_v=low - target[0],
            high_side_margin_v=target[1] - high,
            allocated_voltage_envelope_passes=low >= target[0] and high <= target[1],
            baseline_with_same_complete_path_v=[
                baseline[0] - path["maximum_low_side_loss_v"] - reserve,
                baseline[1] + path["maximum_high_side_ground_rise_v"] + reserve,
            ],
            implemented_on_current_psu=False,
            hardware_voltage_verified=False,
        )
    a = config["analog_reference"]
    pre = next(b for b in supply["bucks"] if b["name"] == "PRE")
    vin = [pre["minimum_dc_v"] - 0.025, pre["maximum_dc_v"] + 0.025]
    dropout = vin[0] - src["V5_REG"]["dc_v"][1] - a["dropout_allocation_v"]
    clamp = a["maximum_buffer_rail_v"] / (a["set_isolation_ohm"] * 0.99)
    drive_min = src["V5_REG"]["dc_v"][0] - a["set_current_max_a"] * a["set_isolation_ohm"] * 1.01
    ldo_power = (vin[1] - src["V5_REG"]["dc_v"][0]) * losses["V5_REG"]["supply_current_a"] + vin[1] * a[
        "ldo_ground_current_allocation_a"
    ]
    b = config["digital_feedback"]
    direct_cap_ok = (
        b["local_effective_capacitance_f"][0] >= b["minimum_direct_effective_capacitance_f"]
        and b["local_effective_capacitance_f"][1] <= b["maximum_direct_effective_capacitance_f"]
    )
    tss = [
        b["soft_start_capacitance_f"][0]
        * 0.6
        * (1 - 0.009)
        / b["tracking_gain"][1]
        / b["soft_start_current_a"][1],
        b["soft_start_capacitance_f"][1]
        * 0.6
        * (1 + 0.009)
        / b["tracking_gain"][0]
        / b["soft_start_current_a"][0],
    ]
    bulk = (
        digital_bulk_nominal_f * 1.2
        + b["extra_load_capacitance_allocation_f"]
        + b["local_effective_capacitance_f"][1]
    )
    inrush = bulk * src["5V_DIG"]["dc_v"][1] / tss[0]
    vmax = config["input_boundary_v"][1]
    vout = src["5V_DIG"]["dc_v"][1]
    ripple = (
        vout
        * (1 - vout / vmax)
        / (b["inductor_nominal_h"] * (1 - b["inductor_tolerance_fraction"]) * b["frequency_allocation_hz"][0])
    )
    peak = losses["5V_DIG"]["supply_current_a"] + inrush + ripple / 2
    duty_max = vout / config["input_boundary_v"][0]
    rms_squared = (losses["5V_DIG"]["supply_current_a"] + inrush) ** 2 + ripple**2 / 12
    conduction = rms_squared * (
        b["high_side_hot_resistance_max_ohm"] * duty_max
        + b["low_side_hot_resistance_max_ohm"] * (1 - duty_max)
        + b["inductor_hot_dcr_allocation_ohm"]
    )
    result = dict(
        revision="P01",
        scope="Conditional new-PSU source and distribution requirements, no existing power certificate replaced",
        target_boundary="E25 protected-board output star, before outgoing load harness contacts/fanouts",
        outgoing_load_harness_voltage_budget_closed=False,
        rails=rails,
        allocated_voltage_envelopes_pass=all(r["allocated_voltage_envelope_passes"] for r in rails.values()),
        analog_input_and_set_screen=dict(
            pre_boundary_v=vin,
            source_to_ldo_dropout_margin_v=dropout,
            reference_input_margin_v=vin[0] - a["reference_minimum_supply_v"],
            set_buffer_minimum_drive_v=drive_min,
            set_current_sink_requirement_a=a["set_current_max_a"],
            conservative_set_clamp_current_a=clamp,
            set_clamp_current_screen_passes=clamp <= a["set_clamp_current_max_a"],
            input_output_screen_passes=dropout > 0
            and vin[0] >= a["reference_minimum_supply_v"]
            and drive_min > 0,
            required_pre_buck_current_a=losses["V5_REG"]["supply_current_a"]
            + a["ldo_ground_current_allocation_a"]
            + a["reference_supply_current_max_a"],
            ldo_dissipation_allocation_w=ldo_power,
            required_ldo_theta_ja_at55c_to85c_c_per_w=30 / ldo_power,
            reference_aging_hysteresis_humidity_bound_guaranteed=False,
            unity_set_buffer_loop_stability_verified=False,
        ),
        digital_startup_and_thermal_screen=dict(
            soft_start_interval_allocation_s=tss,
            connected_bulk_allocation_f=bulk,
            direct_local_capacitance_in_datasheet_range=direct_cap_ok,
            connected_bulk_exceeds_direct_capacitance_limit=bulk
            > b["maximum_direct_effective_capacitance_f"],
            incremental_current_if_switch_on_before_ramp_a=inrush,
            inductor_peak_ramp_allocation_a=peak,
            peak_current_allocation_passes=peak < b["minimum_peak_current_limit_a"],
            switch_and_inductor_conduction_subtotal_allocation_w=conduction,
            converter_loss_allocation_w=b["converter_loss_allocation_w"],
            residual_for_switching_and_other_loss_w=b["converter_loss_allocation_w"] - conduction,
            required_inductor_hot_saturation_a=b["inductor_hot_saturation_requirement_a"],
            maximum_switch_peak_limit_a=b["maximum_peak_current_limit_a"],
            existing_e17_fault_current_allocation_qualified_for_replacement=False,
            required_theta_ja_c_per_w=(b["maximum_junction_allocation_c"] - b["ambient_allocation_c"])
            / b["converter_loss_allocation_w"],
            capacitance_series_damping_and_closed_loop_stability_verified=False,
            late_disconnect_closure_inrush_limited=False,
            frequency_inductor_and_peak_ramp_assumptions_verified=False,
            total_switching_loss_or_thermal_verified=False,
        ),
        circuit=c,
        manufacturer_sources=SOURCES,
        existing_voltage_targets_unchanged=True,
        source_and_protected_interfaces_unchanged=True,
        sd_card_3v3_current_inrush_and_partial_power_budget_closed=False,
        remaining_work=[
            "New PSU schematic, ERC, footprint/stencil review, layout and updated CAD reserves are required; these replacements cannot be populated on the old PSU.",
            "Prove each allocated PCB/contact/wire path including shared returns and common-ground transfer. Existing E25 connectivity routing does not establish these resistances.",
            "Qualify ADR4550 assembly/aging/humidity/hysteresis reserve; its typical lifetime graphs are not guaranteed maximum bounds.",
            "Recheck the unity SET buffer compensation and LT3045 output/load/capacitor stability, noise and load steps.",
            "Reconcile the TPS62903 direct50uF output-capacitance limit with E25digital4700uF, ESR, harness impedance and loop damping. Direct-local-capacitance compliance alone is insufficient.",
            "Bound late gate closure, discharge/restart, source overshoot and actual gate interruption; a slow buck ramp does not limit a later switch closure.",
            "Close SD-card/external3V3 load/inrush, connector fanouts, remaining loads, total input power, thermal and EMI budgets.",
            "Re-run independent E17 OV/hold-up/monitor/startup models for the completed new PSU before any assembly release.",
        ],
        native_schematic_implemented=False,
        native_pcb_routed=False,
        physical_fit_verified=False,
        physical_power_verified=False,
        design_qualified=False,
        fabrication_released=False,
        build_ready=False,
    )
    sources = [
        Path(__file__),
        ROOT / "spec.py",
        ROOT / "__init__.py",
        ROOT / "README.md",
        BASE / "power_supply/generated/electrical-screens.json",
        BASE / "rail_disconnect/generated/electrical-screens.json",
        BASE / "rail_disconnect/components.json",
        REPO / "tests/tooling/test_power_distribution.py",
    ]
    result["source_sha256"] = {
        str(p.relative_to(REPO)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources
    }
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    result = analyze()
    text = json.dumps(result, indent=2) + "\n"
    path = ROOT / "generated/analysis.json"
    if args.check:
        assert path.read_text() == text, "Stale P01 analysis; regenerate"
    else:
        path.parent.mkdir(exist_ok=True)
        path.write_text(text)
    for n, r in result["rails"].items():
        print(
            n,
            "allocated star V:",
            [round(v, 6) for v in r["candidate_at_e25_protected_star_v"]],
            "pass:",
            r["allocated_voltage_envelope_passes"],
        )
    print(
        "P01 is a conditional redesign requirement, not implemented/qualified power hardware; build_ready:false"
    )


if __name__ == "__main__":
    main()
