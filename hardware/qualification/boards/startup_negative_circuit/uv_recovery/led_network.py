"""Actual seven-node LED/shunt DC network; no assumed LED forward voltage.

Extreme zero-conductance/ideal-short LED and sink states are diagnostics.
The closed-form current-divider enclosure is stated separately from the scan.
No optical or transient qualification is inferred from this DC computation.
"""

import hashlib
import itertools
import json
from pathlib import Path

import numpy as np

from hardware.electronics.common.netlists import netlist

ROOT = Path(__file__).resolve().parent
NAMES = [
    "CLAMP_LED_SUPPLY",
    "N19_CLAMP_LED_A",
    "N19_CLAMP_LED_MID",
    "N19_CLAMP_LED_K",
    "N12_CLAMP_LED_A",
    "N12_CLAMP_LED_MID",
    "N12_CLAMP_LED_K",
    "AGND",
]


def values():
    actual, pins = netlist(ROOT / "generated/netlist.xml")
    import re

    r = {}
    for ref in ["R4", "R11", "R5", "R12", "R98", "R99", "R97"]:
        m = re.match(r"([\d.]+)([kK]?)", actual[ref].findtext("value"))
        r[ref] = float(m.group(1)) * (1000 if m.group(2) else 1)
    expected = {
        "R4": ("CLAMP_LED_SUPPLY", "N19_CLAMP_LED_A"),
        "R5": ("N19_CLAMP_LED_A", "N19_CLAMP_LED_MID"),
        "R98": ("N19_CLAMP_LED_MID", "N19_CLAMP_LED_K"),
        "R11": ("CLAMP_LED_SUPPLY", "N12_CLAMP_LED_A"),
        "R12": ("N12_CLAMP_LED_A", "N12_CLAMP_LED_MID"),
        "R99": ("N12_CLAMP_LED_MID", "N12_CLAMP_LED_K"),
        "R97": ("CLAMP_LED_SUPPLY", "AGND"),
    }
    assert all(tuple(pins[ref][str(i)] for i in [1, 2]) == pair for ref, pair in expected.items())
    edges = [(NAMES.index(a), NAMES.index(b), ref) for ref, (a, b) in expected.items()]
    return r, edges


def solve(r, edges, short_LEDs, short_sinks):
    parent = list(range(8))

    def find(n):
        while parent[n] != n:
            parent[n] = parent[parent[n]]
            n = parent[n]
        return n

    def union(a, b):
        a, b = find(a), find(b)
        if a != b:
            parent[b] = a

    for yes, (a, b) in zip(short_LEDs, [(1, 2), (2, 3), (4, 5), (5, 6)]):
        if yes:
            union(a, b)
    for yes, k in zip(short_sinks, [3, 6]):
        if yes:
            union(k, 7)
    ground = find(7)
    groups = sorted({find(i) for i in range(8)} - {ground})
    index = {g: i for i, g in enumerate(groups)}
    G = np.zeros((len(groups), len(groups)))
    # First column is the fixed source vector. Seven more columns assign the
    # TOTAL1uA board-source provision to one node at a time, not1uA/node.
    I = np.zeros((len(groups), 8))
    sources = np.zeros((8, 8))
    sources[0, :] = 1e-6
    sources[3, :] = 10e-6
    sources[6, :] = 10e-6
    for j in range(7):
        sources[j, j + 1] += 1e-6
    for node in range(8):
        group = find(node)
        if group != ground:
            I[index[group], :] += sources[node, :]
    for a, b, ref in edges:
        a, b = find(a), find(b)
        if a == b:
            continue
        g = 1 / r[ref]
        for n in [a, b]:
            if n != ground:
                G[index[n], index[n]] += g
        if a != ground and b != ground:
            G[index[a], index[b]] -= g
            G[index[b], index[a]] -= g
    Vg = np.linalg.solve(G, I)
    V = np.zeros((8, 8))
    for node in range(8):
        if find(node) != ground:
            V[node, :] = Vg[index[find(node)], :]
    residual = float(np.max(np.abs(G @ Vg - I)))
    currents = []
    for offset, feed in [(1, "R4"), (4, "R11")]:
        upstream = (V[0, :] - V[offset, :]) / r[feed] + sources[offset, :]
        # With an ideal-short LED, its parallel shunt has zero voltage. KCL
        # gives the LED current without a numerically ill-conditioned1mohm.
        currents.extend([upstream, upstream + sources[offset + 1, :]])
    for j, yes in enumerate(short_LEDs):
        if not yes:
            currents[j] = np.zeros(8)
    return np.array(currents), residual, V


