#!/usr/bin/env python3
"""E04 audio architecture screen: gain, noise power and supply limits.

Datasheet typical figures and explicit assumptions are NOT measured unit
performance. An allocation is a requirement for an unfinished circuit, not a
prediction that it passes. Rejecting a draft does not lower the product target.
"""

import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "generated"
K = 1.380649e-23
BANDWIDTH = 20000 - 20
TEMPERATURE_K = 298.15
HEADROOM_DB = 20
MODES = [("send_return", 10 ** (-10 / 20), 102), ("master", 0.775 * 10 ** (4 / 20), 98)]

# Same-weighting, independent-noise screening. Do not combine an unweighted
# figure with an A-weighted figure, or average dB directly.
PROFILES = [
    dict(
        name="TAC5242_single_ended_3V3",
        adc_db=110,
        dac_db=111,
        source="https://www.ti.com/lit/ds/symlink/tac5242.pdf",
        condition="3.3V, single-ended; not a claim about Seed3 hardware straps",
    ),
    dict(
        name="TAC5242_differential_3V3",
        adc_db=119,
        dac_db=120,
        source="https://www.ti.com/lit/ds/symlink/tac5242.pdf",
        condition="3.3V, AC-coupled differential; optimistic chip-level screen",
    ),
    dict(
        name="ES9292PRO_AVCCH_3V3",
        adc_db=128,
        dac_db=128.5,
        source="https://www.esstech.com/wp-content/uploads/2026/08/ES9292_DS_v0.1.pdf",
        condition="Internal 2.85V mode; 48kHz EVM typical DNR, A-weighted",
    ),
    dict(
        name="ES9292PRO_AVCCH_4V5",
        adc_db=128.5,
        dac_db=130,
        source="https://www.esstech.com/wp-content/uploads/2026/08/ES9292_DS_v0.1.pdf",
        condition="Internal 3.3V mode; 48kHz EVM typical DNR, A-weighted",
    ),
]


def power_ratio(db):
    return 10 ** (-db / 10)


def combined_db(*values):
    return -10 * math.log10(sum(power_ratio(v) for v in values))


def parallel(a, b):
    return a * b / (a + b)


def rms_noise(resistance):
    return math.sqrt(4 * K * TEMPERATURE_K * BANDWIDTH * resistance)


def noise_screen():
    profiles = []
    for profile in PROFILES:
        combined = combined_db(profile["adc_db"], profile["dac_db"])
        rows = []
        for mode, nominal, target in MODES:
            full_scale = nominal * 10 ** (HEADROOM_DB / 20)
            converter_noise = full_scale * 10 ** (-combined / 20)
            maximum_noise = nominal * 10 ** (-target / 20)
            remaining_power = maximum_noise**2 - converter_noise**2
            rows.append(
                dict(
                    mode=mode,
                    target_snr_db=target,
                    nominal_rms_v=nominal,
                    headroom_db=HEADROOM_DB,
                    converter_only_snr_at_nominal_db=combined - HEADROOM_DB,
                    converter_equivalent_output_noise_uv=converter_noise * 1e6,
                    maximum_total_output_noise_uv=maximum_noise * 1e6,
                    remaining_analog_noise_budget_uv=math.sqrt(remaining_power) * 1e6
                    if remaining_power > 0
                    else None,
                    converter_only_clears_minimum=remaining_power > 0,
                    maximum_headroom_before_analog_noise_db=combined - target,
                )
            )
        profiles.append(
            dict(
                **profile,
                combined_dynamic_range_db=combined,
                modes=rows,
                final_audio_performance_verified=False,
            )
        )
    return profiles


