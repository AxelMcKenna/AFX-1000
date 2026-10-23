#!/usr/bin/env python3
"""E17 independent exported topology, source interfaces and conditional screens.

No switch transient, real fault-current, regulator stability or physical proof.
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
from ..common.reports import source_hashes

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "generated"

RAILS = ["P19", "N19", "P12", "N12", "V5_REG", "5V_DIG"]
FET_FP = "Package_SON:VSONP-8-1EP_5x6_P1.27mm"


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def number(v):
    m = re.match(r"([0-9.]+)([kMunp]?)", v)
    assert m, v
    return float(m[1]) * {"": 1, "k": 1e3, "M": 1e6, "u": 1e-6, "n": 1e-9, "p": 1e-12}[m[2]]


def contract(parts, pins):
    used = set()
    found = {}

    def ic(ref, value, nets):
        assert parts[ref].findtext("value") == value, (ref, value)
        assert pins[ref] == {str(i): n for i, n in nets.items()}, (ref, pins[ref], nets)
        used.add(ref)

    def passive(prefix, a, b, v, precision=False):
        candidates = [
            r
            for r in parts
            if r not in used
            and r.startswith(prefix)
            and pins[r] == {"1": a, "2": b}
            and (
                parts[r].findtext("value") == v
                if isinstance(v, str)
                else math.isclose(number(parts[r].findtext("value")), v)
            )
        ]
        assert candidates, (prefix, a, b, v)
        r = sorted(candidates)[0]
        used.add(r)
        if prefix == "R":
            assert parts[r].findtext("value").endswith("0.01% 5ppm" if precision else "1%"), r
        found.setdefault((prefix, a, b), []).append(r)
        return r

    def r(a, b, v, p=False):
        return passive("R", a, b, v, p)

    def c(a, b, v):
        return passive("C", a, b, v)

    for i, name in enumerate(RAILS, 1):
        src = name + "_SRC"
        common = name + "_COMMON"
        gate = name + "_GATE"
        drive = name + "_DRIVE"
        for ref, drain in [(f"Q{2 * i - 1}", src), (f"Q{2 * i}", name)]:
            ic(ref, "CSD18540Q5B" if i <= 4 else "CSD18510Q5B", {1: common, 2: gate, 3: drain})
            assert parts[ref].findtext("footprint") == FET_FP
        if name == "5V_DIG":
            for ref, drain in (("Q13", src), ("Q14", name)):
                ic(ref, "CSD18510Q5B", {1: common, 2: gate, 3: drain})
                assert parts[ref].findtext("footprint") == FET_FP
        ic(
            f"U{i}",
            "SI8751AB-ISR",
            {
                1: "V2V5_AUX",
                2: name + "_TT",
                3: name + "_ALLOW",
                4: "AGND",
                5: common,
                6: name + "_MCAP2",
                7: name + "_MCAP1",
                8: drive,
            },
        )
        r(drive, gate, 22)
        r(gate, common, 20e6)
        r(name + "_TT", "AGND", 10000)
        r("ALL_RAILS_ALLOW", name + "_ALLOW", 100)
        r(name + "_ALLOW", "AGND", 10000)
        c("V2V5_AUX", "AGND", "100nF 16V X7R")
        for drain, j in ((src, 1), (name, 2)):
            mid = name + f"_MCAP{j}_LIMIT"
            r(drain, mid, 15000)
            c(mid, name + f"_MCAP{j}", "10pF 100V C0G 5%")
        bulk = [
            "1500uF 35V electrolytic 20% EEUFR1V152S",
            "1500uF 35V electrolytic 20% EEUFR1V152S",
            "220uF 35V electrolytic 20% EEUFR1V221",
            "220uF 35V electrolytic 20% EEUFR1V221",
            "1500uF 16V electrolytic 20% EEUFR1C152",
            "4700uF 16V electrolytic 20% EEUFR1C472",
        ][i - 1]
        a, b = ("AGND", name) if name.startswith("N") else (name, "AGND")
        cr = c(a, b, bulk)
        r(name, "AGND", 47000)
        fp = (
            "CP_Radial_D16.0mm_P7.50mm"
            if i in (1, 2, 6)
            else "CP_Radial_D8.0mm_P3.50mm"
            if i in (3, 4)
            else "CP_Radial_D10.0mm_P5.00mm"
        )
        assert parts[cr].findtext("footprint") == "Capacitor_THT:" + fp
    ic(
        "U7",
        "REF35125QDBVR",
        {1: "AGND", 2: "AGND", 3: "V2V5_AUX", 4: "V2V5_AUX", 5: "unconnected-(U7-NR-Pad5)", 6: "PROTECT_REF"},
    )
    c("V2V5_AUX", "AGND", "100nF 16V X7R")
    c("PROTECT_REF", "AGND", "1uF 16V X7R")
    ic(
        "U8",
        "OPA2333AID",
        {
            1: "N19_INV",
            2: "N19_SUM",
            3: "AGND",
            4: "AGND",
            5: "AGND",
            6: "N12_SUM",
            7: "N12_INV",
            8: "V2V5_AUX",
        },
    )
    for name, terms in [("N19", [150000, 6200]), ("N12", [100000])]:
        node = name + "_SRC"
        for j, v in enumerate(terms):
            end = name + "_SUM" if j == len(terms) - 1 else name + "_INPUT_MID"
            r(node, end, v, True)
            node = end
        r(name + "_INV", name + "_SUM", 10000, True)
        r(name + "_INV", name + "_OV_SENSE", 1000)
        c(name + "_OV_SENSE", "AGND", "100pF 50V C0G 5%")
    c("V2V5_AUX", "AGND", "100nF 16V X7R")
    comparisons = []
    for name in RAILS:
        sense = name + "_OV_SENSE"
        ref = name + "_OV_REF"
        out = name + "_OV_OK"
        if not name.startswith("N"):
            terms = {"P19": [143000, 3300], "P12": [90900], "V5_REG": [31600], "5V_DIG": [31600]}[name]
            node = name + "_SRC"
            for j, v in enumerate(terms):
                end = sense if j == len(terms) - 1 else name + "_SENSE_MID"
                r(node, end, v, True)
                node = end
            r(sense, "AGND", 10000, True)
            c(sense, "AGND", "100pF 50V C0G 5%")
        r("PROTECT_REF", ref, 10000, True)
        r(out, ref, 20e6)
        r("V2V5_AUX", out, 10000)
        comparisons.append((ref, sense, out))
    for name, top in [("REF_LOW", 12400), ("REF_HIGH", 7500)]:
        sense = name + "_AUX"
        r("V2V5_AUX", sense, top, True)
        r(sense, "AGND", 10000, True)
        pos = "PROTECT_REF" if name == "REF_LOW" else sense
        neg = sense if name == "REF_LOW" else "PROTECT_REF"
        ref = name + "_POSITIVE"
        out = name + "_OK"
        r(pos, ref, 10000, True)
        r(out, ref, 20e6)
        r("V2V5_AUX", out, 10000)
        comparisons.append((ref, neg, out))
    cp = [(5, 4, 2), (7, 6, 1), (9, 8, 14), (11, 10, 13)]
    for i in range(2):
        nets = {3: "V2V5_AUX", 12: "AGND"}
        for (pos, neg, out), (pp, pn, po) in zip(comparisons[i * 4 : i * 4 + 4], cp):
            nets.update({pp: pos, pn: neg, po: out})
        ic(f"U{9 + i}", "TLV1824IDR", nets)
        c("V2V5_AUX", "AGND", "100nF 16V X7R")
    gates = [
        ("P19_OV_OK", "N19_OV_OK", "OK_19"),
        ("P12_OV_OK", "N12_OV_OK", "OK_12"),
        ("V5_REG_OV_OK", "5V_DIG_OV_OK", "OK_5"),
        ("REF_LOW_OK", "REF_HIGH_OK", "OK_REF"),
        ("OK_19", "OK_12", "OK_ANALOG"),
        ("OK_5", "OK_REF", "OK_AUXILIARY"),
        ("OK_ANALOG", "OK_AUXILIARY", "OK_ALL_OV"),
        ("OK_ALL_OV", "POWER_RUN", "ALL_RAILS_ALLOW"),
    ]
    gp = [(1, 2, 3), (4, 5, 6), (9, 10, 8), (12, 13, 11)]
    for i in range(2):
        nets = {7: "AGND", 14: "V2V5_AUX"}
        for (a, b, y), (pa, pb, py) in zip(gates[i * 4 : i * 4 + 4], gp):
            nets.update({pa: a, pb: b, py: y})
        ic(f"U{11 + i}", "SN74LVC08APWR", nets)
        c("V2V5_AUX", "AGND", "100nF 16V X7R")
    r("POWER_RUN", "AGND", 100000)
    r("PROTECT_REF", "AGND", 10000, True)
    c("V2V5_AUX", "AGND", "10uF 16V X7R")
    for ref, nets in [
        ("J1", ["P19_SRC", "AGND", "N19_SRC", "P12_SRC", "N12_SRC", "V5_REG_SRC"]),
        ("J2", ["5V_DIG_SRC", "AGND"]),
        ("J3", ["P19", "AGND", "N19", "P12", "N12", "V5_REG"]),
        ("J4", ["5V_DIG", "AGND"]),
        ("J5", ["V2V5_AUX", "AGND", "POWER_RUN"]),
        ("J6", ["AGND", "ALL_RAILS_ALLOW", "PROTECT_REF"]),
    ]:
        ic(ref, "Header" + str(len(nets)), dict(enumerate(nets, 1)))
    assert used == set(parts) and len(parts) == 164, (len(used), set(parts) - used)
    return dict(
        physical_components=164,
        resistors=sum(r.startswith("R") for r in parts),
        capacitors=sum(r.startswith("C") for r in parts),
        mosfets=14,
        isolated_drivers=6,
        other_ics=6,
        headers=6,
    )


def screens(parts, pins, supply, input_report):
    def val(ref):
        return number(parts[ref].findtext("value"))

    def edge(a, b):
        rs = [r for r in parts if r.startswith("R") and pins[r] == {"1": a, "2": b}]
        assert len(rs) == 1, (a, b, rs)
        return val(rs[0])

    rows = []
    for name in RAILS:
        limits = {}
        for state in ("rise", "fall"):
            results = []
            gains = []
            for (
                referror,
                aux,
                rt_error,
                rb_error,
                rs_error,
                rh_error,
                vo_choice,
                offset,
                ip,
                im,
                amp_error,
            ) in itertools.product(
                (-0.003, 0.003),
                (2.4, 2.6),
                (-0.001, 0.001),
                (-0.001, 0.001),
                (-0.001, 0.001),
                (-0.05, 0.05),
                (0, 1),
                (-0.005, 0.005),
                (-10e-9, 10e-9),
                (-10e-9, 10e-9),
                (-0.00012, 0.00012) if name.startswith("N") else (0,),
            ):
                vref = 1.25 * (1 + referror)
                rs = edge("PROTECT_REF", name + "_OV_REF") * (1 + rs_error)
                rh = edge(name + "_OV_OK", name + "_OV_REF") * (1 + rh_error)
                out = (
                    (aux - 0.2 if vo_choice == 0 else aux)
                    if state == "rise"
                    else (0 if vo_choice == 0 else 0.4)
                )
                threshold = (vref / rs + out / rh + ip) / (1 / rs + 1 / rh) + offset
                if name.startswith("N"):
                    rin = sum(
                        val(r)
                        for r in parts
                        if r.startswith("R")
                        and pins[r]["1"] in (name + "_SRC", name + "_INPUT_MID")
                        and pins[r]["2"] in (name + "_SUM", name + "_INPUT_MID")
                    ) * (1 + rt_error)
                    rf = edge(name + "_INV", name + "_SUM") * (1 + rb_error)
                    gain = rin / rf
                    trip = (
                        threshold - amp_error + im * edge(name + "_INV", name + "_OV_SENSE") * 1.01
                    ) * gain
                else:
                    rt = sum(
                        val(r)
                        for r in parts
                        if r.startswith("R")
                        and (
                            pins[r]["1"] == name + "_SRC"
                            and ("SENSE" in pins[r]["2"])
                            or pins[r]["1"] == name + "_SENSE_MID"
                        )
                    ) * (1 + rt_error)
                    rb = edge(name + "_OV_SENSE", "AGND") * (1 + rb_error)
                    gain = 1 + rt / rb
                    trip = threshold * gain + im * rt
                results.append(trip)
                gains.append(gain)
            limits[state] = [min(results), max(results)]
        normal = {"P19": 19.19, "N19": 19.19, "P12": 12.12, "N12": 12.12, "V5_REG": 5.025, "5V_DIG": 5.1}[
            name
        ]
        assert limits["rise"][0] > normal and limits["fall"][0] > normal, (name, limits, normal)
        # 100pF manufacturer gate timing is not used as a complete-system bound.
        current = 3 if name == "5V_DIG" else 1
        cap = next(
            r
            for r in parts
            if r.startswith("C") and "electrolytic" in parts[r].findtext("value") and name in pins[r].values()
        )
        cmin = val(cap) * 0.8
        timing = 125e-6
        reserve = 0.1
        overdrive = max(gains) * 0.001
        peak = limits["rise"][1] + overdrive + reserve + current * timing / cmin
        hard = 20 if name.endswith("19") else 18 if name.endswith("12") else 5.5
        # This intentionally records a failure instead of inventing current or
        # capacitance margins if the declared envelope does not close.
        stresses = [
            dict(
                hypothetical_current_a=i,
                assumed_interruption_s=t,
                estimated_peak_v=limits["rise"][1] + overdrive + reserve + i * t / cmin,
                below_hard_limit=limits["rise"][1] + overdrive + reserve + i * t / cmin < hard,
            )
            for i, t in itertools.product((current, 3 * current), (timing, 250e-6))
        ]
        rows.append(
            dict(
                name=name,
                thresholds=limits,
                corners_per_edge=len(results),
                normal_maximum_v=normal,
                minimum_effective_bulk_f=cmin,
                allocated_fault_current_a=current,
                interruption_allocation_s=timing,
                comparator_overdrive_allocation_v=0.001,
                converted_source_overdrive_v=overdrive,
                reserved_overshoot_v=reserve,
                conditional_peak_v=peak,
                hard_limit_screen_v=hard,
                allocated_envelope_pass=peak < hard,
                stress_cases=stresses,
                actual_fault_current_and_timing_verified=False,
            )
        )
    # Loaded gate output includes2uA total FET leakage and20M bleed. All are
    # engineering hot allocations; datasheet values are not extrapolated silently.
    gate_rows = []
    for name in RAILS:
        count = 4 if name == "5V_DIG" else 2
        leakage = count * 1e-6
        gate_rows.append(
            dict(
                name=name,
                mosfets=count,
                hot_total_gate_leakage_allocation_a=leakage,
                minimum_loaded_v=(9 - leakage * 370000) / (1 + 370000 / (20e6 * 0.99)),
                maximum_loaded_v=(13 + leakage * 370000) / (1 + 370000 / (20e6 * 1.01)),
                actual_gate_charge_and_switch_timing_verified=False,
            )
        )
    gate_min = min(row["minimum_loaded_v"] for row in gate_rows)
    gate_max = max(row["maximum_loaded_v"] for row in gate_rows)
    assert gate_min > 4.5 and gate_max < 20
    input_high = (1.9 / 101 - 10e-6) / (1 / 101 + 1 / 9900)
    input_low = (0.4 / 99 + 10e-6) / (1 / 99 + 1 / 10100)
    assert input_high > 2.6 * 0.5 and input_low < 2.4 * 0.25
    assert 10e-6 * 10100 < 2.4 * 0.25
    reference_margins = []
    for aux, ref, signs, out, offset, ib in itertools.product(
        (2.4, 2.6),
        (1.25 * 0.997, 1.25 * 1.003),
        itertools.product((0.999, 1.001), repeat=3),
        (0, 0.4),
        (-0.005, 0.005),
        (-10e-9, 10e-9),
    ):
        low = aux * (10000 * signs[1]) / (12400 * signs[0] + 10000 * signs[1])
        high = aux * (10000 * signs[1]) / (7500 * signs[0] + 10000 * signs[1])
        # A1% hysteresis feedback uncertainty is covered by the20M+10k
        # worst additive shift; these are coarse startup windows only.
        shift = aux * 10000 * 1.001 / (20e6 * 0.95)
        reference_margins.extend(
            [
                ref - low - abs(offset) - abs(ib) * 10000 - shift,
                high - ref - abs(offset) - abs(ib) * 20000 - shift,
            ]
        )
    assert min(reference_margins) > 0
    # Seven high comparator outputs could otherwise lift an open reference
    # through20M feedback resistors. The10k bleeder forces a settled UV fault.
    ref_open_max = (7 * 2.6 / (20e6 * 0.95) + 8 * 10e-9) * (edge("PROTECT_REF", "AGND") * 1.001)
    assert ref_open_max < 0.1
    diode_cases = 0

    def reachable(edges, start, target):
        seen = {start}
        while True:
            more = {b for a, b in edges if a in seen} - seen
            if not more:
                return target in seen
            seen.update(more)

    for mask in itertools.product((False, True), repeat=6):
        for i, name in enumerate(RAILS):
            nodes = [pins[f"Q{2 * i + j}"] for j in (1, 2)]
            if name == "5V_DIG":
                nodes += [pins["Q13"], pins["Q14"]]
            common = nodes[0]["1"]
            assert all(common == q["1"] for q in nodes)
            edges = [(q["1"], q["3"]) for q in nodes]  # NFET body diode:S->D.
            if mask[i]:
                edges.extend((q["3"], q["1"]) for q in nodes)
            for a, b in ((name + "_SRC", name), (name, name + "_SRC")):
                assert reachable(edges, a, b) == mask[i]
                diode_cases += 1
    # Independent failed/stuck gate states for the four digital FETs. A single
    # enabled side already conducts one way through the opposing body diode;
    # parallel parts are for voltage drop, not redundant fault isolation.
    digital_gate_cases = []
    digital_refs = ("Q11", "Q13", "Q12", "Q14")
    for mask in itertools.product((False, True), repeat=4):
        nodes = [pins[r] for r in digital_refs]
        edges = [(q["1"], q["3"]) for q in nodes]
        for q, on in zip(nodes, mask):
            if on:
                edges.append((q["3"], q["1"]))
        forward = reachable(edges, "5V_DIG_SRC", "5V_DIG")
        reverse = reachable(edges, "5V_DIG", "5V_DIG_SRC")
        assert forward == any(mask[:2]) and reverse == any(mask[2:])
        digital_gate_cases.append(
            dict(gates=dict(zip(digital_refs, mask)), forward_conducts=forward, reverse_conducts=reverse)
        )
    drop = []
    linear = {r["name"]: r for r in supply["linear_stages"]}
    buck = next(b for b in supply["bucks"] if b["name"] == "DIG")
    for name in RAILS:
        current = {"P19": 0.026, "N19": 0.026, "P12": 0.151, "N12": 0.151, "V5_REG": 0.251, "5V_DIG": 1.801}[
            name
        ]
        hot = 0.006 if name in RAILS[:4] else 0.003
        copper = 0.001 if name in RAILS[:4] else 0.0005
        parallel = 2 if name == "5V_DIG" else 1
        resistance = 2 * hot / parallel + copper
        delta = current * resistance
        src = buck if name == "5V_DIG" else linear[name]
        lo = src["minimum_dc_v"] if name == "5V_DIG" else src["minimum_magnitude_v"]
        hi = src["maximum_dc_v"] if name == "5V_DIG" else src["maximum_magnitude_v"]
        ripple = 0.010 if name == "5V_DIG" else 0
        target = {
            "P19": [18.81, 19.19],
            "N19": [18.81, 19.19],
            "P12": [11.88, 12.12],
            "N12": [11.88, 12.12],
            "V5_REG": [4.975, 5.025],
            "5V_DIG": [4.9, 5.1],
        }[name]
        assert lo - delta - ripple >= target[0] and hi + ripple <= target[1], (name, lo, hi, delta, target)
        drop.append(
            dict(
                name=name,
                maximum_current_screen_a=current,
                hot_resistance_each_fet_allocation_ohm=hot,
                parallel_devices_per_side=parallel,
                effective_switch_and_star_path_allocation_ohm=resistance,
                copper_star_path_allocation_ohm=copper,
                maximum_voltage_drop_v=delta,
                source_dc_v=[lo, hi],
                protected_dc_with_digital_ripple_v=[lo - delta - ripple, hi + ripple],
                target_at_integrated_board_star_v=target,
                includes_production_harness_or_contacts=False,
                extra_analog_ripple_and_load_step_proof=False,
            )
        )
    # Derive the interlock from actual exported logic pin nets.
    control = [r + "_OV_OK" for r in RAILS] + ["REF_LOW_OK", "REF_HIGH_OK", "POWER_RUN"]
    cases = 0
    gp = [(1, 2, 3), (4, 5, 6), (9, 10, 8), (12, 13, 11)]
    for bits in itertools.product((False, True), repeat=9):
        state = dict(zip(control, bits))
        for ref in ("U11", "U12"):
            for a, b, y in gp:
                state[pins[ref][str(y)]] = state[pins[ref][str(a)]] and state[pins[ref][str(b)]]
        assert state["ALL_RAILS_ALLOW"] == all(bits)
        for i in range(1, 7):
            assert pins[f"U{i}"]["3"] == RAILS[i - 1] + "_ALLOW"
        cases += 1
    assert 60 / (15000 * 0.99) < 0.006
    assert 5e-6 * 101000 < 0.7
    total_bulk_energy = sum(
        0.5
        * val(r)
        * 1.2
        * (
            {"P19": 19.19, "N19": 19.19, "P12": 12.12, "N12": 12.12, "V5_REG": 5.025, "5V_DIG": 5.1}[
                next(n for n in RAILS if n in pins[r].values())
            ]
        )
        ** 2
        for r in parts
        if r.startswith("C") and "electrolytic" in parts[r].findtext("value")
    )
    budget = input_report["load"]
    headroom = budget["efuse_allocated_limit_a"][0] - budget["combined_load_plus_ramp_a"]
    assert headroom > 0
    return dict(
        rail_thresholds=rows,
        threshold_corner_cases=sum(2 * r["corners_per_edge"] for r in rows),
        interlock_powered_boolean_cases=cases,
        source_sensing_does_not_disappear_when_switches_open=True,
        ideal_body_diode_direction_cases=diode_cases,
        independent_digital_gate_state_cases=digital_gate_cases,
        single_fet_fault_isolation_guaranteed=False,
        reference_window=dict(
            normal_corner_margin_min_v=min(reference_margins),
            settled_open_reference_max_v=ref_open_max,
            independent_precision_reference_redundancy=False,
            physical_startup_open_short_or_brownout_verified=False,
        ),
        gate_drive=dict(
            minimum_loaded_v=gate_min,
            maximum_loaded_v=gate_max,
            per_rail_loaded_gate_cases=gate_rows,
            digital_gate_charge_device_count_doubled=True,
            increased_gate_load_is_covered_by_100pf_timing_spec=False,
            manufacturer_turnoff_max_at_100pf_s=35e-6,
            manufacturer_gate_load_f=100e-12,
            actual_gate_charge_and_switch_timing_verified=False,
            receiver_missing_run_harness_max_v=5e-6 * 101000,
            driver_input_leakage_allocation_a=10e-6,
            driver_input_high_min_v=input_high,
            driver_input_low_max_v=input_low,
            missing_interlock_trace_max_v=10e-6 * 10100,
        ),
        normal_drop=drop,
        auxiliary=dict(
            driver_supply_max_at_nominal_10k_tt_a=6 * 0.0095,
            total_load_allocation_a=0.065,
            input_guard_reports_external_load_a=budget["e17_auxiliary_load_allocation_a"],
            aux_regulator_current_screen_a=budget["total_auxiliary_current_screen_a"],
            aux_regulator_dissipation_screen_w=budget["aux_regulator_normal_input_dissipation_allocation_w"],
            normal_current_plus_bus_ramp_margin_a=headroom,
            thermal_and_dynamic_load_verified=False,
        ),
        startup=dict(
            added_maximum_nominal_bulk_charge_energy_j=total_bulk_energy,
            ideal_minimum_extra_charging_s_at_remaining_headroom=total_bulk_energy / (headroom * 10.5 * 0.75),
            this_is_not_a_startup_upper_bound=True,
            load_current_inrush_or_stability_verified=False,
            depends_on_protected_rails_for_enable=False,
        ),
        transient=dict(
            all_allocated_single_rail_envelopes_pass=all(r["allocated_envelope_pass"] for r in rows),
            both_19v_rail_magnitude_sum_v=sum(
                r["conditional_peak_v"] for r in rows if r["name"].endswith("19")
            ),
            physical_rail_protection_verified=False,
            signal_backfeed_and_partial_power_verified=False,
            source_capacitor_fault_dump_bounded=False,
            manufacturer_switch_or_regulator_model_used=False,
        ),
        capacitor_limits=dict(
            minimum_uses_initial_20c_tolerance_only=True, cold_capacitance_esr_and_endurance_verified=False
        ),
        pcb_routed=False,
        enclosure_placement_complete=False,
    )


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--kicad-cli", required=True, type=Path)
    p.add_argument(
        "--footprints",
        type=Path,
        default=Path("/private/tmp/rmx-kicad/KiCad/KiCad.app/Contents/SharedSupport/footprints"),
    )
    args = p.parse_args()
    OUT.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="rmx-e17-") as temporary:
        temp = Path(temporary)
        env = os.environ.copy()
        env["KICAD_CONFIG_HOME"] = str(temp / "config")
        env["KICAD10_FOOTPRINT_DIR"] = str(args.footprints)
        env["FONTCONFIG_FILE"] = str(ROOT.parents[2] / "build-hardware/kicad-fonts.conf")

        def run(*a):
            r = subprocess.run([str(args.kicad_cli), *map(str, a)], env=env, text=True, capture_output=True)
            assert r.returncode == 0, (a, r.stdout, r.stderr)
            return r.stdout.strip()

        version = run("--version")
        sheet = ROOT / "rail_disconnect.kicad_sch"
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
        plan = json.loads((ROOT / "integration.json").read_text())
        assert plan["load_update_revision"] == "E21"
        assert plan["digital_parallel_fets"] == {"source_side": ["Q11", "Q13"], "load_side": ["Q12", "Q14"]}
        assert math.isclose(plan["digital_load_current_allocation_including_bleed_a"], 1.801)
        assert plan["source_analog"] == [pins["J1"][str(i)] for i in range(1, 7)]
        assert plan["protected_analog"] == [pins["J3"][str(i)] for i in range(1, 7)]
        assert plan["auxiliary_control"] == [pins["J5"][str(i)] for i in range(1, 4)]
        assert plan["auxiliary_current_allocation_a"] == 0.065 and not plan["physical_protection_verified"]
        external = {}
        interfaces = {}
        for name in (
            "power_supply",
            "input_protection",
            "rail_monitor",
            "adc_driver",
            "converter",
            "output_stage",
            "input_range",
            "dac_receiver",
            "sequenced_bypass",
        ):
            source = ROOT.parent / name / (name + ".kicad_sch")
            target = temp / (name + ".xml")
            run("sch", "export", "netlist", "--format", "kicadxml", "-o", target, source)
            external[name] = eda.netlist(target)
            _, n = external[name]
            if name == "power_supply":
                assert n["J2"] == pins["J1"] and n["J3"] == pins["J2"]
                assert n["R51"] == {"1": "DIG_FB_TRIM", "2": "DIG_FB"}
                assert n["R6"]["1"] == n["R49"]["1"] == "5V_DIG_SRC"
            if name == "input_protection":
                assert n["J6"] == pins["J5"]
            if name == "rail_monitor":
                assert n["J2"] == pins["J3"]
            if name == "adc_driver":
                assert [n["J3"][str(i)] for i in (1, 2, 3, 4)] == [pins["J3"][str(i)] for i in (4, 2, 5, 6)]
            if name == "converter":
                assert n["J4"]["1"] == "V5_REG"
            if name == "output_stage":
                assert [n["J4"][str(i)] for i in range(1, 6)] == [pins["J3"][str(i)] for i in range(1, 6)]
            if name in ("input_range", "dac_receiver"):
                assert n["J3"] == {"1": "P12", "2": "AGND", "3": "N12"}
            if name == "sequenced_bypass":
                assert n["J1"]["1"] == "5V"  # Protected5V_DIG alias retained in historical E11.
            interfaces[name] = dict(fresh_export=True, source_sha256=sha(source))
        for name in ("power_supply", "input_protection"):
            base = ROOT.parent / name
            report = json.loads((base / "generated/verification.json").read_text())
            assert report["native_erc_violations"] == 0
            for path, h in report["source_sha256"].items():
                assert sha(base / path) == h, (name, path)
        supply = json.loads((ROOT.parent / "power_supply/generated/electrical-screens.json").read_text())
        assert math.isclose(
            plan["digital_load_current_allocation_including_bleed_a"],
            supply["load_budget"]["provided_digital_budget_a"] + 0.001,
        )
        input_report = json.loads(
            (ROOT.parent / "input_protection/generated/electrical-screens.json").read_text()
        )
        screen = screens(parts, pins, supply, input_report)
        footprints = {}
        for ref, part in parts.items():
            identifier = part.findtext("footprint")
            lib, name = identifier.split(":")
            path = args.footprints / (lib + ".pretty") / (name + ".kicad_mod")
            assert set(pins[ref]) <= set(re.findall(r'\(pad\s+"([^"]+)"', path.read_text())), (
                ref,
                identifier,
            )
            footprints[identifier] = sha(path)
        grouping = (args.footprints / "Package_SON.pretty/VSONP-8-1EP_5x6_P1.27mm.kicad_mod").read_text()
        pads = re.findall(r'\(pad "([123])".*?\(at ([^ ]+) ([^)]+)\)', grouping, re.S)
        assert {p: sum(x[0] == p for x in pads) for p in ("1", "2", "3")} == {"1": 3, "2": 1, "3": 5}
        assert {(float(x), float(y)) for p, x, y in pads if p == "1"} == {
            (-2.8, -1.905),
            (-2.8, -0.635),
            (-2.8, 0.635),
        }
        assert [(float(x), float(y)) for p, x, y in pads if p == "2"] == [(-2.8, 1.905)]
        (OUT / "electrical-screens.json").write_text(json.dumps(screen, indent=2) + "\n")
        run("sch", "export", "svg", "--exclude-drawing-sheet", "-o", str(OUT) + os.sep, sheet)
        sources = [
            p
            for p in ROOT.iterdir()
            if p.is_file() and p.suffix not in (".pyc", ".prl", ".lck", ".kicad_prl")
        ]
        sources.append(ROOT.parent / "output_stage/verify.py")
        for name in ("power_supply", "input_protection"):
            sources.extend(
                ROOT.parent / name / "generated" / f for f in ("verification.json", "electrical-screens.json")
            )
        report = dict(
            revision="E17",
            load_update_revision="E21",
            checked_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            kicad_version=version,
            native_erc_violations=0,
            physical_components=len(parts),
            exact_exported_contracts=counts,
            threshold_corner_cases=screen["threshold_corner_cases"],
            powered_interlock_cases=screen["interlock_powered_boolean_cases"],
            ideal_body_diode_direction_cases=screen["ideal_body_diode_direction_cases"],
            protected_star_targets_preserved_under_allocations=True,
            independent_ov_only_interlock_schematic_implemented=True,
            rail_disconnect_schematic_implemented=True,
            manufacturer_timing_applies_to_actual_fets=False,
            physical_protection_verified=False,
            mosfet_functional_pad_grouping_checked=True,
            manufacturer_landpattern_fabrication_approval=False,
            pcb_routed=False,
            enclosure_placement_complete=False,
            interfaces=interfaces,
            footprint_library_sha256=footprints,
            source_sha256=source_hashes(ROOT, sorted(sources)),
        )
        (OUT / "verification.json").write_text(json.dumps(report, indent=2) + "\n")
    print(
        f"KiCad{version}: zero ERC;164 complete exported contracts;{screen['threshold_corner_cases']} threshold corners;512 interlock cases. Actual fault current/timing/stability/fit remain open."
    )


if __name__ == "__main__":
    main()
