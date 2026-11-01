"""Receiving-condition comparisons for actual FH02 pin/net/component data.

No table transfer, PCB implementation, silicon timing or physical acceptance is
created by this analysis. Distinguish useful conditional arithmetic from bounds.
"""

import json
import math

from hardware.electronics.common.netlists import number
from hardware.qualification.boards.fan_health.circuit.design import NF, ROOT


def topology_findings(parts):
    by = {p["ref"]: p for p in parts}
    maps = {r: {p["number"]: p["net"] for p in v["pins"]} for r, v in by.items()}
    checks = {
        "exact_MCU_firmware_pin_contract": maps["U1"]
        == {
            "1": "V3V3",
            "2": "XTAL1",
            "3": "XTAL2",
            "4": "MCU_RESET_N",
            "5": "MCU_TACH_R",
            "6": "MCU_HEALTH",
            "7": "ISP_MOSI",
            "8": "ISP_MISO",
            "9": "ISP_SCK",
            "10": "MCU_TACH_L",
            "11": "HEARTBEAT",
            "12": "TEMP_R_ADC",
            "13": "TEMP_L_ADC",
            "14": "GND",
        },
        "latch_independent_RAW5_power": maps["U8"]["8"] == "FAN5V_IN" and maps["U9"]["4"] == "FAN5V_IN",
        "latch_D_high_and_PRE_inactive": maps["U8"]["2"] == maps["U8"]["7"] == "FAN5V_IN",
        "latch_clear_ONLY_raw_supervisor": maps["U8"]["6"] == "RAW_CLEAR_FAST"
        and maps["U10"]["2"] == "RAW_CLEAR_N"
        and maps["U9"]["6"] == "RAW_CLEAR_N",
        "WD_AND_ENOUT_and_LDO_PG_override": maps["U4"]["7"] == maps["U4"]["8"] == maps["U2"]["3"] == "WD_OK",
        "WD_enabled_and_NOT_MCU_defeatable": maps["U4"]["5"] == "V3V3"
        and maps["R7"] == {"1": "V3V3", "2": "WD_EN"},
        "WD_raw_clock_power_isolation": maps["U6"]
        == {"1": "V3V3", "2": "GND", "3": "WD_OK_FAST", "4": "WD_OK_5", "5": "V3V3", "6": "FAN5V_IN"}
        and maps["U7"]["2"] == "WD_OK_5"
        and maps["U7"]["4"] == maps["U8"]["1"] == "FAULT_CLK",
        "WD_slow_open_drain_Schmitt_first": by["U5"]["part"] == "SN74AUP1G17DCKR"
        and maps["U5"]["2"] == "WD_OK"
        and maps["U5"]["4"] == "WD_OK_FAST",
        "heartbeat_loaded_buffer": by["U16"]["part"] == "SN74LVC1G34DCKR"
        and maps["U16"]["2"] == "HEARTBEAT"
        and maps["U16"]["4"] == maps["U4"]["6"] == "HEARTBEAT_FAST",
        "startup_WD_does_NOT_create_MCU_EXTRF": maps["U1"]["4"] == maps["J5"]["5"] == "MCU_RESET_N"
        and maps["R6"] == {"1": "V3V3", "2": "MCU_RESET_N"},
        "permission_has_two_actual_AND_gates": by["U12"]["part"] == by["U13"]["part"] == "SN74LVC1G08DCKR"
        and maps["U12"]["1"] == "MCU_HEALTH"
        and maps["U12"]["2"] == "WD_OK_FAST"
        and maps["U12"]["4"] == maps["U13"]["1"] == "HEALTH_AND_WD"
        and maps["U13"]["2"] == "HW_NOFAULT"
        and maps["U13"]["4"] == "LEAF_PERMISSION",
        "NOFAULT_conditioned_not_backdriving_MCU": maps["U11"]["2"] == maps["U8"]["3"] == "HW_NOFAULT_5"
        and maps["U11"]["4"] == "HW_NOFAULT",
        "LED_raw_feed_shunt_Ioff_sink": maps["R1"] == {"1": "FAN5V_IN", "2": "LED_A"}
        and maps["R2"] == {"1": "LED_A", "2": "LED_K"}
        and maps["U14"]["2"] == "LEAF_PERMISSION"
        and maps["U14"]["4"] == "LED_K"
        and by["U14"]["part"] == "SN74LVC1G06DCKR",
        "LED_permission_loaded_OFF_pulldown": maps["R13"] == {"1": "LEAF_PERMISSION", "2": "GND"}
        and number(by["R13"]["part"]) <= 10000,
        "ONLY_correct_leaf_contact_exact_TLP_pins": maps["U15"]
        == {"1": "LED_A", "3": "LED_K", "4": "P03_POWER_RUN", "6": "E28_POWER_RUN"}
        and maps["J4"] == {"1": "P03_POWER_RUN", "2": "E28_POWER_RUN"},
        "no_MASTER_ENABLE_drive": not any("MASTER_ENABLE" in str(p["net"]) for c in parts for p in c["pins"]),
        "exact_FP01_tach_interface": maps["J1"]
        == {"1": "GND", "2": "FAN5V_IN", "3": None, "4": None, "5": "FAN_L_TACH", "6": "FAN_R_TACH"},
        "fixed_LDO_DNC_and_NC_are_open": maps["U2"]["2"] is None and maps["U2"]["6"] is None,
        "fixed_LDO_explicit_minimum_load": maps["R24"] == {"1": "V3V3", "2": "GND"}
        and number(by["R24"]["part"]) <= 100000,
        "sensor_series_filter_contract": maps["R21"] == {"1": "TEMP_L_NODE", "2": "TEMP_L_ADC"}
        and maps["R23"] == {"1": "TEMP_R_NODE", "2": "TEMP_R_ADC"}
        and maps["C22"]["1"] == "TEMP_L_ADC"
        and maps["C23"]["1"] == "TEMP_R_ADC",
    }
    return checks


