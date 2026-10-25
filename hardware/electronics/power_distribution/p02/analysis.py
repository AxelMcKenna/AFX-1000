"""Independent P02 source, endpoint, input-power and prerequisite analysis."""

import argparse
import hashlib
import json

from ...common.netlists import netlist, number
from .check import contract
from .distribution import LOADS, MANIFEST, REPO, voltage_bounds
from .loads import endpoint_contract
from .spec import ROOT


def source_corners(parts):
    def r(ref):
        return number(parts[ref].findtext("value"))

    # Guaranteed initial/box-TC/line/load errors, then separately allocated
    # assembly/aging/humidity and finite-loop thermal reserves; no RSS.
    terms = dict(
        initial=0.001,
        box_temperature=5 * 2e-6 * 165,
        line=5 * 10e-6 * 9.9,
        load=5 * 80e-6 * 0.001,
        assembly_aging_humidity_allocation=0.002,
        opamp_offset=0.000350,
        positive_bias=10e-9 * r("R6"),
    )
    common = sum(terms.values())
    leakage = 30e-9 * r("R6")
    corners = {}
    details = {}
    for rail, top, bottom, fb, reg_error in (
        ("DIG", "R8", "R9", "R10", 0.006 + 0.004 + 0.0003 + 0.001),
        ("ANA", "R12", "R13", "R14", 0.002 + 0.0005 + 0.0003 + 0.000054),
    ):
        ratio = r(top) / r(bottom)
        # Each precision resistor has an allocated +/-0.1% TOTAL error,
        # including TC and aging, not merely its room-temperature tolerance.
        gain_low = 1 + ratio * 0.999 / 1.001
        gain_high = 1 + ratio * 1.001 / 0.999
        bias = 5e-9 * (r(fb) + r(top) * r(bottom) / (r(top) + r(bottom)))
        corners[rail] = [
            (5 - common - leakage - bias) * gain_low - reg_error,
            (5 + common + bias) * gain_high + reg_error,
        ]
        details[rail] = dict(
            nominal_v=5 * (1 + ratio),
            source_interval_v=corners[rail],
            regulator_offset_load_line_thermal_sum_v=reg_error,
            negative_bias_v=bias,
            gain_interval=[gain_low, gain_high],
        )
    return corners, dict(
        reference_symmetric_terms_v=terms,
        one_sided_filter_leakage_v=leakage,
        capacitor_leakage_guaranteed=False,
        precision_total_resistor_error_fraction=0.001,
        channels=details,
    )


def legacy_domains():
    path = REPO / "hardware/electronics/power_supply/generated/netlist.xml"
    parts, pins = netlist(path)
    for ref in ("U1", "U13"):
        assert pins[ref]["8"] == "VIN_PROTECTED", (ref, "raw converter VIN domain changed")
    for ref in ("L1", "L2", "L6", "L7"):
        assert pins[ref]["1"] == "VIN_PROTECTED", ref
    for ref in ("R6", "R7", "R49", "R50"):
        assert pins[ref]["1"] == "5V_DIG_SRC" and number(parts[ref].findtext("value")) == 4700, ref
    assert pins["U4"]["2"] == "5V_DIG_SRC"
    for ref in ("U10", "U11"):
        assert pins[ref]["5"] == "5V_DIG_SRC", ref
    return dict(
        raw_converter_vin_net="VIN_PROTECTED",
        raw_inductors_vin_net="VIN_PROTECTED",
        digital_source_local_consumers=[
            "R6",
            "R7",
            "R49",
            "R50",
            "U4.2 REF5025",
            "U10.5 LT3090 SHDN",
            "U11.5 LT3090 SHDN",
        ],
        digital_local_allocation_a=0.018,
        source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
    )


def return_architecture():
    rho_hot = 1.724e-8 * (1 + 0.00393 * 80)
    bars = {}
    for rail, length in (("analog", 0.180), ("digital", 0.090)):
        copper = rho_hot * length / (20e-6)
        joints = 2 * 0.000350
        access = 0.001000
        total = copper + joints + access
        assert total <= 0.002
        bars[rail] = dict(
            maximum_copper_length_m=length,
            minimum_section_mm2=20,
            example_section_mm=[10, 2],
            copper_at_100c_ohm=copper,
            two_hot_eol_joint_allocation_ohm=joints,
            combined_source_and_e26_access_allocation_ohm=access,
            total_ohm=total,
            analysis_upper_ohm=0.002,
        )
    return dict(
        bars=bars,
        quiet_source_attachments=["P02.J5.1", "P02.J6.1"],
        e26_top_attachment_proposals=dict(
            analog=dict(centre_board_mm=[111, 39.5], area_mm=[10, 8]),
            digital=dict(centre_board_mm=[128, 27], area_mm=[10, 8]),
            datum_enclosure_mm=[8, 108.5, 4.6],
            implemented_in_pcb=False,
            reservation_to_original_header_star_path_included_in_access_allocation=True,
        ),
        full_strap_length_includes_bends=True,
        top_studs_supports_and_insulation_implemented=False,
        a11_clearance_or_support_demonstrated=False,
        existing_0p3mm_underside_gap_accepts_nuts=False,
        supplemental_converter_return="E26.J3.2 -> converter.J4.2 AGND; requires real fanout assembly",
        contact_limits_guaranteed=False,
        mechanical_fit_verified=False,
    )


