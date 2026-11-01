"""Conditional SC02 arithmetic; no unverified interval is a device guarantee."""

import hashlib
import itertools
import json
import math
from pathlib import Path

from .design import DRIVER, MILLER, RELAY, REPO, ROOT, SHUNT, STAGES, TI

OUT = ROOT / "generated"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def shunt_corners():
    r = 0.091
    terms = [0.01, 0.0075, 0.01 + 0.0005 / r, 0.005 + 0.0005 / r]
    low, high = [r * (1 + sign * sum(terms)) for sign in [-1, 1]]
    return dict(
        nominal_ohm=r,
        interval_ohm=[low, high],
        declared_fraction_terms=terms,
        current_limit_a=[0.044 / high, 0.056 / low],
        circuit_breaker_a=[0.070 / high, 0.130 / low],
        currentlimit_shunt_power_w=0.056**2 / low,
        conditions="WSL initial1%,75ppm/K*100K project screen, one loadlife(1%+.5mOhm), one solderheat(.5%+.5mOhm). Not a qualified mission profile. LM5067 table ICC2mA/OUT48V above VEE unless noted.",
        all_in_lifetime_bound_approved=False,
        actual_rail_transfer_verified=False,
    )


def timer_corners(c_nom=470e-9, c_fraction=0.1, leakage=0.1e-6):
    if (
        not all(math.isfinite(v) for v in [c_nom, c_fraction, leakage])
        or c_nom <= 0
        or not 0 <= c_fraction < 1
        or not 0 <= leakage < 0.9e-6
    ):
        raise ValueError("Invalid timer scenario")
    lo, hi = c_nom * (1 - c_fraction), c_nom * (1 + c_fraction)
    return dict(
        capacitance_scenario_f=[lo, hi],
        leakage_scenario_a=leakage,
        insertion_from_zero_s=[lo * 3.76 / (9.5e-6 + leakage), hi * 4.16 / (2.5e-6 - leakage)],
        fault_from_zero_s=[lo * 3.76 / (140e-6 + leakage), hi * 4.16 / (44e-6 - leakage)],
        latched_discharge_4p16_to_0p3_s=hi * (4.16 - 0.3) / (0.9e-6 - leakage),
        guaranteed_insertion_s=None,
        guaranteed_fault_s=None,
        guaranteed_reset_s=None,
        initial_timer_upper_before_each_fault_v=None,
        reset_requirement="LM5067-1 requires TIMER<0.3V and a fresh input/UV enable cycle. Do not issue an arbitrary short reset pulse.",
        conditions="RevD7.5 has44..140uA fault charge,2.5..9.5uA insertion and.9..4.25uA fault-end discharge. Narrative8.3.6 says85uA fault vs table95uAtyp; table used. ICC2mA/OUT48V above VEE. EffectiveC/leakage unselected.",
    )


def dividers(top, ovtop):
    uv, uvdown, ov, ovdown = [], [], [], []
    for rt, rb, threshold, ih, bias, ron in itertools.product(
        [top * 0.997, top * 1.003], [9970, 10030], [2.45, 2.55], [10e-6, 34e-6], [-1e-6, 1e-6], [0, 50]
    ):
        uv.append(threshold * (1 + (rt + ron) / rb) + (ih + bias) * (rt + ron))
        uvdown.append(threshold * (1 + (rt + ron) / rb) + bias * (rt + ron))
    for rt, rb, threshold, ih, bias in itertools.product(
        [ovtop * 0.997, ovtop * 1.003], [9970, 10030], [2.43, 2.57], [10e-6, 34e-6], [-1e-6, 1e-6]
    ):
        ov.append(threshold * (1 + rt / rb) + bias * rt)
        ovdown.append(threshold * (1 + rt / rb) + (bias - ih) * rt)
    return dict(
        uv_magnitude_rising_v=[min(uv), max(uv)],
        uv_magnitude_falling_v=[min(uvdown), max(uvdown)],
        ov_magnitude_rising_v=[min(ov), max(ov)],
        ov_magnitude_falling_v=[min(ovdown), max(ovdown)],
        relay_open_uv_from_1ua_offleak_v=1e-6 * 10030,
        note="Magnitudes relative AGND; internal pin thresholds relativeVEE. UV hysteresis sinks10..34uA while LOW; OV hysteresis sources10..34uA while HIGH. Relay50Ohm/1uA25C only, resistor.3% scenario; not hot/defaultOFF qualification.",
    )


