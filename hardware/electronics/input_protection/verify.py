#!/usr/bin/env python3
"""E16 exported circuit audit and conditional DC/startup/fast-OV screens.

No transient semiconductor simulation, fuse coordination or physical evidence.
The independently declared contracts below do not import the generator spec.
"""

import argparse
import datetime
import hashlib
import itertools
import json
import math
import os
import re
import subprocess
import tempfile
from pathlib import Path

from ..common import netlists as eda
from ..common.circuits import linear_solve
from ..common.reports import source_hashes

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "generated"
SUPPLY = ROOT.parent / "power_supply"


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def number(value):
    m = re.match(r"([0-9.]+)([kMunp]?)", value)
    assert m, value
    return float(m[1]) * {"": 1, "k": 1e3, "M": 1e6, "u": 1e-6, "n": 1e-9, "p": 1e-12}[m[2]]


def contract(parts, pins):
    expected = {}
    values = {}

    def part(ref, value, nets):
        expected[ref] = {str(k): v for k, v in nets.items()}
        values[ref] = value

    def nc(ref, name, pad):
        return f"unconnected-({ref}-{name}-Pad{pad})"

    part(
        "U1",
        "TPS26630RGER",
        {
            1: "VIN_IC",
            2: "VIN_IC",
            3: "BLOCK_GATE",
            4: "BLOCK_DRV",
            5: "VIN_SYS",
            6: "INPUT_UV",
            7: "INPUT_OV",
            8: "AGND",
            9: "INPUT_SLEW",
            10: "INPUT_ILIM",
            11: nc("U1", "MODE", 11),
            12: "POWER_RUN",
            13: nc("U1", "IMON", 13),
            14: nc("U1", "FLT", 14),
            15: "INPUT_PGTH",
            16: "POWER_READY",
            17: "VIN_PROTECTED",
            18: "VIN_PROTECTED",
            25: "AGND",
            **{i: nc("U1", "NC", i) for i in range(19, 25)},
        },
    )
    part(
        "U2",
        "TPS7A1601DGNR",
        {
            1: "V2V5_AUX",
            2: "AUX_FB",
            3: "POWER_RUN",
            4: "AGND",
            5: "VIN_IC",
            6: nc("U2", "NC", 6),
            7: "AUX_START_DELAY",
            8: "VIN_IC",
            9: "AGND",
        },
    )
    part("Q1", "PSMN012-100YS,115", {1: "VIN_SYS", 2: "VIN_SYS", 3: "VIN_SYS", 4: "BLOCK_GATE", 5: "VIN_IC"})
    part("Q2", "BSS138-7-F", {1: "BLOCK_DRV", 2: "VIN_SYS", 3: "BLOCK_GATE"})
    part("Q3", "DMN2056U-7", {1: "FAST_OV_GATE", 2: "AGND", 3: "POWER_RUN"})
    part(
        "U3",
        "TLV7011DBVR",
        {1: "FAST_OV_OUT", 2: "AGND", 3: "FAST_OV_SENSE", 4: "FAST_OV_REF", 5: "V2V5_AUX"},
    )
    part("J1", "PJ-102AH", {1: "DC_IN", 2: "AGND", 3: nc("J1", "SWITCH", 3)})
    part("F1", "0451004.MRL 4A 125V", {1: "DC_IN", 2: "VIN_SYS"})
    part("D1", "SMBJ33CA-E3/52", {1: "VIN_SYS", 2: "AGND"})
    part("D2", "BAS116,215", {1: "INPUT_OV", 2: nc("D2", "NC", 2), 3: "V2V5_AUX"})
    part("D3", "SS16-E3/61T", {1: "VIN_PROTECTED", 2: "AGND"})
    part("S1", "JS102011SAQN", {1: "SWITCH_SUPPLY", 2: "POWER_RUN", 3: "AGND"})
    for ref, nets in [
        ("J2", ["VIN_PROTECTED", "AGND"]),
        ("J3", ["AGND", "POWER_READY"]),
        ("J4", ["SWITCH_SUPPLY", "POWER_RUN", "AGND"]),
        ("J5", ["V2V5_AUX", "AGND"]),
        ("J6", ["V2V5_AUX", "AGND", "POWER_RUN"]),
    ]:
        part(ref, "Header" + str(len(nets)), dict(enumerate(nets, 1)))
    rows = [
        ("VIN_SYS", "INPUT_UV", 309000),
        ("INPUT_UV", "AGND", 40200),
        ("VIN_SYS", "INPUT_OV", 309000),
        ("INPUT_OV", "AGND", 28000),
        ("VIN_PROTECTED", "INPUT_PGTH", 73200),
        ("INPUT_PGTH", "AGND", 10000),
        ("INPUT_ILIM", "AGND", 5620),
        ("V2V5_AUX", "AUX_FB", 110000),
        ("AUX_FB", "AGND", 100000),
        ("V2V5_AUX", "POWER_READY", 1000),
        ("V2V5_AUX", "AGND", 10000),
        ("POWER_RUN", "AGND", 47000),
        ("V2V5_AUX", "SWITCH_SUPPLY", 3300),
        ("VIN_PROTECTED", "AGND", 47000),
        ("VIN_IC", "FAST_OV_SENSE", 30900),
        ("FAST_OV_SENSE", "AGND", 3090),
        ("FAST_OV_OUT", "FAST_OV_SENSE", 309000),
        ("V2V5_AUX", "FAST_OV_REF", 10000),
        ("FAST_OV_REF", "AGND", 10000),
        ("FAST_OV_GATE", "AGND", 100000),
        ("FAST_OV_OUT", "FAST_OV_GATE", 100),
    ]
    for i, (a, b, r) in enumerate(rows, 1):
        ref = f"R{i}"
        expected[ref] = {"1": a, "2": b}
        assert number(parts[ref].findtext("value")) == r, ref
        assert parts[ref].findtext("value").endswith("0.1% 10ppm" if i < 10 or 15 <= i <= 19 else "1%"), ref
    for i, (a, b, v) in enumerate(
        [
            ("VIN_SYS", "AGND", "2.2uF 100V X7R"),
            ("VIN_IC", "AGND", "2.2uF 100V X7R"),
            ("VIN_PROTECTED", "AGND", "220uF 35V electrolytic 20% (EEUFR1V221)"),
            ("VIN_PROTECTED", "AGND", "1uF 50V X7R"),
            ("INPUT_SLEW", "AGND", "330nF 16V X7R"),
            ("V2V5_AUX", "AGND", "10uF 16V X7R"),
            ("V2V5_AUX", "AGND", "100nF 16V X7R"),
            ("V2V5_AUX", "AGND", "100nF 16V X7R"),
            ("FAST_OV_REF", "AGND", "1nF 16V C0G 5%"),
            ("AUX_START_DELAY", "AGND", "10nF 16V C0G 5%"),
        ],
        1,
    ):
        part(f"C{i}", v, {1: a, 2: b})
    assert set(parts) == set(expected) and len(parts) == 48
    for ref, nets in expected.items():
        assert pins[ref] == nets, (ref, pins[ref], nets)
    for ref, value in values.items():
        assert parts[ref].findtext("value") == value, (ref, value)
    assert parts["C3"].findtext("footprint") == "Capacitor_THT:CP_Radial_D8.0mm_P3.50mm"
    for ref, footprint in {
        "U1": "Package_DFN_QFN:Texas_RGE0024H_VQFN-24-1EP_4x4mm_P0.5mm_EP2.7x2.7mm",
        "U2": "Package_SO:MSOP-8-1EP_3x3mm_P0.65mm_EP1.68x1.88mm",
        "Q1": "Package_TO_SOT_SMD:LFPAK56",
        "Q2": "Package_TO_SOT_SMD:SOT-23",
        "Q3": "Package_TO_SOT_SMD:SOT-23",
        "U3": "Package_TO_SOT_SMD:SOT-23-5",
        "J1": "RMX_Input:PJ102AH_RearEdge_E23",
        "F1": "Fuse:Fuse_Littelfuse-NANO2-451_453",
        "D1": "Diode_SMD:D_SMB",
        "D2": "Package_TO_SOT_SMD:SOT-23",
        "D3": "Diode_SMD:D_SMA",
        "S1": "RMX_Input:JS102011SAQN_RearEdge_E23",
    }.items():
        assert parts[ref].findtext("footprint") == footprint, (ref, footprint)
    return dict(
        physical_components=48,
        resistors=21,
        capacitors=10,
        ics=3,
        mosfets=3,
        diodes=3,
        fuses=1,
        switches=1,
        connectors=6,
    )


