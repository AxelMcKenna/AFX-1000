"""Bounded negative-startup comparison; no schematic, operating PCB or physical pass."""

import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[3]
ADI = "https://www.analog.com/media/en/technical-documentation/data-sheets/"
TI = "https://www.ti.com/lit/ds/symlink/"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def shunt_window(load, ceiling, cb_min=0.045, acl_max=0.055 * 1.38, tolerance=0.04):
    if (
        not all(math.isfinite(x) and x > 0 for x in [load, ceiling, cb_min, acl_max])
        or not 0 <= tolerance < 1
    ):
        raise ValueError("Invalid current/threshold/tolerance inputs")
    lower = acl_max / (ceiling * (1 - tolerance))
    upper = cb_min / (load * (1 + tolerance))
    return dict(
        nominal_min_for_acl_ceiling_ohm=lower,
        nominal_max_for_no_steady_cb_trip_ohm=upper,
        nonempty=lower < upper,
        minimum_acl_ceiling_before_controller_overhead_a=acl_max
        / cb_min
        * load
        * (1 + tolerance)
        / (1 - tolerance),
        shunt_total_tolerance_scenario=tolerance,
        warning="A nonempty interval is only an algebraic screen. Thermal/TCR/lifetime/Kelvin/pulse errors need actual selected resistor bounds; no guarantee from this4% allocation.",
    )


def charge(voltage, capacitance, constant_load, current):
    if not all(math.isfinite(x) and x > 0 for x in [voltage, capacitance, constant_load, current]):
        raise ValueError("Invalid charge inputs")
    if current <= constant_load:
        return dict(can_charge=False, charge_time_s=None, mosfet_pass_energy_j=None)
    t = capacitance * voltage / (current - constant_load)
    return dict(
        can_charge=True,
        charge_time_s=t,
        capacitor_energy_j=0.5 * capacitance * voltage**2,
        constant_load_pass_energy_j=0.5 * constant_load * voltage * t,
        mosfet_pass_energy_j=0.5 * current * voltage * t,
        initial_pass_power_w=voltage * current,
        model="Full declared CONSTANT current load from zero, no load gating. Linear cap charge/current limit; no parasitic, nonlinear controller or source sag model.",
    )


def ltc_timer(voltage, charge_time, rd=1e6):
    if not all(math.isfinite(x) and x > 0 for x in [voltage, charge_time, rd]):
        raise ValueError("Invalid timer inputs")
    # Exact integral for the declared ideal-linear VDS ramp and typical6V clamp:
    # Integral max((VDS-6)/RD,0)dt = t*(Vin-6)^2/(2*RD*Vin).
    integral_drain = charge_time * max(voltage - 6, 0) ** 2 / (2 * rd * voltage)
    q = 230e-6 * charge_time + 8 * integral_drain
    c = q / 4
    return dict(
        typical_base_timer_charge_c=230e-6 * charge_time,
        typical_drain_acceleration_charge_c=8 * integral_drain,
        exact_linear_scenario_min_ct_f=c,
        exact_linear_scenario_initial_delay_s=4 * c / 5.8e-6,
        datasheet_half_max_acceleration_ct_f=charge_time * (230e-6 + 4 * max(voltage - 6, 0) / rd) / 4,
        rd_ohm=rd,
        typical_drain_clamp_v=6,
        guaranteed_fault_window_s=None,
        guaranteed_initial_delay_s=None,
        multiplier_tolerance=None,
        timer_charge_current_bounds_a=None,
        note="All timing/threshold/acceleration rows are typical-only. This integration is a sensitivity, NOT a guaranteed capacitance selection. Datasheet1.5 design multiplier is not a guaranteed error budget.",
    )