def analyze():
    r, edges = values()
    refs = sorted(r)
    maximum = -1
    worst = None
    residual = 0
    dc_cases = 0
    led_comparisons = 0
    for bits in itertools.product([0.97, 1.03], repeat=len(refs)):
        actual = {name: r[name] * b for name, b in zip(refs, bits)}
        for leds in itertools.product([False, True], repeat=4):
            for sinks in itertools.product([False, True], repeat=2):
                currents, err, V = solve(actual, edges, leds, sinks)
                dc_cases += currents.shape[1]
                led_comparisons += currents.size
                residual = max(residual, err)
                m = float(np.max(currents))
                if m > maximum:
                    maximum = m
                    j, k = np.unravel_index(np.argmax(currents), currents.shape)
                    worst = dict(
                        resistances_ohm=actual,
                        LED_shorts=leds,
                        sink_shorts=sinks,
                        LED_index=int(j),
                        board_source_column=int(k),
                        node_voltages_v=V[:, k].tolist(),
                    )
    # A target sink at ground and both target LEDs at zero voltage maximize
    # its forward current. Its own positive K injection goes to ground. The
    # OTHER10uA plus1uA switch source divides between bleed and target feed;
    # placing the entire board1uA directly on A/M adds at most1uA. The numeric
    # vertex scan must attain this receiving enclosure independently.
    rb = r["R97"] * 1.03
    rf = min(r["R4"], r["R11"]) * 0.97
    enclosure = 11e-6 * rb / (rb + rf) + 1e-6
    assert abs(maximum - enclosure) < 1e-12, (maximum, enclosure)
    assert residual < 1e-15, residual
    return dict(
        revision="NF05R-native-seven-node-LED-DC",
        nodes=NAMES,
        actual_native_resistors_ohm=r,
        dc_cases=dc_cases,
        forward_LED_comparisons=led_comparisons,
        complete_resistor_receiving_fraction=0.03,
        each_OD_complete_positive_source_receiving_a=10e-6,
        OD_VCC0_Ioff_row_is_NOT_powered_or_partial_power_guarantee=True,
        switch_complete_output_source_receiving_a=1e-6,
        board_TOTAL_positive_source_receiving_a=1e-6,
        zero_LED_forward_voltage_credit=True,
        all_nonlinear_LED_and_sink_conductances_scan_open_or_short=True,
        finite_conductance_nonlinear_device_behavior_proven_by_vertex_scan=False,
        independent_enclosure_requires_nonnegative_passive_LED_voltages=True,
        negative_board_leakage_and_transient_injection_bound_accepted=False,
        numeric_max_forward_LED_current_a=maximum,
        independent_Norton_enclosure_a=enclosure,
        forward_current_times1p2_a=1.2 * maximum,
        hot_relay_return_current_minimum_receiving_a=10e-6,
        manufacturer_return_row_only_25C_1200mA=True,
        max_linear_KCL_residual_a=residual,
        worst=worst,
        dynamic_gate_feedthrough_capacitive_and_optical_response_accepted=False,
        source_sha256={
            str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in [ROOT / "generated/netlist.xml", ROOT / "components.json", Path(__file__)]
        },
        numpy_version=np.__version__,
        physical_qualified=False,
        full_cutoff_upper_s=None,
        release_approved=False,
    )


if __name__ == "__main__":
    assert not (ROOT / "handoff.json").exists()
    r = analyze()
    (ROOT / "generated/LED-DC-network.json").write_text(json.dumps(r, indent=2) + "\n")
    print(
        r["dc_cases"],
        r["forward_LED_comparisons"],
        r["numeric_max_forward_LED_current_a"],
        r["forward_current_times1p2_a"],
        r["max_linear_KCL_residual_a"],
    )