def operating_limits(sources):
    dig_load = sum(i for r, _, i in LOADS.values() if r == "DIG")
    ana_load = sum(i for r, _, i in LOADS.values() if r == "ANA")
    dig_bleed_max = sources["DIG"][1] / (909 * 0.99)
    dig_total = dig_load + 0.018 + dig_bleed_max
    ana_total = ana_load + sources["ANA"][1] / (2210 * 0.99)
    pre_current = dig_total + ana_total + 0.025 + 0.001
    pre_low, pre_high = 6 * 0.975 - 0.050, 6 * 1.025 + 0.050
    control_current = 0.080  # full 3A guaranteed maximum, not scaled typical
    digital_heat = (pre_high - sources["DIG"][0]) * dig_total + (13.2 - sources["DIG"][0]) * control_current
    analog_heat = (pre_high - sources["ANA"][0]) * ana_total + pre_high * 0.025
    # Preserve existing conservative upper raw-rail envelopes and 75% minimum
    # efficiency ALLOCATION, charged to the native VIN_PROTECTED domain.
    raw_screen = json.loads(
        (REPO / "hardware/electronics/power_supply/generated/electrical-screens.json").read_text()
    )
    raw_input_power = sum(
        2 * p["raw_envelope_v"][1] * p["load_allocation_each_a"] / p["minimum_efficiency_allocation"]
        for p in raw_screen["power"]["raw_pairs"]
    )
    pre_power = pre_high * pre_current / 0.85
    auxiliaries_power = 13.2 * 0.0711903095
    other_vin_power = 13.2 * (control_current + 0.015)  # control and dual-amplifier reserve
    total_power = raw_input_power + pre_power + auxiliaries_power + other_vin_power
    input_current = total_power / 10.5
    tau_min = 10000 * 0.999 * 12.69e-6
    digital_cmax = 0.0071  # E26bulk+loadsource caps including tolerance, explicit bound
    analog_cmax = 0.0011
    dig_charge = digital_cmax * sources["DIG"][1] / tau_min
    ana_charge = analog_cmax * sources["ANA"][1] / tau_min
    return dict(
        digital_protected_a=dig_load,
        analog_protected_a=ana_load,
        digital_local_source_allocation_a=0.018,
        digital_bleed_max_a=dig_bleed_max,
        digital_regulator_total_a=dig_total,
        analog_regulator_total_a=ana_total,
        pre_regulator_total_a=pre_current,
        module_rating_a=6,
        pre_voltage_allocation_v=[pre_low, pre_high],
        pre_voltage_guaranteed=False,
        dropout=dict(
            digital_in_margin_v=pre_low - sources["DIG"][1] - 0.600,
            digital_control_margin_v=10.5 - sources["DIG"][1] - 1.6,
            analog_in_margin_v=pre_low - sources["ANA"][1] - 0.450,
            reference_input_margin_v=pre_low - 5.3,
        ),
        thermal=dict(
            digital_pass_plus_control_max_w=digital_heat,
            analog_pass_plus_ground_max_w=analog_heat,
            module_loss_at_85pct_allocation_w=pre_power * 0.15,
            ambient_design_c=60,
            junction_design_limit_c=110,
            digital_total_theta_required_c_per_w=(110 - 60) / digital_heat,
            digital_junction_case_c_per_w=3,
            analog_total_theta_required_c_per_w=(110 - 60) / analog_heat,
            measured_or_layout_qualified=False,
        ),
        upstream=dict(
            raw_generators_input_w=raw_input_power,
            pre_buck_input_w=pre_power,
            auxiliaries_w=auxiliaries_power,
            control_and_opamp_w=other_vin_power,
            total_input_w=total_power,
            input_current_at_10v5_a=input_current,
            old_e23_min_limit_a=2.874,
            old_adapter_rating_a=3,
            existing_input_path_passes=input_current <= 2.874,
            new_guard_minimum_normal_capacity_a=4,
            replacement_input_profile_implemented=False,
        ),
        startup=dict(
            reference_tau_min_s=tau_min,
            ramp_screen_scope="reference-acquired preconnected RC ramp only; initial SET-current floor is excluded",
            initial_set_floor_inrush_qualified=False,
            initial_set_floor_digital_cap_current_demand_a=digital_cmax * 0.000051 / 80e-9,
            initial_set_floor_analog_cap_current_demand_a=analog_cmax * 0.000102 / 80e-9,
            digital_preconnected_charge_allocation_a=dig_charge,
            digital_total_with_charge_a=dig_total + dig_charge,
            analog_preconnected_charge_allocation_a=ana_charge,
            analog_total_with_charge_a=ana_total + ana_charge,
            preconnected_ramp_current_screen_passes=dig_total + dig_charge < 3
            and ana_total + ana_charge < 0.5,
            digital_set_current_floor_v=0.000051 * 6800,
            analog_set_current_floor_v=0.000102 * 6800,
            late_e26_gate_closure_current_limited=False,
            digital_late_closure_stored_energy_j=0.5 * digital_cmax * sources["DIG"][1] ** 2,
            analog_late_closure_stored_energy_j=0.5 * analog_cmax * sources["ANA"][1] ** 2,
            measured_startup_stability=False,
        ),
        minimum_load=dict(
            digital_min_a=sources["DIG"][0] / (909 * 1.01), required_for_load_reg_table_a=0.005
        ),
        seed_filter=dict(
            native_r1_ohm=0.47,
            tolerance=0.01,
            allocated_module_current_a=1,
            worst_drop_v=0.47 * 1.01,
            worst_heat_w=0.47 * 1.01,
            nameplate_w=1,
            thermal_derating_qualified=False,
        ),
    )