def threshold(top, bottom, leak, refs):
    # Positive leakage draws current out of the divider node.
    vals = [
        v * (1 + rt / rb) + i * rt
        for rt, rb, v, i in itertools.product(
            (top * 0.997, top * 1.003), (bottom * 0.997, bottom * 1.003), refs, (-leak, leak)
        )
    ]
    return dict(corner_cases=len(vals), minimum_v=min(vals), maximum_v=max(vals))


def fast_guard(parts, minimum_bus):
    def v(r):
        return number(parts[r].findtext("value"))

    bounds = {}
    samples = {}
    gain_max = 0
    input_max = 0
    misplug_input_max = 0
    external_hyst = []
    for state in ("rise", "fall"):
        vals = []
        for aux, signs, error, ip, im, output in itertools.product(
            (2.4, 2.6),
            itertools.product((0.997, 1.003), repeat=5),
            (-0.022, 0.022),
            (-10e-9, 10e-9),
            (-10e-9, 10e-9),
            (0, 1),
        ):
            rt, rb, rf, ra, rz = [v(r) * e for r, e in zip(("R15", "R16", "R17", "R18", "R19"), signs)]
            reference = aux * rz / (ra + rz) + im / (1 / ra + 1 / rz)
            # Output levels at2.4..2.6V are qualification allocations. The
            # manufacturer VOH/VOL entries use5V, not this auxiliary voltage.
            low = 0 if output == 0 else 0.22
            high = aux - 0.3 if output == 0 else aux
            out = low if state == "rise" else high
            gain = 1 + rt / rb + rt / rf
            trip = (reference + error) * gain - out * rt / rf + ip * rt
            vals.append(trip)
            gain_max = max(gain_max, gain)
            external_hyst.append((high - low) * rt / rf)
            # Fail-safe input tolerance is independent of VCC. Fast functional
            # action is screened for24V; higher pulses still need qualification.
            input_max = max(input_max, (60 / rt + aux / rf) / (1 / rt + 1 / rb + 1 / rf))
            misplug_input_max = max(misplug_input_max, (24 / rt + aux / rf) / (1 / rt + 1 / rb + 1 / rf))
        bounds[state] = [min(vals), max(vals)]
        samples[state] = len(vals)
    assert bounds["rise"][0] > 12.6 and bounds["fall"][0] > 12.6
    assert bounds["rise"][1] < 15 and input_max < 5.5 and misplug_input_max < 2.4 + 0.1
    r20 = v("R20") * 0.99
    r21 = v("R21") * 1.01
    gate_min = (2.4 - 0.3) * r20 / (r20 + r21)
    assert gate_min > 1.5
    shdn_current = 2.6 / (v("R13") * 0.99) + 16e-6
    shdn_low = shdn_current * 0.25
    assert shdn_low < 0.8
    # Auxiliary PG is rated0.4V low at1mA. Timing threshold is described only
    # approximately in its datasheet;1V lower bound is a declared allocation.
    assert shdn_current < 1e-3 and 0.4 < 0.8
    aux_pg_delay_min = v("C10") * 0.95 * 1.0 / 2e-6
    ready_allocation = 100e-6 + 5 * (v("R18") * v("R19") / (v("R18") + v("R19"))) * 1.003 * v("C9") * 1.05
    assert aux_pg_delay_min > ready_allocation and 2.4 * 0.85 > 1.6
    timing = dict(
        comparator_at_10mv_overdrive=1e-6, sense_rc=0.1e-6, gate_drive=0.4e-6, efuse_shutdown_max=1.5e-6
    )
    total = sum(timing.values())
    overdrive = 0.010 * gain_max
    initial = bounds["rise"][1] + overdrive + 0.1
    cases = []
    for current, delay in itertools.product((3, 10, 30, 45), (total, 6e-6, 14e-6)):
        peak = initial + current * delay / minimum_bus
        cases.append(
            dict(
                hypothetical_current_a=current,
                assumed_conduction_s=delay,
                estimated_peak_v=peak,
                within_16v=peak < 16,
                inside_allocated_delay=math.isclose(delay, total),
            )
        )
    qualified = [r for r in cases if r["inside_allocated_delay"]]
    assert all(r["within_16v"] for r in qualified)
    assert any(not r["within_16v"] for r in cases)
    return dict(
        rising_threshold_v=bounds["rise"],
        falling_threshold_v=bounds["fall"],
        threshold_corners=sum(samples.values()),
        external_hysteresis_v=[min(external_hyst), max(external_hyst)],
        threshold_offset_plus_hysteresis_allocation_v=0.022,
        input_bias_allocation_each_a=10e-9,
        maximum_sense_voltage_at_60v_v=input_max,
        maximum_sense_voltage_at_24v_v=misplug_input_max,
        comparator_fail_safe_input_maximum_v=5.5,
        qualified_functional_misplug_target_v=24,
        minimum_gate_high_allocation_v=gate_min,
        hot_q3_resistance_allocation_ohm=0.25,
        maximum_shutdown_sink_current_a=shdn_current,
        shutdown_low_allocation_v=shdn_low,
        q3_off_state_leakage_allocation_a=10e-6,
        comparator_low_output_allocation_v=0.22,
        comparator_high_output_headroom_allocation_v=0.3,
        timing_budget_s=timing,
        total_timing_allocation_s=total,
        timing_budget_is_manufacturer_end_to_end_guarantee=False,
        aux_pg_low_max_v=0.4,
        aux_pg_sink_current_rating_for_low_voltage_a=1e-3,
        aux_pg_minimum_delay_under_threshold_allocation_s=aux_pg_delay_min,
        aux_pg_delay_threshold_minimum_allocation_v=1.0,
        comparator_and_reference_ready_allocation_s=ready_allocation,
        comparator_startup_allocation_s=100e-6,
        aux_pg_function_requires_input_at_least_v=3,
        comparator_typical_delay_at_5v_100mv_overdrive_s=310e-9,
        allocated_detection_overdrive_v=0.010,
        converted_input_overdrive_v=overdrive,
        layout_sense_capacitance_allocation_f=20e-12,
        input_charge_budget_c=minimum_bus * (16 - initial),
        hypothetical_cases=cases,
        cases_inside_timing_and_current_allocation=len(qualified),
        maximum_peak_inside_allocation_v=max(r["estimated_peak_v"] for r in qualified),
        all_cases_inside_allocation_pass=True,
        all_stress_cases_pass=False,
        powerup_reference_and_comparator_delay_verified=False,
        manufacturer_guaranteed_gate_drive_at_aux_voltage=False,
        physical_delay_and_fault_charge_verified=False,
    )