def old_network_noise():
    rows = []
    for mode, nominal, target in MODES:
        rf_in = 10000 if mode == "send_return" else parallel(10000, 3480)
        rf_out = parallel(127000, 43200) if mode == "send_return" else 127000
        output_gain = rf_out / 10000
        load_factor = 10000 / 10100
        # Ideal zero-noise op-amps; both resistor noise terms are independent.
        # The input-network noise is propagated through the output stage.
        input_noise = rms_noise(rf_in * (1 + rf_in / 32400)) * output_gain * load_factor
        output_noise = rms_noise(rf_out * (1 + rf_out / 10000)) * load_factor
        series_noise = rms_noise(100) * load_factor
        total = math.sqrt(input_noise**2 + output_noise**2 + series_noise**2)
        snr = 20 * math.log10(nominal / total)
        rows.append(
            dict(
                mode=mode,
                input_network_output_referred_uv=input_noise * 1e6,
                output_feedback_network_uv=output_noise * 1e6,
                series_resistor_uv=series_noise * 1e6,
                resistor_only_output_noise_uv=total * 1e6,
                resistor_only_snr_db=snr,
                target_snr_db=target,
                clears_target_before_other_noise=snr >= target,
            )
        )
    return dict(
        status="rejected for reference-performance path",
        modes=rows,
        assumptions="Ideal flat stages, 20Hz-20kHz rectangular noise bandwidth, 25C, unity wanted signal",
        excluded=[
            "amplifier noise and 1/f noise",
            "converter noise",
            "source/load and supply noise",
            "filter transfer functions and frequency-dependent gain",
            "resistor excess noise and tolerances",
        ],
        interpretation="Lower-bound circuit noise screen, not an A-weighted S/N measurement",
    )


def amplifier_and_gain_screen():
    # A 2Vrms SINGLE-ENDED signal after a differential receiver is the proposed
    # output-stage interface. It is not the direct differential codec pin pair.
    rows = []
    for mode, nominal, _ in MODES:
        feedback = 604 if mode == "send_return" else 5110 + 90.9
        gain = 1 + feedback / 1000
        load_factor = 10000 / 10100
        full_scale = nominal * 10 ** (HEADROOM_DB / 20)
        output_rms = 2 * gain * load_factor
        load = parallel(1000 + feedback, 10100)
        rows.append(
            dict(
                mode=mode,
                post_receiver_interface_rms_v=2,
                topology="noninverting output driver",
                ground_resistor_ohm=1000,
                feedback_resistor_ohm=feedback,
                feedback_parts_ohm=[604] if mode == "send_return" else [5110, 90.9],
                proposed_resistor_tolerance=0.001,
                output_series_ohm=100,
                minimum_combined_external_load_ohm=10000,
                closed_loop_gain=gain,
                effective_amplifier_resistive_load_ohm=load,
                target_output_full_scale_rms_v=full_scale,
                calculated_output_full_scale_rms_v=output_rms,
                nominal_gain_error_db=20 * math.log10(output_rms / full_scale),
                amplifier_peak_at_target_v=full_scale * math.sqrt(2) / load_factor,
            )
        )
    master = rows[1]
    rail = 19
    tolerance = 0.01
    minimum_rail = rail * (1 - tolerance)
    maximum_total_supply = 2 * rail * (1 + tolerance)
    reserve = 0.3
    available = minimum_rail - reserve
    input_buffer_white_noise = math.hypot(rms_noise(2200), 7e-9 * math.sqrt(BANDWIDTH))
    return dict(
        output_interfaces=rows,
        master_driver_candidate="OPA2992D",
        consumer_driver_candidate="OPA1612AID",
        input_buffer_candidate="OPA2992D",
        analog_high_rails=dict(
            nominal_bipolar_v=rail,
            proposed_total_regulation_tolerance=tolerance,
            minimum_rail_magnitude_v=minimum_rail,
            maximum_total_supply_v=maximum_total_supply,
            opa2992_recommended_total_supply_max_v=40,
            supply_within_recommended_range=maximum_total_supply <= 40,
            assumed_output_headroom_v=reserve,
            headroom_source_condition="OPA2992 EC table at 40V supply, 2kOhm load; reuse at 38V is a screening assumption",
            master_effective_load_above_2k=master["effective_amplifier_resistive_load_ohm"] >= 2000,
            screened_available_peak_v=available,
            required_master_peak_v=master["amplifier_peak_at_target_v"],
            screened_peak_margin_v=available - master["amplifier_peak_at_target_v"],
            candidate_clears_voltage_screen=available >= master["amplifier_peak_at_target_v"],
            bench_verified=False,
        ),
        input_buffer=dict(
            series_resistor_ohm=2200,
            assumed_flat_noise_density_nv_rt_hz=7,
            white_noise_estimate_uv=input_buffer_white_noise * 1e6,
            status="Illustrative buffer screen; omits source, bias, low-frequency noise and protection details",
        ),
        limits=[
            "No circuit/PCB or regulator selection is established by this screen",
            "Master/send-return would select separate output drivers; do not join their outputs",
            "Separate stereo input gain selection is still required",
            "E01 feedback-shunt values must not be copied into this proposed topology",
            "Loaded converter full scale, analog filters and calibration remain unresolved",
        ],
    )