def latch_sequence(events):
    """Ideal logic-state control, NOT a power-ramp/propagation proof.

    tuple event=(raw_clear_asserted, WD_OK, MCU_HEALTH); latch stores first
    positive FAULT_CLK edge. Start corresponds clear-low at powered initialization.
    """
    q, old_clock = 0, 1
    result = []
    for clear, wd_ok, health in events:
        clock = not wd_ok
        if clear:
            q = 0
        elif clock and not old_clock:
            q = 1
        permission = bool(health and wd_ok and not q and not clear)
        result.append(dict(latched_fault=bool(q), permission=permission))
        old_clock = clock
    return result


def feed_point(protected_w, plug_v=11.4, feed_ohm=0.36, aux_a=0.09):
    # Protected converter loads are constant power; AUX is direct input current.
    a = feed_ohm
    b = -(plug_v + feed_ohm * aux_a)
    c = plug_v * aux_a + protected_w
    d = b * b - 4 * a * c
    if d < 0:
        raise ValueError("no real steady feed point")
    current = (-b - math.sqrt(d)) / (2 * a)
    return dict(
        current_a=current,
        board_v=plug_v - current * feed_ohm,
        plug_power_w=plug_v * current,
        feed_loss_w=feed_ohm * current**2,
        board_received_power_w=(plug_v - current * feed_ohm) * current,
    )


