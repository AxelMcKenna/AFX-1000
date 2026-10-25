"""Staged higher-headroom external-converter bench requirements."""

import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
PROFILE = "higher-headroom standalone external-converter"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def metric(unit, low=None, high=None, *, expected=None, status="project_target"):
    return dict(unit=unit, minimum=low, maximum=high, expected=expected, limit_status=status)


def cases(repo=REPO):
    power = json.loads((repo / "hardware/electronics/power_supply/integration.json").read_text())
    disconnect = json.loads(
        (repo / "hardware/electronics/rail_disconnect/generated/electrical-screens.json").read_text()
    )
    result = []

    def add(identifier, stage, title, readings, conditions, instruments, procedure, *, isolated=False):
        result.append(
            dict(
                id=identifier,
                stage=stage,
                title=title,
                metrics=readings,
                conditions=conditions,
                instrument_kinds=instruments,
                requires_completed_system_design=not isolated,
                prerequisite="Independent source-bound fixture and isolated-board release"
                if isolated
                else "Completed/reviewed system design and staged assembly release",
                procedure=procedure,
            )
        )

    add(
        "input_protection",
        1,
        "Isolated E23 protected input under approved source/load conditions",
        {
            "minimum_v": metric("V", 10.5, 13.2),
            "maximum_v": metric("V", 10.5, 13.2),
            "no_uncommanded_output": metric("bool", expected=True),
        },
        ["normal_input_no_load", "normal_input_representative_load"],
        ["dmm", "oscilloscope", "load"],
        "Review polarity, input ratings, selected fuse/source and bounded fault fixture first. Test E23 alone into a dummy load. Record actual input/output/current; these bounds are E14's downstream normal-input allocation, not proof of E23 current-limit/SOA protection.",
        isolated=True,
    )
    for row in disconnect["normal_drop"]:
        name = row["name"]
        low, high = power["normal_targets_v"][name]
        for boundary, stage in [("source", 2), ("protected_star", 3)]:
            add(
                f"{boundary}_{name}",
                stage,
                f"{name} signed DC at {boundary}",
                {"minimum_v": metric("V", low, high), "maximum_v": metric("V", low, high)},
                ["no_load", "half_allocated_load", "maximum_allocated_load"],
                ["dmm", "oscilloscope", "load"],
                f"Use the selected hardware variant and local reference return. Sweep the three load conditions up to the E17 allocation {row['maximum_current_screen_a']} A. Source limits are a necessary design-target screen; protected-star measurements do not qualify outgoing load-harness voltage. Record shared-return/cross-domain loading and temperature. Negative rails are signed, never absolute-valued.",
                isolated=boundary == "source",
            )

    def unknown(unit):
        return metric(unit, status="unqualified")

    def yes():
        return metric("bool", expected=True)

    def zero():
        return metric("count", 0, 0)

    add(
        "input_faults",
        3,
        "Input interruption/reversal/current-limit and fault energy",
        {"protected_output_safe": yes(), "fault_current_a": unknown("A"), "device_peak_c": unknown("degC")},
        ["interruption", "approved_reverse_fixture", "approved_overcurrent_fixture"],
        ["oscilloscope", "current_probe", "temperature"],
        "Inject only a separately reviewed, current/energy-limited fixture. Capture input, eFuse output/current and relevant temperatures. Programming-error allocations are not an established protection envelope.",
    )
    add(
        "ripple_load_steps",
        3,
        "Six-rail ripple and load-step response",
        {
            "digital_absolute_ripple_v": metric("V", 0, 0.010, status="design_allocation"),
            "analog_peak_excursion_v": unknown("V"),
            "settling_us": unknown("us"),
            "no_sustained_oscillation": yes(),
        },
        ["all_rails_idle", "all_rails_allocated_load", "cross_domain_load_step"],
        ["oscilloscope", "load"],
        "Capture every source/protected rail and return movement with probe bandwidth/connection documented. The digital 10 mV excursion is an E17 allocation; analog dynamic and settling limits remain unqualified.",
    )
    add(
        "startup",
        3,
        "All-rail start, ramp, shutdown and quick replug",
        {"dry_until_qualified": yes(), "startup_ms": unknown("ms"), "peak_inrush_a": unknown("A")},
        ["cold_start", "slow_ramp", "shutdown", "quick_replug"],
        ["oscilloscope", "current_probe"],
        "Capture input/current, six source and protected rails, reference, gates, ready/permit and relay contacts. Repeat across an approved ramp/temperature matrix. An energy-derived minimum time is not a startup upper bound.",
    )
    add(
        "late_gate_closure",
        3,
        "Close E25 onto discharged protected bulk after the source is running",
        {
            "no_unsafe_permit": yes(),
            "peak_inrush_a": unknown("A"),
            "peak_overshoot_v": unknown("V"),
            "settling_us": unknown("us"),
        },
        ["fully_discharged", "partially_charged", "restart_after_fault"],
        ["oscilloscope", "current_probe", "load"],
        "Use a reviewed dummy-load fixture and selected capacitor/ESR inventory. A source soft-start does not limit a later disconnect closure. P01's direct-output capacitance recommendation does not validate the connected millifarad network.",
    )
    add(
        "brownout",
        4,
        "Rail/reference/logic brownout and fresh rearm",
        {"dry_on_fault": yes(), "fresh_permit_required": yes(), "fault_to_dry_us": unknown("us")},
        ["each_source_rail", "aux_reference", "logic_3v3", "rapid_recovery"],
        ["oscilloscope", "current_probe"],
        "Remove one domain at a time using an approved isolation fixture; hold MCU permit high through the event. Observe gates, latch, coil current, actual contact continuity and audio. Do not infer contact state from latch Q.",
    )
    for row in disconnect["rail_thresholds"]:
        name = row["name"]
        add(
            "disconnect_fault_" + name,
            4,
            f"{name} loaded overvoltage/interruption behavior",
            {
                "protected_absolute_peak_v": metric(
                    "V", 0, row["hard_limit_screen_v"], status="design_allocation"
                ),
                "fault_to_open_us": unknown("us"),
                "all_rails_disable": yes(),
            },
            ["minimum_load", "maximum_allocated_load", "approved_hot_condition"],
            ["oscilloscope", "current_probe", "load"],
            "Record source threshold, protected voltage, all gate-source voltages and fault current with the reviewed energy-limited fixture. The old 125 us interruption term is an unproved allocation, not a guaranteed full-device or fault-to-dry limit.",
        )
    add(
        "gate_banks",
        4,
        "Opposing MOSFET banks, leakage and power-domain transitions",
        {
            "banks_disable_on_fault": yes(),
            "no_unintended_backfeed": yes(),
            "turnoff_us": unknown("us"),
            "hot_vgs_v": unknown("V"),
        },
        ["cold", "approved_hot_condition", "asymmetric_power_loss"],
        ["oscilloscope", "current_probe", "temperature"],
        "Observe every gate relative to its own common-source node, including the two parallel digital devices on each side. Measure current sharing and residual conduction. Datasheet timing at a different gate load is not an acceptance limit here.",
    )
    add(
        "manual_bypass",
        4,
        "Manual contacts, gain change and independent relay qualification",
        {
            "dry_on_manual_bypass": yes(),
            "fresh_permit_after_fault": yes(),
            "contact_bounce_ms": unknown("ms"),
            "audio_click_peak_v": unknown("V"),
        },
        ["manual_press_release", "both_gain_edges", "switch_pole_skew"],
        ["oscilloscope", "audio_analyzer"],
        "Measure actual wet/dry and input contact continuity independently of latch Q. Exercise manual bypass and mode contacts; capture coil/TVS, gain request, readiness, permit and audio. E11 contains K1/K2; its optional J4 must not add duplicate coils.",
    )
    add(
        "watchdog",
        4,
        "Real audio and foreground stalls, frozen heartbeat and permit",
        {"dry_on_stall": yes(), "no_false_rearm": yes(), "fault_to_dry_us": unknown("us")},
        [
            "audio_isr_stopped",
            "foreground_stopped",
            "heartbeat_frozen_high",
            "heartbeat_frozen_low",
            "permit_frozen_high",
        ],
        ["oscilloscope", "debug_trace"],
        "Use a source-hashed fault-injection firmware image; stop each execution path independently. Pulling a GPIO manually is not a processor-stall test. Record real contacts and remaining signal behavior across watchdog phases.",
    )
    add(
        "front_controls",
        5,
        "All controls, touch/angle sensors and bus failure behavior",
        {
            "wrong_control_count": zero(),
            "stuck_control_count": zero(),
            "safe_on_bus_fault": yes(),
            "scan_latency_us": unknown("us"),
        },
        [
            "32_contact_functions",
            "10_pots_endpoints_centers",
            "touch_angle_full_travel",
            "i2c_disconnect_chatter",
        ],
        ["logic_analyzer", "debug_trace"],
        "Walk the 320-pair logical map against purchased terminal assignments. Exercise every contact, selector endpoint, pot, touch region and full release stroke; disconnect each bus/sensor and verify fault policy. Physical switch pin numbering is not established by logical labels.",
    )
    add(
        "led_display",
        5,
        "All 96 sinks, emitter anodes and partial-power/latch behavior",
        {"wrong_channel_count": zero(), "safe_partial_power": yes(), "peak_supply_a": unknown("A")},
        ["walking_96_channels", "maximum_selected_pattern", "partial_power_restore"],
        ["logic_analyzer", "current_probe", "oscilloscope"],
        "Use the selected 2.54-to-1.27 mm adapter and reviewed common-anode assignments. Verify scan order, brightness/current, blank/latch edges and restore behavior. Schematic sink channels do not complete a physical emitter board.",
    )
    add(
        "sd_boot",
        5,
        "Real-card startup, malformed files, removal and fallback",
        {
            "safe_factory_fallback": yes(),
            "no_partial_asset_commit": yes(),
            "no_filesystem_after_audio_start": yes(),
            "boot_elapsed_ms": unknown("ms"),
            "peak_card_current_a": unknown("A"),
        },
        [
            "missing_card",
            "valid_card",
            "malformed_assets",
            "card_removed_during_read",
            "slow_or_faulting_card",
            "allocation_refusal",
        ],
        ["oscilloscope", "logic_analyzer", "debug_trace", "current_probe"],
        "Capture J12 power/inrush, SD lines, file-result diagnostics, heartbeat/converter/permit and elapsed time. The software checks an 8 s inter-operation budget; blocking SDK calls may exceed it. Do not use 8 s as a hard test limit or qualify current from a host file test.",
    )
    add(
        "sd_dma_cache",
        5,
        "SDMMC DMA/cache and SRAM behavior on the real MCU",
        {"corrupt_read_count": zero(), "memory_guard_failures": zero(), "dma_region_correct": yes()},
        ["cold_cache", "repeated_fragmented_reads", "card_errors"],
        ["debug_trace", "logic_analyzer"],
        "Bind captures to the actual ELF and selected SDK; inspect AXI DMA addresses/cache maintenance, guard data and checksums across repeated/error reads. ELF addresses alone do not demonstrate live DMA/cache correctness.",
    )
    add(
        "audio_callback",
        5,
        "Physical callback deadline and no filesystem/allocation in audio",
        {
            "callback_allocations": zero(),
            "callback_filesystem_calls": zero(),
            "deadline_misses": zero(),
            "maximum_callback_us": metric("us", 0, 2400, status="firmware_trip_threshold"),
        },
        ["neutral", "effect_control_stress", "sensor_faults", "after_sd_boot"],
        ["oscilloscope", "debug_trace"],
        "Use calibrated timing capture and source-hashed instrumentation around the real 48 kHz/128-frame callback. Include interrupt/control load. The firmware trips above 2400 us; passing this test does not establish end-to-end latency.",
    )
    add(
        "analog_gain",
        6,
        "Full stereo gain calibration and mode transitions",
        {
            "gain_error_db": unknown("dB"),
            "channel_mismatch_db": unknown("dB"),
            "no_clipping_at_rated_level": yes(),
        },
        ["master_left_right", "send_return_left_right", "mode_transition"],
        ["audio_analyzer", "oscilloscope", "dmm"],
        "Calibrate the complete analog chain, not an isolated software gain. Record source/output level conventions, load, trims, neutral DSP and bypass comparisons. Approved trim range/gain-error and transition limits are still needed.",
    )
    add(
        "audio_quality",
        6,
        "Noise/distortion/frequency response against declared project targets",
        {
            "snr_db": metric("dB", 98),
            "thd_percent": metric("percent", 0, 0.005),
            "response_error_db": unknown("dB"),
        },
        ["master", "send_return"],
        ["audio_analyzer"],
        "Record 20 Hz-20 kHz sweep, noise, distortion, residual source/analyzer floor, weighting, bandwidth, reference level and load. Master SNR target is98 dB; Send/Return target is102 dB (a case-specific check enforces it). Frequency-response tolerance and the final comparison method remain unqualified; do not substitute THD+N for a THD target silently.",
    )
    add(
        "headroom_impedance",
        6,
        "Analog headroom and interface loading",
        {
            "headroom_db": metric("dB", 20),
            "input_impedance_ohm": metric("ohm", 22000),
            "output_impedance_ohm": metric("ohm", 0, 1000),
        },
        ["master", "send_return"],
        ["audio_analyzer", "oscilloscope", "dmm"],
        "Use a reviewed overload/protection fixture and declared clipping criterion. Record reference level, frequency and10k output load. These are project interface targets; raw ADC full-scale/bias stability still needs independent qualification.",
    )
    add(
        "audio_latency",
        6,
        "Stereo round-trip latency, crosstalk and effects fidelity",
        {
            "latency_ms": unknown("ms"),
            "crosstalk_db": unknown("dB"),
            "reference_comparison_completed": metric("bool", expected=True),
        },
        ["master", "send_return", "effect_reference_corpus"],
        ["audio_analyzer", "oscilloscope"],
        "Capture dry and processed stereo impulses/sweeps at declared gain/control positions, including converter and bypass latency. Reference matching and acceptable latency/crosstalk tolerances are not established by host tests.",
    )
    add(
        "thermal",
        7,
        "Enclosed full-load thermal behavior and regulator stability",
        {"maximum_hotspot_c": unknown("degC"), "thermal_shutdown_count": zero(), "stable_all_rails": yes()},
        ["idle", "all_selected_loads", "approved_warm_ambient"],
        ["temperature", "oscilloscope", "current_probe"],
        "Record ambient, case/component hotspots, estimated junction temperatures and actual stackup/airflow. For baseline digital-source accuracy the0..85 C junction allocation matters; P01 has a different source and needs its own thermal review. Do not treat an absolute maximum or the CAD vent gap as a thermal qualification.",
    )
    add(
        "emi",
        7,
        "Conducted/radiated emissions and audio coupling characterization",
        {"worst_spur_level": unknown("declared_unit"), "no_observed_functional_upset": yes()},
        ["clocks_leds_active", "sd_boot", "power_load_steps"],
        ["spectrum_analyzer", "oscilloscope"],
        "Document probe/antenna/coupler geometry, bandwidth, detector and environment. Applicable standard, limits and compliance setup have not been selected; this is characterization, not an EMI-compliance pass.",
    )
    add(
        "soak",
        7,
        "Two-hour powered standalone audio/control session",
        {
            "duration_s": metric("s", 7200),
            "sustained_dropout_count": zero(),
            "uncommanded_rearm_count": zero(),
            "post_test_fault_policy_passes": yes(),
        },
        ["continuous_session"],
        ["audio_analyzer", "debug_trace", "temperature"],
        "After the earlier stages pass, exercise effects/controls and completed storage behavior in the actual enclosure. Retain continuous recordings/logs and warm repeat-fault captures. This standalone test does not claim a rekordbox routing soak.",
    )
    for case in result:
        case["requires_case_ids"] = (
            [earlier["id"] for earlier in result if earlier["stage"] < case["stage"]]
            if case["requires_completed_system_design"]
            else []
        )
    return result