def settled_states(parts, pins):
    """Solve exported passive feedback nodes; evaluate conditional settled states.

    Comparator output and transistor limits are allocations. This does not model
    startup waveforms, input excursions, internal PG circuitry or propagation.
    """

    def value(r):
        return number(parts[r].findtext("value"))

    def solve(vin, aux, out):
        fixed = {"AGND": 0, "VIN_IC": vin, "V2V5_AUX": aux, "FAST_OV_OUT": out}
        refs = [f"R{i}" for i in range(15, 22)]
        nodes = sorted({n for r in refs for n in pins[r].values()} - set(fixed))
        index = {n: i for i, n in enumerate(nodes)}
        a = [[0j] * len(nodes) for _ in nodes]
        b = [0j] * len(nodes)
        for ref in refs:
            x, y = [pins[ref][str(i)] for i in (1, 2)]
            g = 1 / value(ref)
            for node, other in ((x, y), (y, x)):
                if node not in index:
                    continue
                i = index[node]
                a[i][i] += g
                if other in index:
                    a[i][index[other]] -= g
                else:
                    b[i] += g * fixed[other]
        result = linear_solve(a, b)
        return {n: result[i].real for n, i in index.items()}

    cases = [
        ("aux_off", 12, 0, False, "on", None, False),
        ("aux_ramping_low_output", 12, 1.5, False, "on", 0, False),
        ("aux_ramping_high_output", 12, 1.5, False, "on", 1.5, False),
        ("aux_delay_holds_start", 12, 2.4, False, "on", None, False),
        ("normal_ready", 12, 2.4, True, "on", None, True),
        ("overvoltage", 24, 2.4, True, "on", None, False),
        ("overvoltage_still_present", 24, 2.6, True, "on", None, False),
        ("input_returns_to_max_normal", 12.6, 2.6, True, "on", None, True),
        ("manual_off", 12, 2.4, True, "off", None, False),
        ("missing_switch", 12, 2.6, True, "missing", None, False),
        ("aux_pg_fault", 12, 2.4, False, "on", None, False),
    ]
    rows = []
    for name, vin, aux, pg, switch, forced, expected in cases:
        low = solve(vin, aux, min(0.22, aux))
        high = solve(vin, aux, max(0, aux - 0.3))
        if forced is not None:
            output = forced
        elif low["FAST_OV_SENSE"] - low["FAST_OV_REF"] > 0.022:
            output = max(0, aux - 0.3)
        else:
            output = min(0.22, aux)
        actual = solve(vin, aux, output)
        gate = actual["FAST_OV_GATE"]
        if name in ("overvoltage", "overvoltage_still_present"):
            assert low["FAST_OV_SENSE"] - low["FAST_OV_REF"] > 0.022
            assert high["FAST_OV_SENSE"] - high["FAST_OV_REF"] > 0.022 and gate > 1.5
        if name == "input_returns_to_max_normal":
            assert high["FAST_OV_SENSE"] - high["FAST_OV_REF"] < -0.022
        r12 = 1 / (1 / value("R12") + 1 / 100000)
        r13 = value("R13")
        # Nominal signal-node DC with conservative limiting values for sinks.
        if switch == "off":
            shdn = 0
        elif gate >= 1.5:
            shdn = (aux / r13 + 16e-6) / (1 / r12 + 1 / r13 + 1 / 0.25)
        elif not pg:
            shdn = 0.4  # PG low bound at less than1mA; VIN_IC>=3V.
        elif switch == "missing":
            shdn = 16e-6 * r12
        else:
            shdn = (aux / r13 - 16e-6) / (1 / r12 + 1 / r13)
        on = shdn > 2
        assert on == expected, (name, shdn, actual)
        if not expected:
            assert shdn < 0.8, (name, shdn)
        rows.append(
            dict(
                name=name,
                vin_ic_v=vin,
                auxiliary_v=aux,
                aux_pg_released=pg,
                switch=switch,
                passive_solution_v=actual,
                comparator_output_allocation_v=output,
                shutdown_v=shdn,
                efuse_enabled_in_settled_model=on,
            )
        )
    return dict(
        cases=len(rows),
        rows=rows,
        exported_passive_nodes_solved=True,
        physical_transient_or_startup_validation=False,
    )