def calculate():
    profiles = noise_screen()
    # Numerical invariants independent of component choices guard against
    # adding dB, losing the 20dB nominal-level penalty, or using voltage in a
    # noise-power subtraction. These are not hardware-performance tests.
    assert math.isclose(combined_db(120, 120), 120 - 10 * math.log10(2), abs_tol=1e-12)
    assert combined_db(119, 120) < 119
    assert all(not row["converter_only_clears_minimum"] for row in profiles[1]["modes"])
    assert all(row["converter_only_clears_minimum"] for row in profiles[3]["modes"])
    old = old_network_noise()
    assert all(not row["clears_target_before_other_noise"] for row in old["modes"])
    amps = amplifier_and_gain_screen()
    assert amps["analog_high_rails"]["supply_within_recommended_range"]
    assert amps["analog_high_rails"]["candidate_clears_voltage_screen"]
    return dict(
        revision="E04",
        status="architecture screen; no complete analog circuit or measured audio result",
        headroom_both_modes_project_target_db=HEADROOM_DB,
        reference_noise_comparison_assumption="Nominal line signal, unity through gain, same weighting/bandwidth; reference measurement conditions still require verification",
        equal_adc_dac_dynamic_range_needed_before_analog_noise_db={
            mode: target + HEADROOM_DB + 10 * math.log10(2) for mode, _, target in MODES
        },
        converter_profiles=profiles,
        rejected_e01_resistor_network=old,
        prospective_analog_interface=amps,
        decisions=[
            "Keep Seed3 with onboard codec for firmware/control bring-up only",
            "Onboard converter is not approved for reference-performance hardware",
            "Evaluate ES9292QPRO, external differential converter board and new board adapter",
            "Use OPA2992 and regulated +/-19V as high-voltage candidates, not an approved power BOM",
            "Preserve the existing minimum targets; preferred 110dB nominal S/N is not met by these converter screens",
        ],
        unresolved=[
            "Actual Seed3 codec mode/analog transfer and measured performance",
            "ESS 260Ohm input-impedance interpretation and loaded filter/gain network",
            "ESS 390Ohm DAC source impedance and receiver loading",
            "Converter procurement, clock choice, configuration and board adapter",
            "Protection, coupling, power/ground, filter, noise integration and tolerance analysis",
            "High-voltage input buffer full-scale input-pair crossover distortion",
            "Complete native analog/power schematic and routed PCB",
            "Actual unit noise, THD, headroom, response, latency, transients and thermal tests",
        ],
    )


def main():
    report = calculate()
    report["generator_sha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    report["primary_source_record_sha256"] = hashlib.sha256(
        (ROOT / "audio-sources.json").read_bytes()
    ).hexdigest()
    OUT.mkdir(exist_ok=True)
    (OUT / "audio-budget.json").write_text(json.dumps(report, indent=2) + "\n")
    for profile in report["converter_profiles"]:
        print(
            f"{profile['name']}: converter-only nominal S/N {profile['combined_dynamic_range_db'] - HEADROOM_DB:.2f} dB"
        )
    for row in report["rejected_e01_resistor_network"]["modes"]:
        print(
            f"E01 {row['mode']}: resistor-only noise {row['resistor_only_output_noise_uv']:.2f} uVrms, unweighted S/N {row['resistor_only_snr_db']:.2f} dB"
        )
    print("E04 written; voltage/noise screens do not establish a finished analog circuit.")


if __name__ == "__main__":
    main()