def ltc_candidate(voltage, capacitance, load, nominal_shunt, tolerance=0.04):
    lo, hi = nominal_shunt * (1 - tolerance), nominal_shunt * (1 + tolerance)
    acl = [0.045 * 1.05 / hi, 0.055 * 1.38 / lo]
    cb = [0.045 / hi, 0.055 / lo]
    ch = charge(voltage, capacitance, load, acl[0])
    return dict(
        nominal_shunt_ohm=nominal_shunt,
        shunt_interval_ohm=[lo, hi],
        cb_current_table_screen_a=cb,
        acl_conservative_ratio_table_screen_a=acl,
        fcl_threshold_table_screen_a=[0.150 / hi, 0.300 / lo],
        steady_cb_margin_a=cb[0] - load,
        charge=ch,
        timer=ltc_timer(voltage, ch["charge_time_s"]) if ch["can_charge"] else None,
        guaranteed_peak_current_a=None,
        source_hotcapacity_verified=False,
        guaranteed_full_startup_s=None,
        physical_qualified=False,
    )


def native_ss_comparison(voltage, capacitance, load, ceiling, rs=0.180):
    """LTC4252A native exponential SS; every dynamic coefficient here is TYPICAL."""
    if not all(math.isfinite(x) and x > 0 for x in [voltage, capacitance, load, ceiling, rs]):
        raise ValueError("Invalid native SS scenario")
    steady = (0.05 * 1.4 - 0.010) / rs
    amplitude = 0.05 * 1.4 / rs
    if not load < ceiling < steady:
        raise ValueError("No finite typical SS ramp interval for this current window")
    k = math.log((steady - load) / (steady - ceiling))
    charge_per_tau = (steady - load) * (k - (1 - math.exp(-k)))
    tau = capacitance * voltage / charge_per_tau
    tload = tau * math.log(amplitude / (steady - load))
    finish = tload + tau * k
    # Faulted output remains at0V. No circuit-breaker timer until SENSE>VCB.
    cb = 0.050 / rs
    cbtime = tau * math.log(amplitude / (steady - cb))
    fault_charge_integral = steady * (cbtime - tau * math.log(amplitude / steady)) - amplitude * tau * (
        math.exp(-math.log(amplitude / steady)) - math.exp(-cbtime / tau)
    )
    return dict(
        nominal_shunt_ohm=rs,
        initial_constant_load_a=load,
        typical_ss_steady_v=1.4,
        typical_gain_v_per_v=0.05,
        typical_offset_v=0.010,
        typical_rss_ohm=50000,
        typical_tau_required_s=tau,
        minimum_css_typical_coefficients_f=tau / 50000,
        typical_full_load_current_reached_s=tload,
        typical_output_complete_s=finish,
        typical_current_at_completion_a=ceiling,
        typical_cb_activation_into_short_s=cbtime,
        typical_pass_energy_into_short_before_cb_j=voltage * fault_charge_integral,
        typical_initial_delay_with_330nf_s=4 * 330e-9 / 5.8e-6,
        typical_total_with_330nf_initial_s=finish + 4 * 330e-9 / 5.8e-6,
        selected_css_f=None,
        guaranteed_ss_gain_bounds=None,
        guaranteed_ss_current_bounds_a=None,
        guaranteed_ss_rss_bounds_ohm=None,
        guaranteed_ss_offset_bounds_v=None,
        normal_start_current_qualified=False,
        complete_startup_s=None,
        note="This separates normal-start current from larger eventual faultACL, using the actual manufacturer's SS pin instead of drainMillerfeedback. NativeSS avoids large gateC. Nominal CSS arithmetic does not establish a production ramp: RSS,ISS,gain,VOS are typical-only. Do not select or author another circuit from this result alone.",
    )