def build_plan(repo=REPO, *, source_base_commit=None):
    names = [
        "hardware/electronics/power_supply/integration.json",
        "hardware/electronics/power_supply/routing/generated/verification.json",
        "hardware/electronics/rail_disconnect/placement/generated/verification.json",
        "hardware/electronics/rail_disconnect/generated/electrical-screens.json",
        "hardware/electronics/rail_monitor/generated/electrical-screens.json",
        "hardware/electronics/power_distribution/generated/analysis.json",
        "hardware/firmware/external-profile.json",
        "hardware/firmware/main.cpp",
        "hardware/firmware/BootCard.cpp",
        "hardware/firmware/StorageMemory.ld",
        "hardware/firmware/STORAGE.md",
        "hardware/validation/standalone-storage/verification.json",
        "hardware/wiring/generated/system-interconnect.json",
        "docs/specifications.md",
        "hardware/qualification/spec.py",
        "hardware/qualification/check.py",
        "hardware/qualification/generate.py",
        "hardware/qualification/README.md",
        "hardware/qualification/__init__.py",
        "hardware/qualification/verify.py",
    ]
    route = repo / "hardware/electronics/rail_disconnect/routing/generated/verification.json"
    if route.exists():
        names.append(str(route.relative_to(repo)))
        open_count = json.loads(route.read_text())["native_open_connections"]
    else:
        open_count = 365
    p01 = json.loads((repo / names[5]).read_text())
    wiring = json.loads((repo / "hardware/wiring/generated/system-interconnect.json").read_text())
    holds = dict(
        e25_route_incomplete=f"E25 has {open_count} native open connections" if open_count else None,
        source_redesign_not_implemented="P01 requires new schematic/layout and renewed qualification"
        if not p01["native_schematic_implemented"] or not p01["native_pcb_routed"]
        else None,
        downstream_distribution_open="P01 DC budget ends at E25 output star; outgoing contacts/fanouts remain open"
        if not p01["outgoing_load_harness_voltage_budget_closed"]
        else None,
        large_capacitance_stability_open="TPS62903 direct50uF recommendation versus connected5.88mF requires a new loop/inrush study",
        peripheral_and_fanout_assemblies_open=f"{wiring['remaining_required_header_pins']} required peripheral/anode pins and unselected fanouts"
        if not wiring["complete_system_wiring"]
        else None,
        remaining_boards_open="Converter, analog/monitor/bypass and peripheral assemblies are not a qualified routed full-unit design",
    )
    plan = dict(
        schema_version=1,
        profile=PROFILE,
        hardware_variant="E14/E25 baseline interfaces; P01 is a separate unimplemented candidate",
        source_base_commit=source_base_commit
        or subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip(),
        source_sha256={n: digest(repo / n) for n in names},
        hard_holds={k: v for k, v in holds.items() if v},
        cases=cases(repo),
        full_unit_power_up_released=False,
        actual_measurements_performed=False,
        build_ready=False,
    )
    plan["plan_sha256"] = hashlib.sha256(
        json.dumps(plan, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return plan
