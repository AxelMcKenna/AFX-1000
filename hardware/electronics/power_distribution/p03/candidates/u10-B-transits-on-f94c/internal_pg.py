"""Loaded internal PG logic screen; continuous-supply/edge proof remains open."""

import itertools

import numpy as np

from .models import auxiliary, value

EXPECTED_PINS = {
    "1": "AGND",
    "2": "AGND",
    "3": "P03_SOURCES_READY",
    "4": "P03_MON_BUCK_OK",
    "5": "V2V5_AUX",
    "6": "POWER_READY",
}


def evaluate(parts, pins):
    low, high = auxiliary(parts)["source_interval_v"]
    native = parts["U26"].findtext("value") == "SN74LVC1G97DBVR" and pins["U26"] == EXPECTED_PINS
    truth = []
    if native:
        for buck, guard in itertools.product((0, 1), repeat=2):
            signals = {"AGND": 0, "P03_SOURCES_READY": buck, "POWER_READY": guard}
            # RevNTable1: In2 selects In0 whenHIGH, In1 whenLOW.
            y = signals[pins["U26"]["3"]] if signals[pins["U26"]["6"]] else signals[pins["U26"]["1"]]
            truth.append(dict(buck=buck, guard=guard, y=y, expected=buck and guard))
    pg_high = low - value(parts, "R246") * 1.03 * (2 * 5e-6 + 5e-6)
    states = {"guard_high": [], "guard_low": []}
    refs = ("R110", "R204", "R205", "R224", "R225")
    # Signed EN current is an explicit30uA allocation; the published11.6uA
    # sourcing value atVEN1.3V is typical, not a full operating current bound.
    for supply, signs, leaks in itertools.product(
        (low, high), itertools.product((-1, 1), repeat=5), itertools.product((-1, 1), repeat=3)
    ):
        rp, td, bd, ta, ba = [value(parts, r) * (1 + s * 0.03) for r, s in zip(refs, signs)]
        for name, guard_g in (("guard_high", 0), ("guard_low", 1 / 130)):
            matrix = np.array(
                [
                    [1 / rp + 1 / td + 1 / ta + guard_g, -1 / td, -1 / ta],
                    [-1 / td, 1 / td + 1 / bd, 0],
                    [-1 / ta, 0, 1 / ta + 1 / ba],
                ]
            )
            rhs = np.array([supply / rp - leaks[0] * (5e-6 + 150e-9), -leaks[1] * 30e-6, -leaks[2] * 30e-6])
            states[name].append(np.linalg.solve(matrix, rhs).tolist())
    intervals = {
        name: [[min(r[i] for r in rows), max(r[i] for r in rows)] for i in range(3)]
        for name, rows in states.items()
    }
    return dict(
        native_supported_schmitt_gate_and_pin_map=native,
        primary_source="https://www.ti.com/lit/ds/symlink/sn74lvc1g97.pdf",
        primary_revision="SCES416N Rev N",
        pin_map=EXPECTED_PINS,
        truth_table=truth,
        truth_is_and=native and all(r["y"] == r["expected"] for r in truth),
        operating_supply_range_v=[1.65, 5.5],
        actual_aux_source_interval_v=[low, high],
        recommended_conditions_has_input_transition_rate_row=False,
        generic_application_text_references_absent_transition_rate_row=True,
        schmitt_positive_threshold_neighbor_rows_v={"2.3V_max": 1.56, "3.0V_max": 1.87},
        schmitt_negative_threshold_neighbor_rows_v={"2.3V_min": 0.58, "3.0V_min": 0.84},
        neighbor_threshold_envelope_is_inference_not_continuous_supply_guarantee=True,
        continuous_aux_threshold_enclosure_manufacturer_verified=False,
        buck_pg_high_allocation_v=pg_high,
        buck_pg_low_row_max_v=0.5,
        buck_pg_low_row_test_input_v=12,
        buck_pg_low_over_actual9v8_to13v2_input_verified=False,
        buck_pg_loaded_high_margin_to_inferred1v87_v=pg_high - 1.87,
        buck_pg_low_margin_to_inferred0v58_v=0.58 - 0.5,
        guard_pg_and_enable_intervals_v=intervals,
        guard_pg_pulldown_maximum_ohm=130,
        guard_pg_leakage_bound_a=150e-9,
        two_enable_signed_current_each_allocation_a=30e-6,
        enable_current_allocation_manufacturer_verified=False,
        receiver_input_leakage_row_bound_a=5e-6,
        poweroff_output_leakage_row_bound_a=10e-6,
        monitor_input_load_bound_a=30e-9,
        output_test_current_a=100e-6,
        output_high_minimum_v=low - 0.1,
        output_low_maximum_v=0.1,
        monitor_high_trip_max_v=0.508,
        monitor_low_trip_min_v=0.492,
        monitor_input_contamination_and_capacitance_verified=False,
        slow_ramp_input_noise_hysteresis_partial_power_and_propagation_tested=False,
        physical_qualified=False,
    )