def main():
    original = ROOT / "sources/bipolar-planning.json"
    ledger = json.loads(original.read_text())
    rails = {}
    for rail, rs in [("N19", 0.560), ("N12", 0.274)]:
        old = ledger["rail_scenarios"][rail]
        cap = old["local_bulk_initial_tolerance_only_f"]
        v = math.sqrt(2 * old["capacitor_charge_energy_j"] / cap)
        live = old["external_load_plus_native_bleeds_a"]
        # Explicit conservative comparison addition: output clamp hot-leak allocation
        # and controller OUT/DRAIN influence are not established guarantees.
        added = 0.00055
        total = live + added
        ceiling = old["provisional_external_current_ceiling_a"]
        rails[rail] = dict(
            voltage_max_from_frozen_ledger_v=v,
            minimum_normal_input_allocation_v=18.9 if rail == "N19" else 11.9,
            local_bulk_plus_initial20pct_f=cap,
            frozen_external_live_plus_bleed_a=live,
            additional_unverified_load_screen_a=added,
            constant_load_screen_a=total,
            provisional_normal_start_ceiling_a=ceiling,
            ceiling_is_user_approved_hard_limit=False,
            ideal_charge_at_ceiling=charge(v, cap, total, ceiling),
            ltc_fixed_shunt_window=shunt_window(total, ceiling),
            ltc_fixed_shunt_window_zero_tolerance=shunt_window(total, ceiling, tolerance=0),
            ltc_app_text_66mv_window=shunt_window(total, ceiling, acl_max=0.066),
            ltc_app_text_66mv_window_zero_tolerance=shunt_window(total, ceiling, acl_max=0.066, tolerance=0),
            ltc_fixed_shunt_candidate=ltc_candidate(v, cap, total, rs),
            ltc_native_ss_180mohm_comparison=native_ss_comparison(v, cap, total, ceiling),
            capacitor_only_energy_j=0.5 * cap * v**2,
            full_downstream_capacitance_bound_f=None,
            load_vs_voltage_bound_verified=False,
        )
    # A bounded N19 LT4250 native-Miller comparison, despite N12 supply rejection.
    n19 = rails["N19"]
    rslo, rshi = 0.430 * 0.96, 0.430 * 1.04
    startup_no_trip_total = 0.8 * 0.040 / rshi
    cap_current = startup_no_trip_total - n19["constant_load_screen_a"]
    required_cd_nom = 60e-6 * n19["local_bulk_plus_initial20pct_f"] / cap_current / 0.9
    cdv, cgs = 3.3e-6, 39e-6
    v = n19["voltage_max_from_frozen_ledger_v"]
    lt4250 = dict(
        local_supply_min_v=18,
        n12_local_supply_supported=False,
        n19_local_supply_margin_at18p9_v=0.9,
        normal_supply_current_max_a=0.005,
        current_threshold_v=[0.040, 0.060],
        normal_gate_current_a=[30e-6, 60e-6],
        fault_timer_typical_s=0.0005,
        guaranteed_fault_timer_s=None,
        pull_down_25c_testpoint_a=[0.024, 0.070],
        guaranteed_hot_hard_off_s=None,
        n19_shunt_nominal_ohm=0.430,
        n19_shunt_interval_ohm=[rslo, rshi],
        currentlimit_screen_a=[0.040 / rshi, 0.060 / rslo],
        native_recommended_margin_start_total_a=startup_no_trip_total,
        minimum_cdv_nominal_for_native_margin_f=required_cd_nom,
        native_miller_trial_cdv_f=cdv,
        native_anti_injection_trial_cgs_f=cgs,
        charge_time_if_used_as_fixed_currentlim=charge(
            v, n19["local_bulk_plus_initial20pct_f"], n19["constant_load_screen_a"], 0.040 / rshi
        ),
        full_external_cap_charge_to10v_at30ua_s=(cgs * 1.1 * 10 + cdv * 1.1 * (v + 10)) / 30e-6,
        anti_injection_min_cgs_normal_25c_f=(v - 2.1) / 2.1 * (cdv * 1.1 + 61e-12),
        anti_injection_min_cgs_at38p9_step_25c_f=(38.9 - 2.1) / 2.1 * (cdv * 1.1 + 61e-12),
        manufacturer_hard_shunt_maximum_found_ohm=None,
        shunt_basis="4250lhfa p9 gives inrush margin .8*40mV/RS - ILOAD. No numeric hardmaximum shunt found; that does not constitute unrestricted manufacturer approval.",
        status="REJECT for a common N19/N12 local-powered solution: N12 out-of-range. N19 native Miller path still has gate-charge/insertion-state/fast-off drawbacks; no validated circuit chosen.",
    )
    sources = {
        "LTC4252A": dict(
            url=ADI + "425212fe.pdf",
            revision="425212fe June2013",
            locations=[
                "p3 full-temperature table: VCB45..55mV,VACL/VCB1.05..1.38,VLKO9..10V,IINmax2mA atVIN=VZ-.3,gate40..80uA",
                "p4 TIMER currents/thresholds/acceleration and sink currents lack guaranteed min/max",
                "p14 VIN shunt regulator,up to30mA within thermal limits,13V external transient clamp",
                "p16 UV reset/re-insertion and TIMER4V/5.8uA,230uA+8IDRN",
                "p18 built-in gate anti-injection; small >=10nF compensation, not giant Miller cap",
                "p19 Eq8 shunt fromVCBmin/ILmax; application textVACL54..66mV differs from conservative p3 ratio-product enclosure",
                "p20 Eq13 approximate timer/inrush;1.5 multiplier is design margin,not bounded spec",
                "p21 input transient clamp and Kelvin sense; p28-29 SS early SOA/timeout caveats",
            ],
            retrieved_via="Official primary web parsed PDF; direct curl timed out, no invented PDF hash",
            local_pdf_sha256=None,
        ),
        "LT4250": dict(
            url=ADI + "4250lhfa.pdf",
            revision="4250lhfa",
            locations=[
                "p3 operating18..80V,currentlimit40..60mV,gate30..60uA;500us only typical",
                "p5 pin functions:UVLO prevents local12V operation",
                "p8 Fig6a native Millerfeedback/anti-injection network,p9 inrush margin and input-step behavior",
            ],
            retrieved_via="Official primary web parsed PDF; no redistributed model/PDF",
            local_pdf_sha256=None,
        ),
        "LM5067": dict(
            url=TI + "lm5067.pdf",
            locations=["RevD p5 recommendedICC>=2mA,p20 RS<=100mOhm,p6-7 tables"],
            local_pdf_sha256=sha("/private/tmp/afx-lm5067.pdf")
            if Path("/private/tmp/afx-lm5067.pdf").exists()
            else None,
        ),
        "CSD19536KTT": dict(
            url=TI + "csd19536ktt.pdf",
            locations=["RevC Table4.1 gateVthmin2.1V at25C/250uA,gatecharge and Crss testpoints;Fig4-10 SOA"],
            local_pdf_sha256=sha("/private/tmp/afx-csd19536ktt.pdf")
            if Path("/private/tmp/afx-csd19536ktt.pdf").exists()
            else None,
        ),
        "TLP170GM": dict(
            url="https://toshiba.semicon-storage.com/info/TLP170GM_datasheet_en_20230522.pdf?did=69102&prodName=TLP170GM",
            locations=[
                "Rev3.0.A p3 DC25C; p4 turnoffmax1ms atIF2mA,VDD20V,RL200Ohm,25C; not a guaranteed hot logic/fault-isolator delay"
            ],
            local_pdf_sha256=sha("/private/tmp/afx-tlp170gm.pdf")
            if Path("/private/tmp/afx-tlp170gm.pdf").exists()
            else None,
        ),
    }
    report = dict(
        revision="NF01-feasibility-only",
        rails=rails,
        lt4250=lt4250,
        primary_sources=sources,
        ltc_ratio_product_acl_enclosure_v=[0.045 * 1.05, 0.055 * 1.38],
        ltc_application_text_acl_interval_v=[0.054, 0.066],
        ltc_numeric_hard_max_shunt_found_ohm=None,
        ltc_shunt_basis="ManufacturerEq8 supports selectingRS fromload; noLM5067<=.1Ohm rule imported. No numeric upper restriction found is NOT unlimited DFM/device approval.",
        lm5067_fixed_limit_dead_end=dict(
            manufacturer_rs_max_ohm=0.1,
            minimum_currentlimit_at_max_legal_rs_a=0.044 / 0.1,
            rs_min_for_150ma_max_limit_ohm=0.056 / 0.150,
            rs_min_for_220ma_max_limit_ohm=0.056 / 0.220,
            larger_shunts_supported=False,
            source="LM5067RevD§9.2.2.2 explicitlyRS<=100mOhm. Separate normal-ramp control needed; do not waive this selection rule.",
        ),
        ltc_180mohm_fault_screen=dict(
            shunt_interval_scenario_ohm=[0.180 * 0.96, 0.180 * 1.04],
            minimum_cb_a=0.045 / (0.180 * 1.04),
            maximum_acl_a=0.055 * 1.38 / (0.180 * 0.96),
            maximum_fcl_threshold_a=0.300 / (0.180 * 0.96),
            controller_actual_peak_current_a=None,
            source_fault_capacity_verified=False,
            note="MinimumCB~240mA exceeds both normal planning ceilings, allowing nativeSS to finish charging beforeCB is reached in the nominal SS calculation. EventualACL~439mA and FCLthreshold~1.736A exceed normal budgets and require a distinct fault/source/SOA proof.",
        ),
        ltc_n12_headroom_screen=dict(
            rin_candidate_ohm=499,
            rin_total_tolerance=0.01,
            assumed_ic_load_a=0.002,
            supply_after_feed_11p9_v=11.9 - 0.002 * 499 * 1.01,
            comparator_vlko_max_v=10,
            input_zener_min_at2ma_v=11.5,
            steady_if_low_zener_at12p071_source_a=(rails["N12"]["voltage_max_from_frozen_ledger_v"] - 11.5)
            / (499 * 0.99),
            input_tvs_25c_catalogue_step_v=24.4,
            if_low_zener_at24p4_step_a=(24.4 - 11.5) / (499 * 0.99),
            min_rin_at_24p4_for30ma_if11p5_zener_ohm=(24.4 - 11.5) / 0.030,
            prescribed_continuous_vin_current_max_a=0.030,
            gate_drive_min10v_test_condition_iin_a=0.002,
            actual_low_voltage_max_supply_current_bound_a=None,
            low_voltage_gate_drive_guarantee_v=None,
            status="Plausible POR headroom, not a guaranteed12V operating/gate-drive supply.2mA current max is specified atVIN=VZ-.3; gate-drive minimum specified atIIN2mA. At highVZ a12Vlocalfeed is unregulated. Obtainvendor confirmation or qualify separate bounded bias supply; no phantomfeed added.",
        ),
        best_next_architecture="LTC4252A-1 using nativeSS and~180mOhm fault shunt on both rails, separating normal-start ceilings from higher faultACL, with no external drainMillerfeedback. Nominal full-live-load ramp is plausible below5s. Need actual lowVin operating/gate guarantees, SS bounds, faulttimer/sink bounds and complete source/SOA/thermal envelope before selectingCSS or drafting another circuit. FixedACL N12 at220mA remains rejected unless source ceiling changes.",
        viable_with_all_current_contracts_verified=False,
        provisional5s_is_hard_user_requirement=False,
        five_second_guarantee_s=None,
        canonical_boards_modified=False,
        new_schematic_authored=False,
        pcb_implemented=False,
        physical_tests_performed=0,
        startup_qualified=False,
        soa_qualified=False,
        source_sha256={
            str(p.relative_to(REPO)): sha(p)
            for p in [original, ROOT / "compare.py", ROOT / "sources/sc02-verification.json"]
        },
    )
    (ROOT / "comparison.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
