"""Explicit conditional corners; missing transfer/temperature guarantees are not invented."""

import hashlib
import itertools
import json
import math
from pathlib import Path

from .design import DIODE, DRIVER, PNP, RELAY, REPO, ROOT, SHUNT, STAGES, TI

OUT = ROOT / "generated"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def timer_corners(c_nom=470e-9, c_fraction=0.1, leakage=0.1e-6):
    if c_nom <= 0 or not 0 <= c_fraction < 1 or not 0 <= leakage < 3e-6:
        raise ValueError("Invalid timer interval")
    c = [c_nom * (1 - c_fraction), c_nom * (1 + c_fraction)]
    return dict(
        capacitance_assumed_f=c,
        unverified_leakage_allowance_a=leakage,
        insertion_s=[c[0] * 3.76 / (8e-6 + leakage), c[1] * 4.16 / (3e-6 - leakage)],
        fault_s=[c[0] * 3.76 / (120e-6 + leakage), c[1] * 4.16 / (51e-6 - leakage)],
        initial_timer_v_assumed_for_scenario=0,
        initial_timer_upper_bound_before_each_fault_v=None,
        guaranteed_fault_interval_s=None,
        residual_timer_note="Zero-start calculation only. ResidualCTIMER voltage shortens a later fault window; full initial/reset state envelope missing.",
        voltage_threshold_v=[3.76, 4.16],
        insertion_current_a=[3e-6, 8e-6],
        fault_current_a=[51e-6, 120e-6],
        table_conditions="LM5069RevG7.5; VIN48V unlessnoted. Actual12/19V validity and film leakage over temp/aging open.",
        guaranteed_at_operating_rails=False,
    )


def shunt_corners():
    nominal = 0.091
    terms = dict(
        initial=0.01,
        tcr_75ppm_over_declared_100k_excursion=0.0075,
        one_load_life_test=0.01 + 0.0005 / nominal,
        one_solder_heat_test=0.005 + 0.0005 / nominal,
    )
    error = math.fsum(terms.values())
    low, high = nominal * (1 - error), nominal * (1 + error)
    if high > 0.1:
        raise ValueError("Shunt exceeds100mOhm controllerselectionrule")
    return dict(
        nominal_ohm=nominal,
        declared_screen_error_terms=terms,
        interval_ohm=[low, high],
        current_limit_a=[0.0485 / high, 0.0615 / low],
        circuit_breaker_a=[0.080 / high, 0.130 / low],
        max_shunt_power_at_currentlimit_w=0.0615**2 / low,
        assumptions="WSL2512R0910FTA1%,75ppm/K componentTCR.100K componenttemperature excursion is a project screen. Separate loadlife/solder limits added as a conservative sensitivity, not a mission-profile lifetime bound. Kelvin/layout/thermoelectric error unbounded.",
        all_in_received_lifetime_bound_approved=False,
    )


def divider_corners(top, bottom=10000, rfrac=0.003, relay_ron=50):
    uvup = []
    uvdown = []
    ovup = []
    ovdown = []
    for rt, rb, v, ihys, ileak in itertools.product(
        [top * (1 - rfrac), top * (1 + rfrac)],
        [bottom * (1 - rfrac), bottom * (1 + rfrac)],
        [2.45, 2.55],
        [12e-6, 30e-6],
        [-1e-6, 1e-6],
    ):
        # UVLO hysteresis is a current SINK while below threshold (RevGFigure31).
        uvup.append(v * (1 + (rt + relay_ron) / rb) + (ihys + ileak) * (rt + relay_ron))
        uvdown.append(v * (1 + (rt + relay_ron) / rb) + ileak * (rt + relay_ron))
    for rt, rb, v, ihys, ileak in itertools.product(
        [top * (1 - rfrac), top * (1 + rfrac)],
        [bottom * (1 - rfrac), bottom * (1 + rfrac)],
        [2.4, 2.6],
        [12e-6, 30e-6],
        [-1e-6, 1e-6],
    ):
        ovup.append(v * (1 + rt / rb) + ileak * rt)
        ovdown.append(v * (1 + rt / rb) + (ileak - ihys) * rt)
    return dict(
        uv_rising_v=[min(uvup), max(uvup)],
        uv_falling_v=[min(uvdown), max(uvdown)],
        ov_rising_v=[min(ovup), max(ovup)],
        ov_falling_v=[min(ovdown), max(ovdown)],
    )