def analyze():
    parts, pins = netlist(ROOT / "generated/netlist.xml")
    native = contract(parts, pins)
    sources, details = source_corners(parts)
    distribution = voltage_bounds(sources)
    limits = operating_limits(sources)
    seed = distribution["endpoints"]["processor_5v"]
    limits["seed_filter"]["minimum_module_vin_v"] = seed["minimum_v"] - 0.4747
    limits["seed_filter"]["project_bringup_threshold_v"] = 4.0
    limits["seed_filter"]["manufacturer_module_input_limit_verified"] = False
    holds = [
        "New TPSM63606 manufacturer land pattern and entire P02 PCB/thermal design are absent.",
        "All specified cable lengths, gauges, contact limits and fanout assemblies require selection and hot/EOL qualification.",
        "Board AGND load/port spread and E26 multiport copper limits require extracted and measured confirmation.",
        "New >=4A input guard/adapter/jack/fuse/return-star profile required; existing E23 profile fails the new normal input budget.",
        "Reference assembly/aging/humidity, capacitor leakage and resistor total errors are allocations, not complete manufacturer guarantees.",
        "Closed-loop SET buffer compensation, actual module effective capacitor range, ripple and load-step reserves need simulation/measurement.",
        "Slow SET ramp screens preconnected bulk only; startup floor, shutdown, partial power and late E26 gate closure are unqualified.",
        "SD-card 3V3 current/inrush, Seed 3V3 source capacity, emitters, coil current and R1 derating remain unverified actual-load budgets.",
        "Two new <=2mohm source-to-E26 ground straps and a <=1mohm input-guard star path require new mounting/contact/return interfaces and qualification.",
    ]
    result = dict(
        revision="P02",
        native_contract=native,
        source_corners=details,
        legacy_native_power_domains=legacy_domains(),
        actual_endpoint_contract=endpoint_contract(),
        module_to_existing_psu_binding={
            "P02.J1.1": "power_supply.J1.1 VIN_PROTECTED",
            "P02.J1.2": "power_supply quiet AGND",
            "P02.J1.3": "power_supply.J5.2 POWER_READY",
            "P02.J2.1": "power_supply.J3.1 5V_DIG_SRC (old source removed)",
            "P02.J3.1": "power_supply.J2.6 V5_REG_SRC (old source removed)",
            "direct_connector_interchangeable": False,
            "native_existing_psu_replacement_layout_implemented": False,
        },
        return_architecture=return_architecture(),
        source_to_load=distribution,
        operating_limits=limits,
        qualification_holds=holds,
        dc_endpoint_interval_screen_passes=distribution["all_pass"],
        stability_qualified=False,
        startup_qualified=False,
        thermal_qualified=False,
        actual_harness_qualified=False,
        physical_power_verified=False,
        complete_unit_qualified=False,
        fabrication_released=False,
        build_ready=False,
    )
    deps = [
        MANIFEST,
        REPO / "hardware/electronics/power_supply/generated/electrical-screens.json",
        REPO / "hardware/electronics/common/circuits.py",
        ROOT / "distribution.py",
        ROOT / "analysis.py",
        ROOT / "check.py",
        ROOT / "loads.py",
        ROOT / "spec.py",
        ROOT / "generated/netlist.xml",
    ]
    result["source_sha256"] = {
        str(p.relative_to(REPO)): hashlib.sha256(p.read_bytes()).hexdigest() for p in deps
    }
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--check", action="store_true")
    args = p.parse_args()
    report = analyze()
    path = ROOT / "generated/analysis.json"
    if args.check:
        assert json.loads(path.read_text()) == json.loads(json.dumps(report)), "P02 analysis stale"
    else:
        path.write_text(json.dumps(report, indent=2) + "\n")
    for name, row in report["source_to_load"]["endpoints"].items():
        print(
            f"{name}: {row['minimum_v']:.6f}..{row['maximum_v']:.6f} V; {'PASS' if row['passes'] else 'FAIL'}"
        )
    print(
        "P02 DC screen:", report["dc_endpoint_interval_screen_passes"], "build_ready:", report["build_ready"]
    )


if __name__ == "__main__":
    main()