def screens(parts, pins, sparts, spins, power):
    def value(r):
        return number(parts[r].findtext("value"))

    def sval(r):
        return number(sparts[r].findtext("value"))

    uv = threshold(value("R1"), value("R2"), 150e-9, (1.176, 1.224))
    ov = threshold(value("R3"), value("R4"), 230e-9, (1.176, 1.224))
    pg = threshold(value("R5"), value("R6"), 150e-9, (1.176, 1.224))
    uvfall = threshold(value("R1"), value("R2"), 150e-9, (1.09, 1.15))
    ovfall = threshold(value("R3"), value("R4"), 230e-9, (1.09, 1.15))
    assert value("R1") * 0.997 >= 300000 and value("R3") * 0.997 >= 300000
    assert uv["maximum_v"] < 11.4 and ov["minimum_v"] > 12.6
    assert ovfall["minimum_v"] > 12.6 and ov["maximum_v"] < 16
    aux = []
    for rt, rb, err, ib in itertools.product(
        (value("R8") * 0.997, value("R8") * 1.003),
        (value("R9") * 0.997, value("R9") * 1.003),
        (0.98, 1.02),
        (-0.1e-6, 0.1e-6),
    ):
        aux.append(1.193 * err * (1 + rt / rb) + ib * rt)
    assert min(aux) > 2.4 and max(aux) < 2.6
    # Clamp injection cannot hold the bleeder-loaded aux output above2.4V.
    injection = (60 - 2.4) / (value("R3") * 0.997)
    bleeder = 2.4 / (value("R11") * 1.01)
    assert injection < bleeder and 2.6 + 1.3 < 4.0
    # Buck EN source currents have typical-only manufacturer entries.10uA per
    # pin is a qualification allocation, not a guaranteed maximum.
    top = 1 / (1 / sval("R8") + 1 / sval("R12"))
    bottom = 1 / (1 / sval("R9") + 1 / sval("R13"))
    assert top == 5000 and bottom == 11000
    hi = []
    lo = []
    missing = []
    switch = []
    for a, t, b, p, leak in itertools.product(
        (2.4, 2.6),
        (top * 0.99, top * 1.01),
        (bottom * 0.99, bottom * 1.01),
        (value("R10") * 0.99, value("R10") * 1.01),
        (-20e-6, 20e-6),
    ):
        hi.append((a / (p + t) + leak) / (1 / (p + t) + 1 / b))
        # PGOOD on-resistance<=130ohm, loaded by the actual divider.
        g = 130
        series = p + t + p * t / g
        lo.append((a / series + leak) / (1 / b + (1 + p / g) / series))
        missing.append(leak * b)
    assert min(hi) > 1.28 and max(lo) < 1.1 and max(missing) < 1.1
    for a, rp, rs, leak in itertools.product(
        (2.4, 2.6),
        (value("R12") * 0.99, value("R12") * 1.01),
        (value("R13") * 0.99, value("R13") * 1.01),
        (-11e-6, 11e-6),
    ):
        switch.append((a / rs + leak) / (1 / rs + 1 / rp))
    assert min(switch) > 2 and 11e-6 * value("R12") * 1.01 < 0.8
    connected = []
    missing_connected = []
    for a, rp, receiver, rs, leak in itertools.product(
        (2.4, 2.6),
        (value("R12") * 0.99, value("R12") * 1.01),
        (99000, 101000),
        (value("R13") * 0.99, value("R13") * 1.01),
        (-16e-6, 16e-6),
    ):
        parallel = 1 / (1 / rp + 1 / receiver)
        connected.append((a / rs + leak) / (1 / rs + 1 / parallel))
        missing_connected.append(16e-6 * parallel)
    assert min(connected) > 2 and max(missing_connected) < 0.8
    # Read the actual E14 input capacitance, then apply explicitly conditional
    # effective minima and20% nominal upper limits. No MLCC MPN yet selected.
    caps = {
        r: number(c.findtext("value"))
        for r, c in sparts.items()
        if r.startswith("C") and spins[r] == {"1": "VIN_PROTECTED", "2": "AGND"}
    }
    assert len(caps) == 11 and math.isclose(sum(caps.values()), 106.4e-6)
    assert sorted(round(v * 1e6, 3) for v in caps.values()) == [0.1] * 4 + [10] * 4 + [22] * 3
    minimum_supply_caps = sum(5e-6 for v in caps.values() if v > 9e-6)
    assert math.isclose(minimum_supply_caps, 35e-6)
    minimum_bulk = value("C3") * 0.8 + value("C4") * 0.1 + minimum_supply_caps
    maximum_bulk = value("C3") * 1.2 + value("C4") * 1.2 + sum(caps.values()) * 1.2
    assert maximum_bulk < 400e-6
    ramp_max = 1 / (20800 * value("C5") * 0.8) * (2.225 / 2)
    inrush = 400e-6 * ramp_max
    ilim = 18000 / value("R7")
    imin = ilim * 0.90 / 1.003
    imax = ilim * 1.10 / 0.997
    overhead = (
        0.0017
        + 2.6 / (value("R10") * 0.99)
        + 2.6 / (value("R11") * 0.99)
        + 2.6 / ((value("R12") + value("R13")) * 0.99)
    )
    overhead += 2.6 / ((value("R8") + value("R9")) * 0.997) + 12.6 / ((value("R1") + value("R2")) * 0.997)
    overhead += 12.6 / ((value("R3") + value("R4")) * 0.997) + 13.2 / ((value("R5") + value("R6")) * 0.997)
    overhead += 13.2 / (value("R14") * 0.99) + 0.0001
    # Worst simultaneous allocation includes Q3 holding SHDN low while the
    # panel switch is ON, plus its reference and gate pull-down currents.
    overhead += 2.6 / (value("R13") * 0.99) - 2.6 / ((value("R12") + value("R13")) * 0.99)
    overhead += 2.6 / ((value("R18") + value("R19")) * 0.997) + 2.6 / (value("R20") * 0.99) + 20e-6
    assert overhead < 0.010
    # E17 six isolated drivers plus sensing/logic; actual RF/startup current
    # and auxiliary-regulator copper/thermal behavior remain unverified.
    downstream_aux_load = 0.065
    assert overhead + downstream_aux_load < 0.100
    load = power["maximum_allocated_input_power_w"] / 10.5 + 0.010 + downstream_aux_load
    digital_charge = power["digital_startup"]["maximum_extra_input_charging_a"]
    combined = load + inrush + digital_charge
    assert combined < imin and imax < 4
    resistances = dict(
        efuse_maximum=0.053,
        blocking_fet_hot_allocation=0.040,
        jack_maximum=0.030,
        fuse_hot_allocation=0.030,
        wiring_allocation=0.020,
    )
    resistance = sum(resistances.values())
    protected_min = 11.4 - load * resistance
    assert protected_min > 10.5 and pg["maximum_v"] < protected_min
    # A quasi-static trip below16V does NOT prove that a24V misplug transient
    # cannot exceed it. Compute a measurable charge budget and include a sweep
    # which deliberately exposes failing hypothetical current/delay cases.
    reserve = 0.1
    charge = minimum_bulk * (16 - ov["maximum_v"] - reserve)
    assert charge > 0
    transient = []
    for current, delay in itertools.product((3, 10, 30, 45), (8.5e-6, 14e-6, 30e-6)):
        rise = current * delay / minimum_bulk
        transient.append(
            dict(
                hypothetical_current_a=current,
                assumed_conduction_s=delay,
                estimated_peak_v=ov["maximum_v"] + reserve + rise,
                within_16v=rise * minimum_bulk <= charge,
            )
        )
    assert any(r["within_16v"] for r in transient) and any(not r["within_16v"] for r in transient)
    fast = fast_guard(parts, minimum_bulk)
    fast["settled_states"] = settled_states(parts, pins)
    return dict(
        fast_overvoltage_guard=fast,
        thresholds=dict(uv_rising=uv, uv_falling=uvfall, ov_rising=ovfall, pg_rising=pg),
        threshold_corners=sum(v["corner_cases"] for v in (uv, uvfall, ov, ovfall, pg)),
        auxiliary=dict(
            calculated_v=[min(aux), max(aux)],
            allocated_v=[2.4, 2.6],
            corners=len(aux),
            reference_error_fraction=0.02,
            feedback_bias_a=0.1e-6,
            resistor_total_fraction=0.003,
            ov_clamp_forward_drop_allocation_v=1.3,
            ov_pin_positive_clamp_allocation_v=3.9,
            clamp_injection_at_60v_a=injection,
            minimum_bleeder_current_at_2v4_a=bleeder,
            physical_clamp_and_temperature_verified=False,
        ),
        guard=dict(
            high_v=[min(hi), max(hi)],
            low_v=[min(lo), max(lo)],
            cases=len(hi),
            missing_cable_max_v=max(missing),
            buck_en_source_current_allocation_each_a=10e-6,
            buck_en_source_current_is_manufacturer_guarantee=False,
            power_switch_high_v=[min(switch), max(switch)],
            missing_switch_max_v=11e-6 * value("R12") * 1.01,
            switch_high_with_e17_receiver_v=[min(connected), max(connected)],
            missing_switch_with_e17_receiver_max_v=max(missing_connected),
            e17_missing_run_harness_max_v=5e-6 * 101000,
            e17_run_receiver_pulldown_ohm=100000,
            pgood_requires_internal_fet_enhanced=True,
            missing_harness_disables_under_leakage_allocation=True,
            physical_sequence_verified=False,
        ),
        load=dict(
            input_power_allocation_w=power["maximum_allocated_input_power_w"],
            protection_overhead_screen_a=overhead,
            protection_overhead_allocation_a=0.010,
            e17_auxiliary_load_allocation_a=downstream_aux_load,
            total_auxiliary_current_screen_a=overhead + downstream_aux_load,
            aux_regulator_normal_input_dissipation_allocation_w=(12.6 - 2.4)
            * (overhead + downstream_aux_load),
            maximum_allocated_steady_input_a=load,
            efuse_nominal_limit_a=ilim,
            efuse_allocated_limit_a=[imin, imax],
            programming_error_allocation_fraction=0.10,
            programming_resistor_ohm=value("R7"),
            programming_error_at_selected_resistor_is_manufacturer_guarantee=False,
            e14_direct_input_capacitors_f=caps,
            minimum_effective_bus_f=minimum_bulk,
            nominal_tolerance_maximum_bus_f=maximum_bulk,
            qualified_bus_upper_allocation_f=400e-6,
            ramp_gain_is_nominal=True,
            dvdt_current_extremes_ua=[1.775, 2.225],
            ramp_max_allocation_v_per_s=ramp_max,
            inrush_current_allocation_a=inrush,
            digital_preconnected_bulk_ramp_input_allocation_a=digital_charge,
            combined_load_plus_ramp_a=combined,
            remaining_current_margin_a=imin - combined,
            other_rail_charging_or_late_switch_close_included=False,
            path_resistance_ohm=resistances,
            minimum_allocated_protected_input_v=protected_min,
            efuse_hot_conduction_allocation_w=load * load * 0.053,
            physical_load_inrush_soa_thermal_verified=False,
        ),
        overvoltage_transient=dict(
            static_maximum_trip_v=ov["maximum_v"],
            bus_abs_limit_v=16,
            reserved_overshoot_v=reserve,
            remaining_transferred_charge_c=charge,
            manufacturer_ovp_to_flt_delay_s=[8.5e-6, 14e-6],
            timing_condition="OVP20mV above threshold to FLT low; not proof of end-to-end current interruption",
            hypothetical_cases=transient,
            all_hypothetical_cases_pass=False,
            adapter3a_is_an_instantaneous_current_bound=False,
            physical_transferred_charge_verified=False,
        ),
        reverse_topology=dict(
            external_fet_source="VIN_SYS",
            external_fet_drain="VIN_IC",
            external_body_diode_forward="VIN_SYS -> VIN_IC",
            internal_body_diode_forward="VIN_PROTECTED -> VIN_IC",
            auxiliary_cold_start_path="Q1 body diode -> VIN_IC -> U2",
            pulldown_fet_source="VIN_SYS",
            bench_reverse_current_and_charged_output_verified=False,
        ),
        limits=dict(
            steady_misplug_target_v=24,
            tvs_standoff_v=33,
            tvs_rated_pulse_clamp_v=53.3,
            efuse_input_operating_maximum_v=60,
            blocking_fet_vds_rating_v=100,
            fuse_tvs_adapter_coordination_verified=False,
            iec_surge_qualification=False,
            downstream_rail_ov_disconnect_implemented=False,
            pcb_routed=False,
            physical_power_verified=False,
        ),
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kicad-cli", required=True, type=Path)
    parser.add_argument(
        "--footprints",
        type=Path,
        default=Path("/private/tmp/rmx-kicad/KiCad/KiCad.app/Contents/SharedSupport/footprints"),
    )
    args = parser.parse_args()
    OUT.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="rmx-e15-") as temp:
        env = os.environ.copy()
        env["KICAD_CONFIG_HOME"] = temp + "/config"
        env["KICAD10_FOOTPRINT_DIR"] = str(args.footprints)
        env["FONTCONFIG_FILE"] = str(ROOT.parents[2] / "build-hardware/kicad-fonts.conf")

        def run(*words):
            r = subprocess.run(
                [str(args.kicad_cli), *map(str, words)], env=env, text=True, capture_output=True
            )
            assert r.returncode == 0, (words, r.stdout, r.stderr)
            return r.stdout.strip()

        version = run("--version")
        sheet = ROOT / "input_protection.kicad_sch"
        run(
            "sch",
            "erc",
            "--severity-all",
            "--exit-code-violations",
            "--format",
            "json",
            "-o",
            OUT / "erc.json",
            sheet,
        )
        assert all(not s["violations"] for s in json.loads((OUT / "erc.json").read_text())["sheets"])
        run("sch", "export", "netlist", "--format", "kicadxml", "-o", OUT / "netlist.xml", sheet)
        parts, pins = eda.netlist(OUT / "netlist.xml")
        counts = contract(parts, pins)
        supply_net = Path(temp) / "supply.xml"
        run(
            "sch",
            "export",
            "netlist",
            "--format",
            "kicadxml",
            "-o",
            supply_net,
            SUPPLY / "power_supply.kicad_sch",
        )
        sparts, spins = eda.netlist(supply_net)
        assert pins["J2"] == spins["J1"] and pins["J3"] == spins["J5"]
        assert spins["U2"]["2"] == spins["U3"]["2"] == "SUPPLY_ENABLE"
        downstream_sheet = ROOT.parent / "rail_disconnect/rail_disconnect.kicad_sch"
        downstream_net = Path(temp) / "disconnect.xml"
        run("sch", "export", "netlist", "--format", "kicadxml", "-o", downstream_net, downstream_sheet)
        downstream_parts, downstream_pins = eda.netlist(downstream_net)
        assert downstream_pins["J5"] == pins["J6"]
        receiver = [
            r
            for r in downstream_parts
            if r.startswith("R") and downstream_pins[r] == {"1": "POWER_RUN", "2": "AGND"}
        ]
        assert len(receiver) == 1 and number(downstream_parts[receiver[0]].findtext("value")) == 100000
        plan = json.loads((ROOT / "integration.json").read_text())
        assert plan["load_update_revision"] == "E21"
        assert plan["current_limit_programming_resistor_ohm"] == number(parts["R7"].findtext("value"))
        assert math.isclose(plan["protected_input_slew_cap_f"], number(parts["C5"].findtext("value")))
        assert plan["output"]["header"] == [pins["J2"][str(i)] for i in (1, 2)]
        assert plan["guard"]["header"] == ["AGND", "POWER_READY"]
        assert plan["input"]["required_delivered_at_inlet_v"] == [11.4, 12.6]
        assert plan["startup_guard_schematic_implemented"] and not plan["physical_protection_verified"]
        assert plan["revision"] == "E16" and plan["fast_overvoltage_guard"]["comparator"] == parts[
            "U3"
        ].findtext("value")
        assert plan["fast_overvoltage_guard"]["sense_net"] == pins["R15"]["1"] == "VIN_IC"
        assert not plan["fast_overvoltage_guard"]["uses_main_digital_or_mcu"]
        assert plan["e17_interface"]["auxiliary_load_allocation_a"] == 0.065
        assert plan["e17_interface"]["run_pulldown_ohm"] == 100000
        for r in ("R8", "R12"):
            assert spins[r] == {"1": "POWER_READY", "2": "SUPPLY_ENABLE"}
        for r in ("R9", "R13"):
            assert spins[r] == {"1": "SUPPLY_ENABLE", "2": "AGND"}
        supply_report = json.loads((SUPPLY / "generated/verification.json").read_text())
        assert supply_report["native_erc_violations"] == 0 and supply_report["physical_components"] == 157
        for p, digest in supply_report["source_sha256"].items():
            assert sha(SUPPLY / p) == digest, p
        screen = screens(
            parts,
            pins,
            sparts,
            spins,
            json.loads((SUPPLY / "generated/electrical-screens.json").read_text())["power"],
        )
        footprints = {}
        for ref, part in parts.items():
            identifier = part.findtext("footprint")
            lib, name = identifier.split(":")
            path = (
                (ROOT if lib == "RMX_Input" else args.footprints) / (lib + ".pretty") / (name + ".kicad_mod")
            )
            assert set(pins[ref]) <= set(re.findall(r'\(pad\s+"([^"]+)"', path.read_text())), (
                ref,
                identifier,
            )
            footprints[identifier] = sha(path)
        (OUT / "electrical-screens.json").write_text(json.dumps(screen, indent=2) + "\n")
        run("sch", "export", "svg", "--exclude-drawing-sheet", "-o", str(OUT) + os.sep, sheet)
        board_record_path = OUT / "routing-verification.json"
        board_record = None
        if board_record_path.exists():
            board_record = json.loads(board_record_path.read_text())
            assert board_record["revision"] == "E23"
            assert all(
                board_record[k] == 0
                for k in ("native_drc_violations", "schematic_parity_issues", "unconnected_items")
            )
            for path, digest in board_record["source_sha256"].items():
                assert sha(ROOT / path) == digest, ("Rerun input_protection.check_board", path)
        sources = [
            p
            for p in ROOT.iterdir()
            if p.is_file() and p.suffix not in (".pyc", ".prl", ".lck", ".kicad_prl")
        ]
        sources.extend(
            [
                ROOT.parent / "output_stage/verify.py",
                SUPPLY / "power_supply.kicad_sch",
                SUPPLY / "generated/verification.json",
                SUPPLY / "generated/electrical-screens.json",
                downstream_sheet,
            ]
        )
        if board_record is not None:
            sources.append(board_record_path)
        sources.extend(ROOT.glob("RMX_Input.pretty/*.kicad_mod"))
        report = dict(
            revision="E16",
            load_update_revision="E21",
            checked_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            kicad_version=version,
            native_erc_violations=0,
            physical_components=len(parts),
            exact_exported_contracts=counts,
            threshold_corners=screen["threshold_corners"],
            footprint_library_sha256=footprints,
            fresh_main_supply_export=True,
            main_supply_components=157,
            startup_guard_schematic_implemented=True,
            input_protection_schematic_implemented=True,
            fast_ov_shutdown_schematic_implemented=True,
            fast_ov_threshold_corners=screen["fast_overvoltage_guard"]["threshold_corners"],
            fast_ov_delay_and_charge_physically_verified=False,
            fast_ov_settled_state_cases=screen["fast_overvoltage_guard"]["settled_states"]["cases"],
            external_rail_disconnect_schematic_implemented=True,
            downstream_rail_ov_disconnect_implemented=False,
            pcb_routed=board_record is not None,
            pcb_routing_revision="E23" if board_record is not None else None,
            physical_power_verified=False,
            source_sha256=source_hashes(ROOT, sorted(sources)),
        )
        (OUT / "verification.json").write_text(json.dumps(report, indent=2) + "\n")
    print(
        f"KiCad{version}: zero ERC;48 exact contracts;{screen['threshold_corners']} eFuse and {screen['fast_overvoltage_guard']['threshold_corners']} fast-OV threshold corners; E14 interface checked. Physical delay/charge/fuse/layout proof open."
    )


if __name__ == "__main__":
    main()