def ramp(voltage, c_load, live, cdv, cgs, rfb, final_gate=10.0):
    if not all(math.isfinite(v) and v > 0 for v in [voltage, c_load, live, cdv, cgs, rfb, final_gate]):
        raise ValueError("Finite positive scenario inputs required")
    cd = [cdv * 0.9, cdv * 1.1]
    cg = [cgs * 0.9, cgs * 1.1]
    slew = [30e-6 / cd[1], 74e-6 / cd[0]]
    output = [voltage / slew[1], voltage / slew[0]]
    # Charge conservation for the EXTERNAL caps, starting OFF at a settled input:
    # Cgs:0 -> Vgs_final; Cdv:-Vin -> +Vgs_final. Not a nonlinear time-domain model.
    full_charge = cg[1] * final_gate + cd[1] * (voltage + final_gate)
    return dict(
        net_gate_current_scenario_a=[30e-6, 74e-6],
        effective_cdv_scenario_f=cd,
        effective_cgs_scenario_f=cg,
        assumed_final_vgs_v=final_gate,
        output_slew_scenario_v_per_s=slew,
        output_only_scenario_s=output,
        downstream_peak_scenario_a=live + c_load * slew[1],
        ideal_capacitor_pass_energy_j=0.5 * c_load * voltage**2,
        ideal_constant_live_pass_energy_slowest_j=0.5 * live * voltage * output[1],
        external_gate_cap_charge_scenario_c=full_charge,
        external_cap_charge_time_at_30ua_s=full_charge / 30e-6,
        zero_start_insertion_plus_capcharge_scenario_s=timer_corners()["insertion_from_zero_s"][1]
        + full_charge / 30e-6,
        full_cap_charge_scenario_within_5s=full_charge / 30e-6 <= 5,
        cgs_only_target_to_2p1_at_1p9ma_s=cg[1] * (final_gate - 2.1) / 1.9e-3,
        cgs_only_target_to_2p1_at_45ma_s=cg[1] * (final_gate - 2.1) / 0.045,
        rfb_cdv_max_s=rfb * 1.01 * cd[1],
        input_step_initial_feedback_current_if_gate_clamped_a=voltage / (rfb * 0.99),
        input_step_cdv_energy_scenario_j=0.5 * cd[1] * voltage**2,
        step_current_is_guaranteed=False,
        anti_injection_cgs_min_at_25c_vth2p1_scenario_f=(voltage - 2.1) / 2.1 * (cd[1] + 61e-12),
        guaranteed_output_slew_v_per_s=None,
        guaranteed_complete_startup_s=None,
        guaranteed_fault_turnoff_s=None,
        cross_controller_network_validated=False,
        notes="32..72uA LM5067 normal table plus +/-2uA unverified allowance =>30..74uA. NOT full-trajectory bounds. LT4250 Fig6a/150us RC rule is cross-controller inference. Cgs/Qgd, variableVth/transconductance, input steps/initialcharge, controller modulation/stability and sink waveform missing. Selected10V finalVGS corresponds to CSD RDS table drive, not an output-ready definition. Full-cap-charge number is conditional time to selected finalVGS, not a load-ready timing guarantee; Cgs-only discharge numbers OMIT Cdv/Miller/loop action and are NOT turnoff bounds.",
    )