def ramp(voltage, c_load, load, cdv):
    if not all(math.isfinite(v) and v > 0 for v in [voltage, c_load, load, cdv]):
        raise ValueError("Positive finite ramp inputsrequired")
    cmin, cmax = cdv * 0.9, cdv * 1.1
    slew = [8e-6 / cmax, 42e-6 / cmin]
    time = [voltage / slew[1], voltage / slew[0]]
    return dict(
        effective_capacitance_scenario_f=[cmin, cmax],
        net_gate_current_scenario_a=[8e-6, 42e-6],
        output_slew_scenario_v_per_s=slew,
        output_only_ramp_s=time,
        local_bulk_charge_current_a=c_load * slew[1],
        downstream_bulk_plus_live_peak_a=load + c_load * slew[1],
        capacitor_pass_energy_j=0.5 * c_load * voltage**2,
        constant_live_load_pass_energy_at_slowest_j=0.5 * load * voltage * time[1],
        five_second_output_only_scenario_pass=time[1] <= 5,
        complete_startup_bound_s=None,
        full_trajectory_gate_current_bound_a=None,
        full_effective_capacitance_bound_f=None,
        output_ramp_qualified=False,
    )


def main():
    planning = ROOT / "sources/bipolar-planning.json"
    old = json.loads(planning.read_text())
    shunt = shunt_corners()
    timer = timer_corners()
    rows = {}
    for rail, d in STAGES.items():
        prev = old["rail_scenarios"][rail]
        voltage = math.sqrt(
            2 * prev["capacitor_charge_energy_j"] / prev["local_bulk_initial_tolerance_only_f"]
        )
        downstream_added = voltage / (100000 * 0.98) + 0.5e-3 + 25e-6
        r = ramp(
            voltage,
            prev["local_bulk_initial_tolerance_only_f"],
            prev["external_load_plus_native_bleeds_a"] + downstream_added,
            d["cdv"],
        )
        uv = divider_corners(d["uvtop"])
        ov = divider_corners(d["ovtop"])
        # Rtol/tcr/life2% is an unapproved envelope; LED Vf1.1..1.4 only specified25C at10mA.
        led_series = [(voltage - 1.4 - 0.065) / (d["rled"] * 1.02), (voltage - 1.1) / (d["rled"] * 0.98)]
        led = [led_series[0] - 1.4 / (10000 * 0.98), led_series[1] - 1.1 / (10000 * 1.02)]
        input_divider_current = voltage / ((d["uvtop"] + 10000) * 0.997) + voltage / (
            (d["ovtop"] + 10000) * 0.997
        )
        # Extra clamp/monitor/gate terms are declared allowances, not missing zeros.
        overhead = 1.6e-3 + led_series[1] + input_divider_current + 1e-6 + 42e-6
        power_nominal = [d["rpwr"] / (1.3e5 * 0.091) + 0.00118 * v / 0.091 for v in [0, voltage]]
        power_sensitivity = [
            d["rpwr"] * 0.997 * 0.76 / (1.3e5 * shunt["interval_ohm"][1]),
            d["rpwr"] * 1.003 * 1.24 / (1.3e5 * shunt["interval_ohm"][0])
            + 0.00118 * voltage / shunt["interval_ohm"][0],
        ]
        fault_energy_without_powerlimit = voltage * shunt["current_limit_a"][1] * timer["fault_s"][1]
        normal_power = voltage * r["downstream_bulk_plus_live_peak_a"]
        rows[rail] = dict(
            source_voltage_upper_scenario_v=voltage,
            source_planning_row=prev,
            ramp=r,
            uv_corner_scenario_v=dict(rising=uv["uv_rising_v"], falling=uv["uv_falling_v"]),
            ov_corner_scenario_v=dict(rising=ov["ov_rising_v"], falling=ov["ov_falling_v"]),
            divider_total_resistance_fraction_assumed=0.003,
            uv_relay_on_resistance25c_max_ohm=50,
            uv_default_open_voltage_from_declared_32ua_absolute_injection_v=32e-6 * 10000 * 1.003,
            default_off_full_temperature_proved=False,
            led_series_current25c_scenario_a=led_series,
            led_actual_current_after_parallel_shunt_scenario_a=led,
            led25c_scenario_above_1ma_trigger=led[0] >= 0.001,
            led25c_scenario_above_2ma_recommended=led[0] >= 0.002,
            local_input_overhead_scenario_a=overhead,
            added_downstream_pg_clamp_outbias_scenario_a=downstream_added,
            extra_load_basis="PG100k +STPS1H100A0.5mA at125C/100V reference +unverifiedOUTbias25uA allowance; not fulltemperature guaranteed load.",
            source_total_during_fastest_local_ramp_a=r["downstream_bulk_plus_live_peak_a"] + overhead,
            old_controller_input_reserve_a=prev["new_controller_input_current_reserve_in_source_model_a"],
            input_overhead_excess_over_old_controller_reserve_a=overhead
            - prev["new_controller_input_current_reserve_in_source_model_a"],
            digital_enable_current_upper_requirement_a=3.6 / (10000 * 0.99) + 10e-6,
            additional_v2v5_aux_steady_load_a=0,
            powerlimit_typical_equation_over_vds_w=power_nominal,
            powerlimit_testpoint_factor_sensitivity_w=power_sensitivity,
            powerlimit_sensitivity_basis="19/25..31/25 factors from48V/150k testpoint are NOT guaranteed at selectedR/12/19V. Offset/gain bounds unavailable; sensitivity only.",
            guaranteed_powerlimit_at_selected_values_w=None,
            normal_ramp_initial_pass_power_scenario_w=normal_power,
            nominal_powerlimit_would_avoid_normal_ramp_limiting=power_nominal[1] > normal_power,
            sensitivity_lower_power_would_avoid_normal_ramp_limiting=power_sensitivity[0] > normal_power,
            hotshort_energy_screen_ignoring_powerlimit_j=fault_energy_without_powerlimit,
            hotshort_screen_basis="I<=conditional currentlimit upper immediately after breaker recovery, VDS<=normal source upper, duration<=conditional timerupper. Initial breaker/inductive overshoot and railfaults excluded, so not a faultenergy bound.",
            soa=dict(
                device="CSD19536KTT",
                pdf_revision="SLPS540C May2025",
                read_graph_point=dict(
                    vds_v=50,
                    id_dc_a=2,
                    case_c=25,
                    reading_basis="Conservative manual read of red DC curveFigure4-10; graph digitization uncertainty not bounded.",
                ),
                case_requirement_for_comparison_c=100,
                ti_application_derating_factor=(175 - 100) / (175 - 25),
                resulting_conditional_dc_current_a=1.0,
                fault_margin_factor1p3_pass_if_all_preconditions_hold=shunt["current_limit_a"][1] * 1.3 <= 1,
                preconditions=[
                    "Case<=100C throughout startup/hotshort",
                    "VDS<=50V including dynamic transients",
                    "Referenced graph/derating applicable to realdevice andlayout",
                    "Currentlimit/timertransfer valid at12/19V",
                    "Initial circuitbreaker pulse independently safe",
                ],
                actual_case_temperature_bound_c=None,
                physical_or_fault_soa_qualified=False,
            ),
            dv_cap_maximum_voltage_from25c_candidate_input_clamp_plus_gate_v=(38.9 if rail == "P19" else 24.4)
            + 12.6,
            dv_cap_voltage_requirement_v=100,
            dv_cap_exact_part_selected=False,
            all_downstream_bulk_after_limiter_in_draft=True,
            canonical_bulk_rewired=False,
            reverse_current_and_partial_power_qualified=False,
            late_bank_closure_ramp_qualified=False,
        )
    rows["P19"]["unimplemented_faster_comparison_only"] = ramp(
        rows["P19"]["source_voltage_upper_scenario_v"],
        old["rail_scenarios"]["P19"]["local_bulk_initial_tolerance_only_f"],
        old["rail_scenarios"]["P19"]["external_load_plus_native_bleeds_a"],
        1.2e-6,
    )
    docs = {}
    for name, url, path in [
        ("lm5069", TI + "lm5069.pdf", "/private/tmp/afx-lm5069.pdf"),
        ("ti-ramp-guide", "https://www.ti.com/lit/ug/tidues3/tidues3.pdf", "/private/tmp/afx-tidues3.pdf"),
        ("pass-mosfet", TI + "csd19536ktt.pdf", "/private/tmp/afx-csd19536ktt.pdf"),
        ("opto", RELAY, "/private/tmp/afx-tlp170gm.pdf"),
        ("pnp", PNP, "/private/tmp/afx-mmbt5401.pdf"),
        ("ramp-diode", DIODE, "/private/tmp/afx-1n4148w.pdf"),
        ("shunt", SHUNT, "/private/tmp/afx-wsl.pdf"),
    ]:
        docs[name] = dict(url=url, external_pdf_sha256=sha(path), redistributed=False)
    docs["driver"] = dict(
        url=DRIVER,
        external_pdf_sha256=None,
        basis="Primary webPDF parsed Table2pinmap andTable7; directPDFdownload403. No invented document hash.",
    )
    report = dict(
        revision="SC01-draft",
        rail_scenarios=rows,
        shunt=shunt,
        timer=timer,
        primary_documents=docs,
        default_off_interface="Normallyopen TLP170GM connects UVupper branch only when illuminated. BSS138BK10kGS pulldown; localafter-bankrail powersLED throughR9;10kLEDshunt diverts offleakage. Controlrequiresindependent3.0..3.6Vhigh/0..0.1Vlow and bounded unpowered leakage; fulltemp/fault proofopen.",
        startup_order=[
            "Source→retainedB2BhardOFFbank→SC01shunt/Q1→ALLprotectedbulk andloads",
            "Local100nFcontrollerinputbypass is not relocated protected reservoirbulk",
            "Bankclosinglate applies freshVIN toLM5069; cannot have completedrampbeforebankclose in this ordering",
            "Chargedload may backfeed Q1bodydiode intoSENSE/VIN; no safe reverse/partialpower claim",
        ],
        missing_implementations=[
            "Negativecounterpart",
            "Independent loadabsolutevoltagevalid receiver andsystem sequencing",
            "ENABLE3V3 is incompatible with E28J9 2.5V status directly; actual translator/controlinterface not implemented",
            "CanonicalE28/P03rewiring",
            "FilmCdv/CT exactMPN/leakage/tempagingbounds",
            "TLP170GM footprint andalloperatingconnector selection",
            "Wholeunit sourcehotcapacity/transient/combinedheat budgets",
            "Concurrentactivationvalidity andsourcegood waveforms",
            "Chargedload/discharge/reset/rampcapacitorreset healthgating",
            "PCB thermalpath andhotSOAfixture",
        ],
        source_sha256={
            str(p.relative_to(REPO)): sha(p)
            for p in [ROOT / "design.py", ROOT / "analyze.py", planning, ROOT / "sources/e28-components.json"]
        },
        provisional_wholeunit_startup_target_s=5,
        complete_startup_bound_s=None,
        five_second_wholeunit_pass=False,
        controller_table_transfer_to_actual_rails_proven=False,
        physical_tests_performed=0,
        schematic_is_fabrication_release=False,
        pcb_implemented=False,
        whole_unit_implemented=False,
    )
    OUT.mkdir(exist_ok=True)
    (OUT / "analysis.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