def analyze(parts, nf_power):
    by = {p["ref"]: p for p in parts}

    def val(ref):
        return number(by[ref]["part"])

    raw_low, raw_high = 4.8, 5.2
    v33_low, v33_high = 3.3 * 0.98, 3.3 * 1.02
    rfeed, rshunt = val("R1"), val("R2")
    led_min = (raw_low - 1.6 - 0.55) / (rfeed * 1.03) - 1.6 / (rshunt * 0.97)
    led_branch_max = (raw_high - 1.0) / (rfeed * 0.97)
    sensor_short = 2 * v33_high / (val("R20") * 0.995)
    wd_cap_nf = val("C7") * 1e9
    wd_min = (77.4 * wd_cap_nf * 0.9 + 55) * 0.905
    wd_max = (77.4 * wd_cap_nf * 1.1 + 55) * 1.095
    timeout_nom = 77.4 * wd_cap_nf + 55
    raw_por_nom = 1.15 * (1 + val("R11") / val("R12"))
    sense_ibias = 100e-9  # table atVSENSE5V; transfer to1.15 is receiving
    por_lo = 1.15 * 0.99 * (1 + val("R11") * 0.99 / (val("R12") * 1.01)) - sense_ibias * val("R11") * 1.01
    por_hi = 1.15 * 1.01 * (1 + val("R11") * 1.01 / (val("R12") * 0.99)) + sense_ibias * val("R11") * 1.01
    # Per-part rail-input ICC rows plus EXPLICIT non-rail-input receiving envelopes.
    # DeltaICC test points do NOT prove these whole-waveform/whole-interval maxima.
    icc = {
        "U1_MCU_complete_VCC_receiving": 0.003,
        "U2_LDO_ground_receiving_at_actual_load": 0.000050,
        "U3_LVC2G17_ICC": 0.000010,
        "U4_TPS3431_IDD": 0.000019,
        "U5_AUP17_ICC": 0.0000009,
        "U6_1T45_sum_ICC": 0.000004,
        "U7_LVC14_ICC": 0.000010,
        "U8_LVC74_ICC": 0.000010,
        "U9_TPS3890_supply_receiving": 0.0000065,
        "U10_LVC17_ICC": 0.000010,
        "U11_LVC17_ICC": 0.000010,
        "U12_LVC08_ICC": 0.000010,
        "U13_LVC08_ICC": 0.000010,
        "U14_LVC06_ICC": 0.000010,
        "U16_LVC34_ICC": 0.000010,
    }
    # U3 two tachinputs; U7 one; U8 CLK+CLR; U10 one; U11 one;
    # U12 two; U13 two; U14 one; U16 one => thirteen LVC inputs.
    delta_input_counts = {
        "U3": 2,
        "U7": 1,
        "U8": 2,
        "U10": 1,
        "U11": 1,
        "U12": 2,
        "U13": 2,
        "U14": 1,
        "U16": 1,
    }
    deltas = {r: n * 0.0005 for r, n in delta_input_counts.items()}
    deltas.update(U5=0.000050, U6=0.000100)
    # Deliberately enclose mutually exclusive stable states by summing their
    # maxima. Do not call this a physically realizable typical current point.
    pullups = {
        "WD_and_ISP_external_pullups_low_enclosure": v33_high
        * (1 / (val("R5") * 0.97) + 1 / (val("R6") * 0.97)),
        "RAW_POR_external_low": raw_high / (val("R10") * 0.97),
        "RAW_POR_divider": raw_high / ((val("R11") + val("R12")) * 0.99),
        "translator_B_high": raw_high / (val("R8") * 0.97),
        "latch_Q_N_high": raw_high / (val("R9") * 0.97),
        "permission_output_high_pulldown": v33_high / (val("R13") * 0.97),
        "WD_EN_pullup_zeroV_input_leak_receiving": 0.000002,
        "LDO_minimum_load_bleed": v33_high / (val("R24") * 0.97),
    }
    # R3/R4 are MCU-driven; their pin-sourced currents are INSIDE MCU VCC3mA.
    # Tach receiver pulldown draw is INSIDE FP01 full tachpullup provision.
    dynamic_receiving = 0.000200
    static_enclosure = (
        sum(icc.values())
        + sum(deltas.values())
        + sum(pullups.values())
        + sensor_short
        + led_branch_max
        + dynamic_receiving
    )
    guarded = 1.2 * static_enclosure
    old_pool = nf_power["remaining_for_fan_health_after_nf20pct_and_fp01_a"]
    proposed_dig = 2.42
    new_pool = old_pool + proposed_dig - nf_power["retained_digital_total_a"]
    known_other = (
        1.984
        + nf_power["fan_partition_a"]
        + nf_power["fan_protection_partition_a"]
        + nf_power["nf_digital_with20pct_requirement_a"]
    )
    delta_w = (proposed_dig - 2.4) * 5.1 / 0.85
    base_feed = feed_point(nf_power["protected_constant_power_requirement_w"])
    new_feed = feed_point(nf_power["protected_constant_power_requirement_w"] + delta_w)
    # Complete receiver loop250ohm RECEIVING, includes switch100ohm plus
    # connectors/wire/P03source impedance150ohm; NOT a measured loop resistance.
    run_lo = (2.533479 - 250 * 22e-6) / (1 + 250 / 9800)
    off_hi = (10e-6 + 22e-6) * 10200
    settle_tau = (val("R20") * 1.005 + val("R21") * 1.03) * val("C22") * 1.10
    checks = topology_findings(parts)
    return dict(
        revision="FH02-native-receiving-design-not-qualification",
        topology_checks=checks,
        topology_all_pass=all(checks.values()),
        voltage_receiving=dict(
            RAW5_v=[raw_low, raw_high],
            V3V3_v=[v33_low, v33_high],
            RAW5_operating_harness_proven=False,
            LDO_actual_load_ground_current_guaranteed=False,
            headroom_at_minimum_input_to_maximum_output_v=raw_low - v33_high,
            manufacturer_accuracy_condition_headroom_v=0.5,
            minimum_load_bleed_receiving_min_a=v33_low / (val("R24") * 1.03),
            manufacturer_accuracy_minimum_load_a=10e-6,
            LDO_effective_CIN_COUT_receiving_f=[3e-6, 14e-6],
            effective_C_and_ESR_qualified=False,
        ),
        LED=dict(
            min_current_under_receiving_VF_VOL_a=led_min,
            minimum_recommended_current_a=0.002,
            has20pct_current_headroom=led_min >= 0.0024,
            maximum_raw_branch_current_under_receiving_VF_a=led_branch_max,
            shunt_is_included_once=True,
            VF_receiving_v=[1.0, 1.6],
            VOL_receiving_max_v=0.55,
            off_sink_Ioff_10ua_shunt_voltage_v=10e-6 * rshunt * 1.03,
            hot_LED_off_current_receiving_max_a=1e-6,
            hot_off_current_proven=False,
            permission_Ioff10ua_plus_input5ua_pulldown_voltage_v=15e-6 * val("R13") * 1.03,
            TLP_recommended_ambient_c=[-40, 65],
            TLP_VF_RON_IFC_switch_times_tables_at25c_only=True,
            OFF_and_falling_rail_behavior_qualified=False,
        ),
        watchdog=dict(
            actual_CWD_f=val("C7"),
            complete_CWD_receiving_tolerance=0.10,
            nominal_timeout_ms=timeout_nom,
            timeout_interval_given_receiving_C_ms=[wd_min, wd_max],
            first_falling_heartbeat_after_WD_supply_valid_receiving_max_ms=160,
            startup_clock_POR_BOD_supply_ramp_all_inside160ms_receiving=True,
            first_heartbeat_has20pct_timeout_headroom=1.2 * 160 <= wd_min,
            firmware_falling_edge_period_ms=20,
            reset_pulse_table_ms=[170, 230],
            first_heartbeat_and_full_ramps_measured=False,
            MCU_RESET_internal_pullup_min_receiving_ohm=20000,
            watchdog_only_sink_receiving_requirement_a=v33_high / (val("R5") * 0.97) + 2e-6,
            external_watchdog_resets_MCU=False,
            cold_POR_external_reset_flag_conflict_avoided_by_separate_RESET_net=True,
            WDO_low_voltage_transferred_from5V3mA_row_qualified=False,
            automatic_retry_reclosure_in_ideal_state_model=False,
            independent_latch_required=True,
            MCU_permission_stuck_HIGH_covered_in_logic_model=True,
        ),
        raw_latch=dict(
            raw_clear_nominal_v=raw_por_nom,
            raw_clear_given_receiving_R_bias_interval_v=[por_lo, por_hi],
            clear_release_nominal_ms=(val("C14") * 1e6 * 1.07 + 25e-6) * 1000,
            translator_off_B_given2ua_plus5ua_v=7e-6 * val("R8") * 1.03,
            latch_off_Q_N_given10ua_plus5ua_v=15e-6 * val("R9") * 1.03,
            reference_G14_VTminus_at4p5_v=1.41,
            reference_G17_VTminus_at3_v=0.89,
            complete_intermediate_supply_threshold_enclosure_qualified=False,
            first_clock_clear_recovery_partial_power_ramps_qualified=False,
            raw_latch_retention_and_powercycle_reset_threshold_measured=False,
        ),
        loaded_levels=dict(
            MCU_VOH_receiving_min_v=2.5,
            MCU_VOL_receiving_max_v=0.5,
            LVC08_and_LVC34_3to3p6_VIH_min_v=2.0,
            LVC08_and_LVC34_VIL_max_v=0.8,
            heartbeat_buffer_VOH_at100ua_min_v=v33_low - 0.1,
            watchdog_VIH_enclosing_v=0.8 * v33_high,
            heartbeat_high_receiving_margin_v=v33_low - 0.1 - 0.8 * v33_high,
            WD_OK_Schmitt_output_load_receiving_max_a=20e-6,
            translator_RAW5_VOH_receiving_min_v=3.8,
            RAW5_G14_VTplus_receiving_max_v=3.33,
            MCU_table3V5mA_to_actual_supply_transfer_guaranteed=False,
            RAW5_discrete_threshold_output_table_enclosure_guaranteed=False,
            all_loaded_levels_and_transition_times_qualified=False,
        ),
        tach=dict(
            source_pullups_in_FP01_ohm=[9900, 10100],
            actual_receiver_pulldown_ohm=val("R14"),
            source_switched_voltage_receiving_v=[raw_low, raw_high],
            receiver_input_leak_receiving_a=5e-6,
            resulting_HIGH_receiving_min_v=(raw_low / 10100 - 5e-6) / (1 / 10100 + 1 / (val("R14") * 0.97)),
            fan_LOW_receiving_max_v=0.4,
            input_voltage_and_edge_noise_partial_power_qualified=False,
        ),
        leaf=dict(
            exact_source="P03.J106.3 POWER_RUN leaf only",
            exact_destination="E28.J5.3",
            source_loaded_receiving_interval_v=[2.533479, 2.656441],
            existing_receiver_R93_ohm=[9800, 10200],
            receiver_input_plus_board_leak_receiving_max_a=22e-6,
            contact_hot_RON_receiving_max_ohm=100,
            complete_loop_receiving_max_ohm=250,
            resulting_HIGH_min_v=run_lo,
            required_receiver_HIGH_v=2.0,
            has20pct_HIGH_headroom=run_lo >= 2.4,
            contact_hot_OFF_leak_receiving_max_a=10e-6,
            resulting_OFF_max_v=off_hi,
            required_receiver_LOW_max_v=0.4,
            has20pct_LOW_headroom=off_hi * 1.2 <= 0.4,
            source_loaded_voltage_and_current_verified=False,
            contact_and_complete_harness_qualified=False,
            complete_turnoff_and_capacitor_discharge_bound_s=None,
        ),
        sensors=dict(
            remote_assembly_parts=["SEMITEC203AT-2", "SEMITEC203AT-2"],
            R25_ohm=[19800, 20200],
            B25_85_K=[3972.87, 4053.13],
            pullup_complete_receiving_tolerance=0.005,
            series_complete_receiving_tolerance=0.03,
            ADC_complete_error_receiving_LSB=3,
            input_and_cap_leak_receiving_a=1.1e-6,
            max_filter_tau_receiving_s=settle_tau,
            firmware_settle_s=0.020,
            firmware_ADC_short_max=8,
            firmware_ADC_open_min=1000,
            firmware_ADC_hot_max=186,
            manufacturer_beta_model_discrepancy_and_R_T_curve_bound=None,
            dissipation_typical_w_per_k=0.002,
            free_air_tau_typical_s=15,
            local_sensor_attachment_and_hot_lag_qualified=False,
        ),
        crystal=dict(
            part=by["X1"]["part"],
            frequency_hz=4e6,
            actual_external_cap_each_f=val("C20"),
            nominal_external_series_load_f=val("C20") / 2,
            manufacturer_load_f=12e-12,
            implied_effective_stray_f=12e-12 - val("C20") / 2,
            initial_and_temperature_catalog_ppm=[30, 30],
            first_year_aging_catalog_ppm=5,
            ESR_max_ohm=180,
            C0_max_f=7e-12,
            drive_max_w=0.001,
            complete_clock_error_receiving_fraction=0.001,
            complete_period_capture_error_receiving_engine_ticks=20,
            catalog_terms_are_NOT_complete_clock_bound=True,
            actual_drive_startup_pulling_aging_and_loaded_frequency_qualified=False,
        ),
        budget=dict(
            ICC_or_complete_MCU_receiving_a=icc,
            extra_nonrail_input_receiving_a=deltas,
            LVC_input_count=sum(delta_input_counts.values()),
            extra_nonrail_rows_AUP50ua_LVC500ua_translator100ua_are_receiving_not_full_interval_guarantees=True,
            independent_pullup_enclosing_a=pullups,
            sensors_both_shorted_a=sensor_short,
            LED_raw_branch_max_a=led_branch_max,
            dynamic_complete_addition_receiving_a=dynamic_receiving,
            complete_enclosing_current_receiving_a=static_enclosure,
            with20pct_a=guarded,
            prior_FH_remaining_a=old_pool,
            fits_prior_2p4A_allocation=guarded <= old_pool,
            proposed_new_DIG_total_a=proposed_dig,
            proposed_new_FH_pool_a=new_pool,
            fits_new_pool=guarded <= new_pool,
            known_other_partitions_a=known_other,
            full_allocated_total_with_FH_guard_a=known_other + guarded,
            new_pool_unallocated_remainder_a=new_pool - guarded,
            MCU_R3_R4_pin_sourced_currents_inside3ma_not_added_twice=True,
            MCU_internal_RESET_pullup_current_inside3ma_not_added_twice=True,
            tach_input_pulldown_current_inside_FP01_tach_pullup_partition=True,
            mutually_exclusive_state_maxima_deliberately_enclosed=True,
            complete_hot_and_dynamic_current_bound_verified=False,
            proposed_DIG_revision_adopted=False,
        ),
        source_delta=dict(
            proposed_DIG_increment_a=0.020,
            assumed_complete_conversion_efficiency=0.85,
            new_protected_power_increment_planning_w=delta_w,
            old_normal_feed_point=base_feed,
            new_normal_feed_point_given_same_conditions=new_feed,
            incremental_inlet_current_a=new_feed["current_a"] - base_feed["current_a"],
            incremental_feed_heat_w=new_feed["feed_loss_w"] - base_feed["feed_loss_w"],
            NF03_capacity_heat_w=nf_power["new_enclosing_whole_inside_heat_requirement_w"],
            proposed_capacity_heat_w=nf_power["new_enclosing_whole_inside_heat_requirement_w"] + delta_w,
            capacity_screen_retains_separate4A_feed_partition=True,
            do_NOT_add_normal_feed_loss_again_to_capacity_heat=True,
            FH_complete_board_RAW5_heat_enclosure_w=raw_high * static_enclosure,
            heat_is_inside_DIG_capacity_NOT_added_again=True,
            new_source_current_voltage_connector_guard_startup_PDN_qualification=False,
        ),
        assembly=dict(
            native_PCB_implemented=False,
            proposed_board_size_mm=[58, 25],
            actual_placement_and_fit_qualified=False,
            remote_NTCs_are_NOT_board_mounted=True,
            programmer_target_power_injection_allowed=False,
            firmware_and_fuse_readback_measured=False,
            TLP_land_pattern_is_own_unapproved_receiving_pattern=True,
            ABLS_manufacturer_land_pattern_used=True,
        ),
        physical_qualified=False,
        fabrication_released=False,
        production_released=False,
        holds=[
            "The 3mA MCU VCC provision includes the actual4MHz crystal/ADC/timers/WDT/I/O; the primary2mA row is a different3V external-clock/PRRff condition and cannot certify this load.",
            "Normal logic voltage intervals and non-rail ICC provisions are explicit receiving requirements; primary discrete rows and delta-ICC test points are not whole-interval/transition guarantees.",
            "TLP175A recommendedambient ends65C. Its quoted VF/returncurrent/RON/switchtime rows are25C; hot complete OFF/ON, LED current and discharge must be measured.",
            "RAW5 latch startup, supervisor delay/retention crossover, slow ramps, source collapse, isolated3.3V resets and watchdog retry require actual waveform fault injection.",
            "The watchdog latch prevents reclosure AFTER a capturedtimeout. A HEALTHpin physicallystuckHIGH before the first timeout can permit an initial startupwindow; no hardware RPM/first-heartbeat qualification or arbitrary single-fault coverage is claimed.",
            "ISP is target-self-powered only; an external3.3V source could phantom-feed LDO/PG/raw-latch state and is not approved.",
            "RAW5 collapse while3.3V output capacitance remains charged requires LDO reverse-current/backfeed and latch-state characterization; no reverse-isolation guarantee is inferred.",
            "No PCB placement/routing, pad manufacture, thermal map, return/current path, fan-supply branch, connector/joint/strain or EMI acceptance is present.",
            "Sensors' typical15s free-air lag and2mW/K dissipation are not installed thermal limits; pot50C and relay65C operating windows require local temperatures.",
            "New2.42A DIG allocation is proposed only and needs full source/guard/PDN/contact/input/startup/heat reconciliation. Old NF03/FP01 seals are unchanged.",
        ],
    )


def main():
    parts = json.loads((ROOT / "components.json").read_text())
    captured = (
        ROOT
        / "sources/repository/hardware/qualification/boards/startup_negative_circuit/compact/generated/analysis.json"
    )
    source = captured if captured.exists() else NF / "generated/analysis.json"
    power = json.loads(source.read_text())["power"]
    result = analyze(parts, power)
    (ROOT / "generated/analysis.json").write_text(json.dumps(result, indent=2) + "\n")
    print(
        json.dumps(
            dict(
                topology=result["topology_all_pass"],
                current_a=result["budget"]["complete_enclosing_current_receiving_a"],
                guarded_a=result["budget"]["with20pct_a"],
                old_pool_a=result["budget"]["prior_FH_remaining_a"],
                proposed_pool_a=result["budget"]["proposed_new_FH_pool_a"],
            )
        )
    )


if __name__ == "__main__":
    main()