def main():
    planning = ROOT / "sources/bipolar-planning.json"
    ledger = json.loads(planning.read_text())
    shunt = shunt_corners()
    rows = {}
    for rail, d in STAGES.items():
        old = ledger["rail_scenarios"][rail]
        vmax = math.sqrt(2 * old["capacitor_charge_energy_j"] / old["local_bulk_initial_tolerance_only_f"])
        # These are comparison allocations only; the exact normal input bounds must be captured at integration.
        vmin = 18.9 if rail == "N19" else 11.9
        pg = vmax / 98000
        live = old["external_load_plus_native_bleeds_a"] + 0.5e-3 + 50e-6
        screen = ramp(vmax, old["local_bulk_initial_tolerance_only_f"], live, d["cdv"], d["cgs"], d["rfb"])
        rinmin, rinmax = d["rin"] * 0.997, d["rin"] * 1.003
        regulated = vmin > 13.65
        iccmin = max(0, (vmin - 13.65) / rinmax) if regulated else None
        iccmax = (vmax - 12.35) / rinmin if regulated else None
        # No claim that a VCC-to-VEE bleed forces any current into the IC.
        unregulated_vcc = vmin - 0.0012 * rinmax if not regulated else None
        input_feed_ceiling_sensitivity = iccmax if regulated else 0.0012
        divider_max = vmax / ((d["uvtop"] + 10000) * 0.997) + vmax / ((d["ovtop"] + 10000) * 0.997)
        source_overhead = input_feed_ceiling_sensitivity + divider_max + pg + 1e-6 + 74e-6
        # Same current flows through VCC feed then VEE; gate allocation may overlap it,
        # intentionally conservative. Digital LED current is NOT charged to negative rail.
        tp = d["rpwr"] / (1.42e5 * 0.091)
        cgs_step = (vmax - 2.1) / 2.1 * (d["cdv"] * 1.1 + 61e-12)
        clamp25 = 38.9 if rail == "N19" else 24.4
        cgs_clamp = (clamp25 - 2.1) / 2.1 * (d["cdv"] * 1.1 + 61e-12)
        rows[rail] = dict(
            retained_bulk_ref=old["protected_bulk_ref"],
            native_bulk=old["native_bulk_value"],
            retained_bulk_plus20pct_f=old["local_bulk_initial_tolerance_only_f"],
            external_and_existing_bleed_a=old["external_load_plus_native_bleeds_a"],
            downstream_added_scenario_a=0.5e-3 + 50e-6,
            input_pg_pullup_bad_state_current_scenario_a=pg,
            output_voltage_max_derived_from_frozen_ledger_v=vmax,
            input_min_comparison_allocation_v=vmin,
            source_input_min_bound_verified=False,
            vcc=dict(
                rin_ohm=d["rin"],
                regulated_at_13p65_possible=regulated,
                regulated_icc_scenario_a=[iccmin, iccmax] if regulated else None,
                recommended_2ma_established_by_comparison=regulated and iccmin >= 0.002,
                unregulated_1p2ma_load_assumed_vcc_min_v=unregulated_vcc,
                unregulated_current_allowance_a=0.0012 if not regulated else None,
                guaranteed_operating_supply_interval_v=None,
                failure=None
                if regulated
                else "FAIL: -12V input below13.65V cannot establish recommended ICC>=2mA/internal-zener test condition via passive RIN. Advertised -9V range is not an approved exception to recommended table. Vendor clarification or different qualified supply/controller architecture required.",
                regulated_ic_heat_scenario_w=13.65 * iccmax if regulated else None,
                normal_rin_heat_scenario_w=(vmax - 12.35) ** 2 / rinmin
                if regulated
                else (0.0012**2 * rinmax),
                thermal_qualified=False,
            ),
            divider=dividers(d["uvtop"], d["ovtop"]),
            ramp=screen,
            external_anti_injection=dict(
                cgs_min_scenario_f=d["cgs"] * 0.9,
                required_at_normal_25c_vth_f=cgs_step,
                comparison_input_step_v=clamp25,
                required_at_catalog_tvs_clamp_and_25c_vth_f=cgs_clamp,
                normal_25c_only_geometry_screen=d["cgs"] * 0.9 >= cgs_step,
                catalog_clamp_25c_only_screen=d["cgs"] * 0.9 >= cgs_clamp,
                hot_vth_lower_bound_v=None,
                full_nonlinear_cgd_upper_bound_f=None,
                insertion_off_qualified=False,
                note="CSD Vthmin2.1V at25C/250uA, Crssmax61pF atVDS50V/1MHz are not full hot/input-step bounds. TVS catalog clamp only25C specified pulse; not system transient bound. Normal screen is not an OFF guarantee.",
            ),
            rpwr_ohm=d["rpwr"],
            typical_selected_power_equation_w=tp,
            testpoint_gain_only_sensitivity_w=[tp * 16.5 / 22, tp * 27.5 / 22],
            guaranteed_actual_selected_powerlimit_w=None,
            normal_initial_pass_power_scenario_w=vmax * screen["downstream_peak_scenario_a"],
            powerlimit_transfer_note="LM5067Eq3 and7.5 testpoint24V/75k, no selected12/19V gain/offset/leakage bound. Conservative DC SOA graph reference alone does not cover added-capacitor turnoff energy.",
            source_overhead_sensitivity_a=source_overhead,
            source_total_fast_output_sensitivity_a=screen["downstream_peak_scenario_a"] + source_overhead,
            additional_v2v5_aux_load_a=0,
            source_current_hotcapacity_verified=False,
            canonical_bulk_rewired=False,
        )
    digital = dict(
        host_voltage_requirement_v=[3.0, 3.6],
        enable_high_requirement_v=[3.0, 3.6],
        enable_low_requirement_v=[0, 0.1],
        e28_j9_2p5v_direct_compatible=False,
        led_resistor_ohm=680,
        led_series_current_max_scenario_a=(3.6 - 1.1) / (680 * 0.99),
        led_min_scenario_a=(3 - 1.4 - 0.065) / (680 * 1.01) - 1.4 / 9900,
        enable_input_max_scenario_a=3.6 / 9900 + 10e-6,
        recommended_tlp_led_typ_a=0.002,
        led_trigger_max_25c_a=0.001,
        negative_local_led_load_a=0,
        additional_v2v5_aux_load_a=0,
        temperature_and_leakage_guarantees_verified=False,
        digital_load_budget_verified=False,
        host_missing_or_enable_highz="10k gate pulldown requests OFF; no guaranteed hot/defaultOFF until driver/relay/input leakage and host power sequencing are bounded.",
        receiver_and_ready_sequencer_implemented=False,
    )
    docs = {}
    for key, name, url in [
        ("LM5067", "afx-lm5067.pdf", TI + "lm5067.pdf"),
        ("CSD19536KTT", "afx-csd19536ktt.pdf", TI + "csd19536ktt.pdf"),
        ("WSL", "afx-wsl.pdf", SHUNT),
        ("TLP170GM", "afx-tlp170gm.pdf", RELAY),
    ]:
        p = Path("/private/tmp") / name
        docs[key] = dict(url=url, local_sha256=sha(p) if p.exists() else None, redistributed=False)
    docs["LT4250"] = dict(
        url=MILLER,
        local_sha256=None,
        fetched_via_web=True,
        reference="4250lhfa p8Fig6a, APPLICATIONS INFORMATION. ADI PDF direct curl failed; parsed official web source inspected. Exact circuit-image verification remains open; SC02 RC is declared an engineering topology, not a copy/certification.",
        redistributed=False,
    )
    docs["BSS138BK"] = dict(url=DRIVER, local_sha256=None, fetched_via_web=True)
    report = dict(
        revision="SC02-negative-native-draft",
        rail_scenarios=rows,
        shunt=shunt,
        timer=timer_corners(),
        digital_interface=digital,
        primary_sources=docs,
        source_sha256={
            str(p.relative_to(REPO)): sha(p)
            for p in [planning, ROOT / "design.py", ROOT / "analyze.py", ROOT / "sources/e28-components.json"]
        },
        charged_load="NFET body diode SENSE->PROTECTED can discharge a charged negative load into a missing/collapsed input. InitialCdv/Cgs/CTIMER/output states and external crossrail injection unbounded; no reverse blocking or verified precharge/reset detector.",
        late_b2b_closure="All retained bulk after this new limiter, so closing a bank into an empty local cap cannot bypass this stage. All downstream connections/caps, reset/power-loss paths still require actual integration; canonical bank/PCB untouched.",
        pg_health="PG_RAW negative VEE..AGND and high withVCC-VEE<2V. Not logic-safe and not independent output-valid. Missing receiver and absolute rail/VCC checks.",
        soa=dict(
            graph_reference="CSDRevC Fig4-10 read conservatively at50V DC=2A, Tc25C; TI case-temperature derating to100C gives1A conditional reference, not actual cooling proof.",
            dc_current_reference_at50v_case100c_a=1.0,
            currentlimit_margin_1p3_times_upper_a=1.3 * shunt["current_limit_a"][1],
            circuitbreaker_upper_a=shunt["circuit_breaker_a"][1],
            cb_upper_exceeds_1a_reference=shunt["circuit_breaker_a"][1] > 1,
            case_temperature_bound_c=None,
            full_fault_waveform_verified=False,
            qualified=False,
            limitation="No pass: externalCgs/Cdv delays actualFETturnoff; CB pulse/currentpeak, source overshoot, powerlimit transfer/reset states and junction/case cooling are unbounded. Graph/DC screen cannot replace waveform SOA.",
        ),
        complete_startup_bound_s=None,
        five_second_wholeunit_pass=False,
        whole_unit_implemented=False,
        guaranteed_ramp_network=False,
        soa_qualified=False,
        physical_tests_performed=0,
        fabrication_released=False,
        pcb_implemented=False,
        canonical_boards_modified=False,
        bounds_status="Calculations are declared sensitivities, including a failing -12V recommended-supply condition. Neither nativeERC nor normal-ramp arithmetic establishes hardware validity.",
    )
    OUT.mkdir(exist_ok=True)
    (OUT / "analysis.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
