#!/usr/bin/env python3
"""E14/E24 native ERC, independent topology and conditional supply screens.

E24 placement is checked separately. No switching/transient macromodel, routed
PCB, physical startup or protection proof is established here.
"""

import argparse
import cmath
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
from ..dac_receiver import verify as e08

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "generated"


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def number(s):
    m = re.match(r"([0-9.]+)([kMmuµnp]?)", s)
    assert m, s
    return (
        float(m[1])
        * {"": 1, "k": 1e3, "M": 1e6, "m": 1e-3, "u": 1e-6, "µ": 1e-6, "n": 1e-9, "p": 1e-12}[m[2]]
    )


def contract(parts, pins):
    expected = {}
    values = {}

    def pair(ref, a, b, value):
        expected[ref] = {"1": a, "2": b}
        values[ref] = value

    def ic(ref, value, nets):
        expected[ref] = {str(i): v for i, v in nets.items()}
        values[ref] = value

    def nc(ref, name, pin):
        return f"unconnected-({ref}-{name}-Pad{pin})"

    ic(
        "U1",
        "LT3471EDD#PBF",
        {
            1: "RAW_P_FB",
            2: "SW_REF_1V",
            3: "SW_REF_1V",
            4: "RAW_N_FB",
            5: "AGND",
            6: "RAW_N_SW",
            7: "RAW_N_SS",
            8: "VIN_PROTECTED",
            9: "RAW_P_SS",
            10: "RAW_P_SW",
            11: "AGND",
        },
    )
    ic(
        "U13",
        "LT3471EDD#PBF",
        {
            1: "LO_P_FB",
            2: "LO_REF_1V",
            3: "LO_REF_1V",
            4: "LO_N_FB",
            5: "AGND",
            6: "LO_N_SW",
            7: "LO_N_SS",
            8: "VIN_PROTECTED",
            9: "LO_P_SS",
            10: "LO_P_SW",
            11: "AGND",
        },
    )
    for ref, name in [("U2", "DIG"), ("U3", "PRE")]:
        ic(
            ref,
            "TPS62933FDRLR",
            {
                1: nc(ref, "RT", 1),
                2: "SUPPLY_ENABLE",
                3: "VIN_PROTECTED",
                4: "AGND",
                5: name + "_SW",
                6: name + "_BST",
                7: name + "_SS",
                8: name + "_FB",
            },
        )
    ic(
        "U4",
        "REF5025EIDR",
        {
            1: "5V_DIG",
            2: "5V_DIG",
            3: nc("U4", "TEMP", 3),
            4: "AGND",
            5: nc("U4", "NR", 5),
            6: "PREF_2V5",
            7: nc("U4", "NC", 7),
            8: nc("U4", "DNC", 8),
        },
    )
    ic(
        "U5",
        "OPA4192ID",
        {
            1: "P19_DRIVE",
            2: "P19_FB",
            3: "PREF_FILTER",
            4: "RAW_P22",
            5: "PREF_FILTER",
            6: "P12_FB",
            7: "P12_DRIVE",
            8: "V5_REG_DRIVE",
            9: "V5_REG_FB",
            10: "PREF_FILTER",
            11: "AGND",
            12: "AGND",
            13: "SPARE_OUT",
            14: "SPARE_OUT",
        },
    )
    ic(
        "U6",
        "OPA2192ID",
        {
            1: "N19_DRIVE",
            2: "N19_FB",
            3: "NREF_FILTER",
            4: "RAW_N22",
            5: "NREF_FILTER",
            6: "N12_FB",
            7: "N12_DRIVE",
            8: "AGND",
        },
    )
    for ref, name, source, control in [
        ("U7", "P19", "RAW_P22", "RAW_P22"),
        ("U8", "P12", "RAW_P17", "RAW_P17"),
        ("U9", "V5_REG", "V5_PRE", "VIN_PROTECTED"),
    ]:
        if name == "P12":
            ic(ref, "LT3080IQ#PBF", {1: nc(ref, "NC", 1), 2: name + "_SET", 3: name, 4: control, 5: source})
        else:
            ic(
                ref,
                "LT3080IMS8E#PBF",
                {
                    1: name,
                    2: name,
                    3: name,
                    4: name + "_SET",
                    5: control,
                    6: nc(ref, "NC", 6),
                    7: source,
                    8: source,
                    9: name,
                },
            )
    for ref, name, source in [("U10", "N19", "RAW_N22"), ("U11", "N12", "RAW_N17")]:
        ic(
            ref,
            "LT3090IDD#PBF",
            {
                1: name,
                2: name,
                3: "AGND",
                4: name + "_SET",
                5: "5V_DIG",
                6: nc(ref, "IMONN", 6),
                7: nc(ref, "IMONP", 7),
                8: source,
                9: source,
                10: source,
                11: source,
            },
        )
    ic(
        "U12",
        "LT1634AIS8-2.5#PBF",
        {
            **{i: nc("U12", "DNC", i) for i in (1, 2, 3, 7)},
            4: "NREF_2V5",
            5: "NREF_2V5",
            6: "AGND",
            8: nc("U12", "NC", 8),
        },
    )
    for ref, nets in [
        ("J1", ["VIN_PROTECTED", "AGND"]),
        ("J2", ["P19", "AGND", "N19", "P12", "N12", "V5_REG"]),
        ("J3", ["5V_DIG", "AGND"]),
        ("J4", ["RAW_P22", "AGND", "RAW_N22", "RAW_P17", "RAW_N17", "V5_PRE"]),
        ("J5", ["AGND", "POWER_READY"]),
    ]:
        ic(ref, "Header" + str(len(nets)), dict(enumerate(nets, 1)))
    for ref, a, k in [
        ("D1", "RAW_P_SW", "RAW_P22"),
        ("D2", "CUK_NODE", "AGND"),
        ("D3", "LO_P_SW", "RAW_P17"),
        ("D4", "LO_CUK_NODE", "AGND"),
    ]:
        pair(ref, k, a, "SS16-E3/61T")
    for i, (a, b, v) in enumerate(
        [
            ("VIN_PROTECTED", "RAW_P_SW", 33),
            ("VIN_PROTECTED", "RAW_N_SW", 68),
            ("CUK_NODE", "RAW_N22", 68),
            ("DIG_SW", "5V_DIG", 10),
            ("PRE_SW", "V5_PRE", 10),
            ("VIN_PROTECTED", "LO_P_SW", 33),
            ("VIN_PROTECTED", "LO_N_SW", 68),
            ("LO_CUK_NODE", "RAW_N17", 68),
        ],
        1,
    ):
        pair(
            f"L{i}",
            a,
            b,
            f"{v}uH 20% " + ({33: "SRP7050WA-330M", 68: "SRP1050WA-680M", 10: "SRP1050WA-100M"}[v]),
        )
    resistors = [
        ("RAW_P22", "RAW_P_RMID", 300000),
        ("RAW_P_RMID", "RAW_P_FB", 15000),
        ("RAW_P_FB", "AGND", 15000),
        ("SW_REF_1V", "RAW_N_FB", 15000),
        ("RAW_N_FB", "RAW_N22", 330000),
        ("5V_DIG", "RAW_P_SS", 4700),
        ("5V_DIG", "RAW_N_SS", 4700),
        ("POWER_READY", "SUPPLY_ENABLE", 10000),
        ("SUPPLY_ENABLE", "AGND", 22000),
        ("5V_DIG", "DIG_FB_TRIM", 10500),
        ("DIG_FB", "AGND", 2000),
        ("POWER_READY", "SUPPLY_ENABLE", 10000),
        ("SUPPLY_ENABLE", "AGND", 22000),
        ("V5_PRE", "PRE_RMID", 12400),
        ("PRE_RMID", "PRE_FB", 100),
        ("PRE_FB", "AGND", 2000),
        ("PREF_2V5", "PREF_FILTER", 1000),
        ("NREF_2V5", "RAW_N22", 100000),
        ("NREF_2V5", "NREF_FILTER", 1000),
    ]
    stages = [
        ("P19", (330000, 330000), 9090),
        ("P12", (200000, 180000), 5620),
        ("V5_REG", (100000,), 2210),
        ("N19", (330000, 330000), 9090),
        ("N12", (200000, 180000), 5620),
    ]
    precision = {1, 2, 3, 4, 5, 10, 11, 14, 15, 16}
    for name, terms, bleed in stages:
        start = len(resistors) + 1
        if len(terms) == 2:
            resistors.extend(
                [(name + "_SET", name + "_RMID", terms[0]), (name + "_RMID", name + "_FB", terms[1])]
            )
        else:
            resistors.append((name + "_SET", name + "_FB", terms[0]))
        resistors.extend(
            [(name + "_FB", "AGND", 100000), (name + "_DRIVE", name + "_SET", 6800), (name, "AGND", bleed)]
        )
        precision.update(range(start, len(resistors) - 1))
    for i, (a, b, v) in enumerate(resistors, 1):
        ref = f"R{i}"
        expected[ref] = {"1": a, "2": b}
        assert math.isclose(number(parts[ref].findtext("value")), v), ref
        assert ("0.01% 5ppm" in parts[ref].findtext("value")) == (i in precision), ref
    extra = [
        ("RAW_P17", "LO_P_FB", 240000),
        ("LO_P_FB", "AGND", 15000),
        ("LO_REF_1V", "LO_N_FB", 15000),
        ("LO_N_FB", "LO_N_RMID", 200000),
        ("LO_N_RMID", "RAW_N17", 54900),
        ("5V_DIG", "LO_P_SS", 4700),
        ("5V_DIG", "LO_N_SS", 4700),
    ]
    for i, (a, b, v) in enumerate(extra, 44):
        ref = f"R{i}"
        expected[ref] = {"1": a, "2": b}
        assert number(parts[ref].findtext("value")) == v
        assert ("0.01% 5ppm" in parts[ref].findtext("value")) == (i < 49), ref
    resistors.extend(extra)
    caps = [("RAW_N_SW", "CUK_NODE", "10uF 63V X7R")]
    for rail in ["VIN_PROTECTED", "RAW_P22", "RAW_N22"]:
        caps.extend([(rail, "AGND", "22uF 50V X7R")] * 2 + [(rail, "AGND", "100nF 50V X7R")])
    caps.append(("SW_REF_1V", "AGND", "100nF 16V X7R"))
    for rail, fb, ss in [("RAW_P22", "RAW_P_FB", "RAW_P_SS"), ("RAW_N22", "RAW_N_FB", "RAW_N_SS")]:
        caps.extend([(rail, fb, "68pF 50V C0G 5%"), (ss, "AGND", "330nF 16V X7R")])
    for name, out in [("DIG", "5V_DIG"), ("PRE", "V5_PRE")]:
        caps.extend(
            [
                (name + "_BST", name + "_SW", "100nF 16V X7R"),
                (name + "_SS", "AGND", "1uF 16V X7R" if name == "DIG" else "33nF 16V X7R"),
            ]
            + [(out, "AGND", "22uF 16V X7R")] * 2
            + [("VIN_PROTECTED", "AGND", "10uF 25V X7R")] * 2
            + [("VIN_PROTECTED", "AGND", "100nF 50V X7R")]
        )
    caps.extend(
        [
            ("5V_DIG", "AGND", "100nF 16V X7R"),
            ("PREF_2V5", "AGND", "2.2uF 16V X7R"),
            ("PREF_FILTER", "AGND", "1uF film 63V 10% MKS2C041001F00KSSD"),
            ("NREF_FILTER", "AGND", "1uF film 63V 10% MKS2C041001F00KSSD"),
        ]
    )
    for name, _, _ in stages:
        source = {"P19": "RAW_P22", "P12": "RAW_P17", "V5_REG": "V5_PRE", "N19": "RAW_N22", "N12": "RAW_N17"}[
            name
        ]
        caps.extend(
            [
                (name + "_DRIVE", name + "_FB", "47nF 50V C0G 5%"),
                (name + "_SET", "AGND", "100nF 50V X7R"),
                (source, "AGND", "10uF 50V X7R"),
                (name, "AGND", "22uF 50V X7R"),
                (name, "AGND", "100nF 50V X7R"),
            ]
        )
    for rail in ("RAW_P22", "RAW_N22"):
        caps.extend([(rail, "AGND", "100nF 50V X7R"), (rail, "AGND", "1uF 50V X7R")])
    caps.append(("LO_N_SW", "LO_CUK_NODE", "10uF 63V X7R"))
    for rail in ("RAW_P17", "RAW_N17"):
        caps.extend([(rail, "AGND", "22uF 50V X7R")] * 2 + [(rail, "AGND", "100nF 50V X7R")])
    caps.extend(
        [
            ("VIN_PROTECTED", "AGND", "22uF 50V X7R"),
            ("VIN_PROTECTED", "AGND", "100nF 50V X7R"),
            ("LO_REF_1V", "AGND", "100nF 16V X7R"),
        ]
    )
    for rail, fb, ss in [("RAW_P17", "LO_P_FB", "LO_P_SS"), ("RAW_N17", "LO_N_FB", "LO_N_SS")]:
        caps.extend([(rail, fb, "68pF 50V C0G 5%"), (ss, "AGND", "330nF 16V X7R")])
    for i, (a, b, v) in enumerate(caps, 1):
        pair(f"C{i}", a, b, v)
    pair("R51", "DIG_FB_TRIM", "DIG_FB", "10 0.01% 5ppm")
    rails = {"P19", "N19", "P12", "N12", "V5_REG", "5V_DIG"}
    expected = {
        ref: {p: n + "_SRC" if n in rails else n for p, n in nets.items()} for ref, nets in expected.items()
    }
    assert len(parts) == len(expected) == 157 and len(resistors) == 50 and len(caps) == 76
    for ref, net in expected.items():
        assert pins[ref] == net, (ref, pins[ref], net)
    for ref, v in values.items():
        assert parts[ref].findtext("value") == v, (ref, v)
    return dict(parts=157, resistors=51, capacitors=76, inductors=8, diodes=4, ics=13, headers=5)


def corners(parts, mapping):
    def value(ref):
        return number(parts[ref].findtext("value"))

    results = []
    count = 0
    for stage in mapping["stages"]:
        name = stage["name"]
        nom = abs(stage["nominal"])
        negative = stage["nominal"] < 0
        assert nom == {"P19": 19, "N19": 19, "P12": 12, "N12": 12, "V5_REG": 5}[name]
        rf = sum(value(r) for r in stage["top"])
        rg = value(stage["bottom"])
        iso = value(stage["isolation"])
        assert iso == 6800 and rg == 100000 and rf == {19: 660000, 12: 380000, 5: 100000}[nom]
        bounds = []
        drives = []
        # Correlated actual resistors, reference error, full-temperature offset/
        # bias allocations and conservative LDO additive error are independent.
        # Positive MSOP:3.5mV initial+1.3mV load+line/control reserve ->12mV.
        # Positive DD-PAK has6mV initial offset; allocate15mV total for12V.
        # Negative:2mV initial+2.5mV load+30uV/V set gain+line ->6mV total.
        ldo_error = 0.006 if negative else 0.012
        if name == "P12":
            ldo_error = 0.015  # DD-PAK offset maximum6mV instead of3.5mV
        # 5V uses a tighter actual control/input differential line screen.
        if name == "V5_REG":
            ldo_error = 0.010
        ref_error = 0.0035 if negative else 0.001
        for sr, st, sb, so, ibp, ibn, sl, iset in itertools.product((-1, 1), repeat=8):
            ref = 2.5 * (1 + sr * ref_error)
            rft = rf * (1 + st * 0.001)
            rgt = rg * (1 + sb * 0.001)
            setv = (ref + so * 350e-6 + ibp * 5e-9 * 1000) * (1 + rft / rgt) + ibn * 5e-9 * rft
            # Positive SET sources current; negative SET sinks it. Work in
            # magnitudes, then check worst drive capability in either direction.
            set_current = (51e-6 if negative else 10.2e-6) * (1 if iset > 0 else -1)
            drive = setv + (setv / (rft + rgt) + set_current) * iso * 1.01
            v = setv + sl * ldo_error
            bounds.append(v)
            drives.append(abs(drive))
            count += 1
        low, high = min(bounds), max(bounds)
        tol = 0.005 if name == "V5_REG" else 0.01
        assert low >= nom * (1 - tol) and high <= nom * (1 + tol), (name, low, high)
        assert max(drives) < 21.12 - 1.0, (name, max(drives))
        bleed = value(stage["bleed"])
        minimum = low / (bleed * 1.01)
        assert minimum > 0.001  # Both positive and negative are deliberately loaded.
        power = high * high / (bleed * 0.99)
        assert power < 0.125
        results.append(
            dict(
                name=name,
                corners=len(bounds),
                minimum_magnitude_v=low,
                maximum_magnitude_v=high,
                maximum_target_amplifier_drive_v=max(drives),
                ldo_total_error_allocation_v=ldo_error,
                reference_total_error_allocation=ref_error,
                minimum_bleed_current_a=minimum,
                maximum_bleed_power_w=power,
                specified_normal_fraction=tol,
            )
        )
    bucks = []
    for b in mapping["bucks"]:
        top = sum(value(r) for r in b["top"])
        bottom = value(b["bottom"])
        vals = []
        for vref, st, sb, ib in itertools.product((0.788, 0.812), (-1, 1), (-1, 1), (-0.15e-6, 0.15e-6)):
            vals.append(
                vref * (1 + top * (1 + st * 0.001) / (bottom * (1 + sb * 0.001)))
                + ib * top * (1 + st * 0.001)
            )
        low, high = min(vals), max(vals)
        if b["name"] == "DIG":
            assert low - 0.010 >= 4.9 and high + 0.010 <= 5.1, (low, high)
        else:
            assert low - 0.025 > 5.025 + 0.5
        bucks.append(
            dict(
                name=b["name"],
                allocated_junction_c=[0, 85],
                reference_v=[0.788, 0.812],
                corners=len(vals),
                minimum_dc_v=low,
                maximum_dc_v=high,
                extra_ripple_transient_reserve_v=0.010 if b["name"] == "DIG" else 0.025,
                extended_temperature_reference_v=[0.784, 0.816],
                physical_accuracy_ripple_thermal_verified=False,
            )
        )
    return dict(
        linear_stages=results,
        linear_corner_cases=count,
        bucks=bucks,
        allocations=dict(
            precision_resistor_total_fraction=0.001,
            opamp_full_error_v=350e-6,
            opamp_input_bias_a=5e-9,
            opamp_gain_line_load_reserve_included_in_offset=True,
            positive_reference_fraction=0.001,
            negative_reference_fraction=0.0035,
        ),
        manufacturer_macromodel_or_physical_proof=False,
    )


def power_screen(parts, mapping):
    def value(ref):
        return number(parts[ref].findtext("value"))

    pairs = []
    for name, nom, lo, hi, load, rp, rb, rn, rnr, positive_l, negative_l in [
        ("high", 22, 21.12, 22.88, 0.05, ["R1", "R2"], "R3", ["R5"], "R4", "L1", "L2"),
        ("low", 17, 16.32, 17.68, 0.20, ["R44"], "R45", ["R47", "R48"], "R46", "L6", "L7"),
    ]:
        rf = sum(value(r) for r in rp)
        rfn = sum(value(r) for r in rn)
        raw = []
        for vin, refsign, ofs, rbias, rt, bot in itertools.product(
            (10.5, 13.2), (-1, 1), (-0.003, 0.003), (-100e-9, 100e-9), (-1, 1), (-1, 1)
        ):
            rref = 1 + refsign * (0.013 + 0.0008 * abs(vin - 3) + 0.002 * 0.68)
            p = (rref + ofs) * (
                1 + rf * (1 + rt * 0.001) / (value(rb) * (1 + bot * 0.001))
            ) + rbias * rf * 1.001
            n = (
                rref * rfn * (1 + rt * 0.001) / (value(rnr) * (1 + bot * 0.001))
                + ofs * (1 + rfn * (1 + rt * 0.001) / (value(rnr) * (1 + bot * 0.001)))
                + rbias * rfn * 1.001
            )
            assert min(p, n) - 0.05 >= lo and max(p, n) + 0.05 <= hi, (name, p, n)
            raw.append((p, n))
        vin = 10.5
        eff = 0.75
        diode = 1.0
        duty = (hi + diode) / (vin + hi + diode)
        # Cuk switch current includes BOTH inductors, losses and both ripple
        # half-amplitudes. The0.9A data-sheet minimum is a25C conditional screen.
        input_current = hi * load / (vin * eff)
        ripple = vin * duty / (value(negative_l) * 0.8 * 1e6)
        peak = input_current + load + ripple
        assert duty < 0.86 and peak < 0.9, (name, peak)
        boost_duty = 1 - vin / (hi + diode)
        boost_peak = input_current + vin * boost_duty / (value(positive_l) * 0.8 * 1e6) / 2
        assert boost_peak < 0.9 and 1 - 13.2 / lo > 0.15
        switch = 13.2 + hi + diode + 3
        assert switch < 42
        pairs.append(
            dict(
                name=name,
                nominal_v=nom,
                load_allocation_each_a=load,
                setpoint_corners=len(raw),
                minimum_dc_magnitude_v=min(min(x) for x in raw),
                maximum_dc_magnitude_v=max(max(x) for x in raw),
                raw_envelope_v=[lo, hi],
                raw_ripple_reserve_peak_v=0.05,
                maximum_cuk_duty=duty,
                maximum_cuk_switch_peak_a=peak,
                maximum_boost_switch_peak_a=boost_peak,
                used_switch_current_limit_a=0.9,
                current_limit_temperature_guarantee=False,
                minimum_efficiency_allocation=eff,
                diode_forward_voltage_allocation_v=diode,
                switch_maximum_with_3v_ringing_allocation_v=switch,
                switch_rating_v=42,
            )
        )
    maximum_input_power = (
        sum(2 * r["raw_envelope_v"][1] * r["load_allocation_each_a"] / 0.75 for r in pairs)
        + (5.1 * 1.8 + 5.95 * 0.25) / 0.85
        + 13.2 * 0.030
    )
    assert maximum_input_power / 10.5 < 2.5
    currents = dict(
        positive_high=0.025 + 0.006 + 0.008,
        negative_high=0.025 + 0.005 + 0.004 + 0.00025,
        positive_low=0.150 + 0.030,
        negative_low=0.150 + 0.0225,
    )
    assert currents["positive_high"] < 0.05 and currents["negative_high"] < 0.05
    assert currents["positive_low"] < 0.20 and currents["negative_low"] < 0.20
    # Conditional digital ramp only: the protected bulk must already be joined
    # before the source rises. A late-closing E17 switch is a different event.
    css = value("C17")
    ss_min = css * 0.8 * 0.788 / 6.5e-6
    ss_max = css * 1.2 * 0.812 / 4.5e-6
    capacitance_allocation = 0.0065
    charging = capacitance_allocation * 5.1 / ss_min
    ripple = 5.1 * (1 - 5.1 / 13.2) / (value("L4") * 0.8 * 0.450e6)
    peak = 1.8 + charging + ripple / 2
    assert peak < 4.2, ("digital startup peak exceeds minimum high-side limit", peak)
    return dict(
        raw_pairs=pairs,
        raw_setpoint_corners=sum(r["setpoint_corners"] for r in pairs),
        raw_current_budgets_a=currents,
        maximum_allocated_input_power_w=maximum_input_power,
        maximum_allocated_input_current_a=maximum_input_power / 10.5,
        candidate_external_adapter_v=12,
        candidate_external_adapter_a=3,
        digital_startup=dict(
            soft_start_cap_f=css,
            effective_cap_fraction=[0.8, 1.2],
            ss_charge_current_a=[4.5e-6, 6.5e-6],
            conditional_ramp_time_s=[ss_min, ss_max],
            maximum_connected_capacitance_allocation_f=capacitance_allocation,
            maximum_digital_capacitor_charging_a=charging,
            maximum_extra_input_charging_a=charging * 5.1 / (10.5 * 0.85),
            maximum_inductor_ripple_a=ripple,
            maximum_conditional_inductor_peak_a=peak,
            minimum_high_side_limit_a=4.2,
            protected_bulk_preconnected_assumption=True,
            actual_preconnection_order_verified=False,
            late_switch_close_bounded=False,
            other_rail_charging_included=False,
            connected_capacitor_inventory_and_effective_bounds_closed=False,
            full_startup_current_or_stability_verified=False,
        ),
        target_source_short_current_a=22.88 / (6800 * 0.99),
        positive_set_absolute_current_a=0.010,
        negative_set_absolute_current_a=0.005,
        output_or_input_short_protection_complete=False,
        loop_compensation_verified=False,
        thermal_verified=False,
        input_efuse_reverse_ov_disconnect_implemented=False,
        downstream_ov_disconnect_implemented=False,
    )


def dropout_and_thermal(screen):
    stages = {r["name"]: r for r in screen["linear_stages"]}
    pre = screen["bucks"][1]
    rail = {n: (r["minimum_magnitude_v"], r["maximum_magnitude_v"]) for n, r in stages.items()}
    rail.update(
        RAW_P22=(21.12, 22.88),
        RAW_N22=(21.12, 22.88),
        RAW_P17=(16.32, 17.68),
        RAW_N17=(16.32, 17.68),
        V5_PRE=(pre["minimum_dc_v"] - 0.025, pre["maximum_dc_v"] + 0.025),
        VIN_PROTECTED=(10.5, 13.2),
    )
    rows = []
    for name, source, control, current, iq in [
        ("P19", "RAW_P22", "RAW_P22", 0.025, 0.006),
        ("P12", "RAW_P17", "RAW_P17", 0.15, 0.030),
        ("V5_REG", "V5_PRE", "VIN_PROTECTED", 0.25, 0.030),
        ("N19", "RAW_N22", None, 0.025, 0.005),
        ("N12", "RAW_N17", None, 0.15, 0.0225),
    ]:
        minimum = rail[source][0] - rail[name][1]
        negative = name.startswith("N")
        required = 0.45 if negative else 0.5
        assert minimum > required, (name, minimum)
        ctrl = rail[control][0] - rail[name][1] if control else None
        assert ctrl is None or ctrl > 1.6
        # Full-data-sheet control/IQ maxima, not typical interpolated currents.
        power = (rail[source][1] - rail[name][0]) * current
        power += (rail[source][1] if negative else rail[control][1] - rail[name][0]) * iq
        theta = 34 if negative else 30 if name == "P12" else 60
        rows.append(
            dict(
                name=name,
                minimum_input_headroom_v=minimum,
                required_input_headroom_v=required,
                minimum_control_headroom_v=ctrl,
                required_control_headroom_v=None if negative else 1.6,
                output_current_budget_including_bleed_a=current,
                control_or_ground_current_budget_a=iq,
                maximum_allocated_ic_power_w=power,
                example_board_theta_ja_c_per_w=theta,
                conditional_junction_at55c_local_ambient_c=55 + theta * power,
                thermal_layout_and_local_ambient_verified=False,
            )
        )
        assert 55 + theta * power < 125, (name, power)
    # 19V stages now feed only the master path;12V stages have separate raw rails.
    assert 0.012 + rail["P19"][1] / (9090 * 0.99) < 0.025
    assert 0.012 + rail["N19"][1] / (9090 * 0.99) < 0.025
    # References are independent. A short positive reference must not establish
    # a false healthy negative supply by sharing the monitor's own reference.
    shunt_min = (21.12 - 2.5 * 1.0035) / (100000 * 1.01)
    shunt_max = (22.88 - 2.5 * 0.9965) / (100000 * 0.99)
    assert shunt_min > 8e-6 and shunt_max < 0.002
    return dict(
        linear_regulators=rows,
        negative_reference_shunt_current_a=[shunt_min, shunt_max],
        negative_reference_total_fraction=0.0035,
        negative_reference_full_temp_fraction=0.00175,
        negative_reference_current_change_limit_v=0.003,
        negative_reference_aging_thermal_reserve_fraction=0.0005,
        positive_reference_total_fraction=0.001,
        unit_ambient_target_c=[0, 40],
        local_pcb_ambient_assumption_c=55,
        digital_buck_junction_must_remain_below_c=85,
        digital_buck_dissipation_allocation_w=0.90,
        required_digital_buck_theta_ja_at55c_max_c_per_w=(85 - 55) / 0.90,
        digital_thermal_allocation_verified=False,
        whole_unit_heat_dissipation_and_ventilation_verified=False,
    )


def target_loops(parts, mapping):
    # A two-pole hypothetical amplifier, not the OPA manufacturer's macromodel.
    # Riso/Cset remote feedback is bypassed locally by Ccomp at high frequency.
    def value(r):
        return number(parts[r].findtext("value"))

    cases = 0
    minimum = 180.0
    worst_peak = 0.0
    frequencies = [10 ** (-2 + i * 0.025) for i in range(441)]
    for st in mapping["stages"][:3]:
        rf = sum(value(r) for r in st["top"])
        rg = value(st["bottom"])
        iso = value(st["isolation"])
        cf = value(st["compensation"])
        for ri, ct, cc, a0, gb, second in itertools.product(
            (0.99, 1.01), (50e-9, 120e-9), (0.95, 1.05), (1e6, 1e7), (5e6, 15e6), (1.5, 3)
        ):
            previous = None
            crossings = []
            peak = 0
            for f in frequencies:
                s = 2j * math.pi * f
                gi = 1 / (iso * ri)
                gf = 1 / rf
                gg = 1 / rg
                yc = s * cf * cc
                aa = gi + s * ct + gf
                bb = gf + gg + yc
                det = aa * bb - gf * gf
                beta = (aa * yc + gf * gi) / det
                to_set = (gi * bb + gf * yc) / det
                amp = a0 / ((1 + s / (2 * math.pi * gb / a0)) * (1 + s / (2 * math.pi * gb * second)))
                loop = amp * beta
                gain = abs(loop)
                if previous is not None and previous >= 1 and gain < 1:
                    crossings.append(180 + math.degrees(cmath.phase(loop)))
                transfer = amp * to_set / (1 + loop)
                peak = max(peak, abs(transfer) / (1 + rf / rg))
                previous = gain
            assert len(crossings) == 1 and crossings[0] > 50, (st["name"], crossings)
            assert peak < 1.05, (st["name"], peak)
            minimum = min(minimum, *crossings)
            worst_peak = max(worst_peak, peak)
            cases += 1
    return dict(
        hypothetical_cases=cases,
        minimum_screened_phase_margin_deg=minimum,
        maximum_normalized_reference_transfer=worst_peak,
        gbw_allocation_hz=[5e6, 15e6],
        dc_open_loop_gain_allocation=[1e6, 1e7],
        second_pole_multiple_gbw=[1.5, 3],
        set_cap_effective_f=[50e-9, 120e-9],
        switcher_loops_included=False,
        ldo_internal_loop_included=False,
        opamp_manufacturer_model=False,
        physical_compensation_or_transient_proof=False,
    )


def audio_load(external):
    # Count actual native amplifier packages before applying manufacturer IQ
    # maxima. Do not size the rails using typical quiescent currents alone.
    counts = {}
    for name in ("output_stage", "dac_receiver", "input_range", "adc_driver"):
        for ref, p in external[name][0].items():
            if ref.startswith("U"):
                v = p.findtext("value")
                counts[v] = counts.get(v, 0) + 1
    for name, count in [("OPA1612AID", 5), ("OPA1656ID", 3), ("OPA4192ID", 1), ("OPA2992D", 1)]:
        assert counts[name] == count, (name, counts)
    quiescent = 5 * 2 * 0.0055 + 3 * 2 * 0.0050 + 4 * 0.0015
    assert math.isclose(quiescent, 0.091)

    parts, pins = external["dac_receiver"]
    record = ROOT.parent / "dac_receiver/generated/circuit-analysis.json"
    scale = json.loads(record.read_text())["dac_scale"]["differential_current_rms_a_for_2v_at_1khz"]
    maximum = 0
    cases = 0
    for r, dc, f in itertools.product((195, 390), (0, 1.65), (20, 1000, 20000)):
        total = 0
        for ch in ("L", "R"):
            rd = (r * 0.85, r * 1.15)
            ac = e08.Circuit(parts, pins, ch, f, rdac=rd, finite=True)
            ax = ac.solve(idiff=scale)
            steady = e08.Circuit(parts, pins, ch, 0, rdac=rd, finite=True)
            dx = steady.solve(dc_voltage=dc, rdac=rd)
            # The extra MNA variables are physical amplifier output currents.
            total += sum(
                abs(dx[steady.count + i]) + math.sqrt(2) * abs(ax[ac.count + i]) for i in range(len(ac.amps))
            )
        maximum = max(maximum, total)
        cases += 1
    bleed = 12.12 / (5620 * 0.99)
    extra = 0.010
    required = quiescent + maximum + bleed + extra
    assert required < 0.150, (required, counts)
    led_parts, led_pins = external["led_driver"]
    assert sum(p.findtext("value") == "TLC5947DAPR" for p in led_parts.values()) == 4
    for chip in range(4):
        assert number(led_parts[f"R{chip + 1}"].findtext("value")) == 16500
        assert all(led_pins[f"U{chip + 1}"][str(5 + i)] == f"LED_{chip * 24 + i:02d}" for i in range(24))
    digital = dict(
        seed_and_its_3v3_load_allocation_a=0.600,
        led_sink_ceiling_a=96 * 0.004,
        led_driver_logic_allocation_a=4 * 0.090,
        led_driver_misc_allocation_a=0.020,
        four_relay_coils_allocation_a=4 * 0.030,
        panel_and_sensor_reserve_a=0.080,
        other_reserve_a=0.010,
    )
    assert math.isclose(sum(digital.values()), 1.574) and sum(digital.values()) < 1.8
    return dict(
        actual_package_counts=counts,
        per_12v_rail_full_temperature_quiescent_a=quiescent,
        e08_hypothetical_current_cases=cases,
        e08_both_channel_sum_dc_plus_ac_peak_a=maximum,
        additional_non_e08_output_current_reserve_a=extra,
        own_bleed_max_a=bleed,
        required_per_12v_rail_allocated_a=required,
        provided_per_12v_rail_budget_a=0.150,
        e08_hypothetical_converter_scale=True,
        actual_load_current_verified=False,
        digital_budget=digital,
        digital_budget_total_a=sum(digital.values()),
        provided_digital_budget_a=1.8,
        e20_load_included=True,
        e20_low_current_icc_and_sink_bounds_physically_verified=False,
        led_3ma_current_setting_and_brightness_verified=False,
        seed_external_3v3_load_budget_closed=False,
        source_analysis_sha256=sha(record),
        complete_signal_overload_and_short_current_proof=False,
    )


def passive_selection(parts):
    """Candidate identity/rating screen; typical currents do not close qualification."""
    rows = {}
    for refs, mpn, inductance, dcr, irms, isat, requirement in [
        (("L1", "L6"), "SRP7050WA-330M", 33e-6, 0.1276, 4, 4.9, (0.2, 1.5, 3)),
        (("L2", "L3", "L7", "L8"), "SRP1050WA-680M", 68e-6, 0.150, 3.5, 4.8, (0.2, 1.5, 3)),
        (("L4", "L5"), "SRP1050WA-100M", 10e-6, 0.023, 9, 13, (0.1, 3, 6)),
    ]:
        assert dcr * 1.3 <= requirement[0] and irms >= requirement[1] and isat >= requirement[2]
        for ref in refs:
            value = parts[ref].findtext("value")
            assert value.endswith(mpn) and math.isclose(number(value), inductance)
            rows[ref] = dict(
                mpn=mpn,
                inductance_h=inductance,
                dcr_max_25c_ohm=dcr,
                irms_typ_25c_a=irms,
                isat_typ_25c_a=isat,
                hot_dcr_multiplier_allocation=1.3,
                hot_dcr_allocation_ohm=dcr * 1.3,
                current_bounds_guaranteed=False,
                bias_and_hot_inductance_verified=False,
                core_loss_and_temperature_verified=False,
            )
    for ref in ("C32", "C33"):
        assert parts[ref].findtext("value") == "1uF film 63V 10% MKS2C041001F00KSSD"
    return dict(
        revision="E24",
        inductors=rows,
        film_capacitors=dict(
            references=["C32", "C33"],
            mpn="MKS2C041001F00KSSD",
            capacitance_f=1e-6,
            nominal_v=63,
            tolerance=0.1,
            nominal_body_mm=[7.2, 5, 10],
            lead_pitch_mm=5,
            full_temperature_leakage_and_assembly_qualified=False,
        ),
        limits="Irms/Isat are typical25C values; Isat denotes30% inductance drop. The1.3 DCR multiplier is an unqualified temperature allocation. Existing loop/startup screens do not establish bias/thermal/EMI or physical performance.",
        physical_passive_qualification_complete=False,
    )


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--kicad-cli", type=Path, required=True)
    p.add_argument(
        "--footprints",
        type=Path,
        default=Path("/private/tmp/rmx-kicad/KiCad/KiCad.app/Contents/SharedSupport/footprints"),
    )
    args = p.parse_args()
    OUT.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="rmx-e14-") as temporary:
        temp = Path(temporary)
        env = os.environ.copy()
        env["KICAD_CONFIG_HOME"] = str(temp / "config")
        env["KICAD10_FOOTPRINT_DIR"] = str(args.footprints)
        env["FONTCONFIG_FILE"] = str(ROOT.parents[2] / "build-hardware/kicad-fonts.conf")

        def run(*args_):
            r = subprocess.run(
                [str(args.kicad_cli), *map(str, args_)], env=env, text=True, capture_output=True
            )
            assert r.returncode == 0, (args_, r.stdout, r.stderr)
            return r.stdout.strip()

        version = run("--version")
        sheet = ROOT / "power_supply.kicad_sch"
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
        mapping = json.loads((ROOT / "supply-map.json").read_text())
        screen = corners(parts, mapping)
        screen["power"] = power_screen(parts, mapping)
        screen["dropout_thermal"] = dropout_and_thermal(screen)
        screen["target_source_loops"] = target_loops(parts, mapping)
        selection = passive_selection(parts)
        (OUT / "part-selection.json").write_text(json.dumps(selection, indent=2) + "\n")
        interfaces = {}
        external = {}
        load_header = {p: n.removesuffix("_SRC") for p, n in pins["J2"].items()}
        for name in (
            "rail_monitor",
            "adc_driver",
            "converter",
            "output_stage",
            "input_range",
            "dac_receiver",
            "sequenced_bypass",
            "led_driver",
        ):
            source = ROOT.parent / name / (name + ".kicad_sch")
            target = temp / (name + ".xml")
            run("sch", "export", "netlist", "--format", "kicadxml", "-o", target, source)
            external[name] = eda.netlist(target)
            _, other = external[name]
            if name == "rail_monitor":
                assert other["J2"] == load_header
            if name == "adc_driver":
                assert [other["J3"][str(i)] for i in range(1, 5)] == [
                    load_header[str(i)] for i in (4, 2, 5, 6)
                ]
                assert other["U5"]["3"] == other["U6"]["3"] == "AGND"  # Pumps start before CHIP_EN.
            if name == "output_stage":
                assert [other["J4"][str(i)] for i in range(1, 6)] == [
                    load_header[str(i)] for i in range(1, 6)
                ]
            if name in ("input_range", "dac_receiver"):
                assert [other["J3"][str(i)] for i in (1, 2, 3)] == [load_header[str(i)] for i in (4, 2, 5)]
            if name == "converter":
                assert [other["J4"][str(i)] for i in (1, 2)] == [load_header[str(i)] for i in (6, 2)]
            if name == "sequenced_bypass":
                assert other["J1"] == {"1": "5V", "2": "AGND", "3": "3V3"}
            interfaces[name] = dict(
                fresh_export=True,
                source_sha256=sha(source),
                via="Required E17 disconnect stage; protected-load names checked",
            )
        screen["load_budget"] = audio_load(external)
        plan = json.loads((ROOT / "integration.json").read_text())
        assert plan["load_update_revision"] == "E21" and plan["e20_led_driver_included"]
        assert math.isclose(plan["digital_soft_start_cap_f"], number(parts["C17"].findtext("value")))
        assert plan["normal_targets_v"]["P19"] == [18.81, 19.19]
        assert plan["raw_generation_implemented"] and not plan["overvoltage_disconnect_implemented"]
        assert plan["input"]["normal_v"] == [10.5, 13.2]
        assert plan["output_header"] == [pins["J2"][str(i)] for i in range(1, 7)]
        assert plan["digital_header"] == [pins["J3"][str(i)] for i in (1, 2)]
        assert math.isclose(plan["digital_source_nominal_v"], 5.004)
        assert plan["raw_rails_v"] == dict(
            RAW_P22=[21.12, 22.88], RAW_N22=[-22.88, -21.12], RAW_P17=[16.32, 17.68], RAW_N17=[-17.68, -16.32]
        )
        assert plan["current_allocations_a"] == dict(
            P19=0.025,
            N19=0.025,
            P12=0.150,
            N12=0.150,
            V5_REG=0.25,
            RAW_P22=0.05,
            RAW_N22=0.05,
            RAW_P17=0.20,
            RAW_N17=0.20,
            **{"5V_DIG": 1.8},
        )
        screen["startup_dependency_topology"] = dict(
            buck_enable_from="E15 POWER_READY via J5",
            missing_guard_harness_disables_bucks=True,
            raw_enable_from="5V_DIG_SRC",
            reference_from=["5V_DIG_SRC", "RAW_N22"],
            negative_bias_pumps_enabled_before_codec=True,
            depends_on_chip_en=False,
            physical_startup_timing_verified=False,
        )
        footprints = {}
        for ref, part in parts.items():
            identifier = part.findtext("footprint")
            lib, name = identifier.split(":")
            path = (
                (ROOT if lib == "RMX_Power" else args.footprints) / (lib + ".pretty") / (name + ".kicad_mod")
            )
            assert set(pins[ref]) <= set(re.findall(r'\(pad\s+"([^"]+)"', path.read_text())), (
                ref,
                identifier,
            )
            footprints[identifier] = sha(path)
        (OUT / "electrical-screens.json").write_text(json.dumps(screen, indent=2) + "\n")
        run("sch", "export", "svg", "--exclude-drawing-sheet", "-o", str(OUT) + os.sep, sheet)
        sources = [
            p
            for p in ROOT.iterdir()
            if p.is_file() and p.suffix not in (".pyc", ".prl", ".kicad_prl", ".lck")
        ]
        sources.extend(
            [
                ROOT.parent / "output_stage/verify.py",
                ROOT.parent / "dac_receiver/verify.py",
                ROOT.parent / "dac_receiver/generated/circuit-analysis.json",
            ]
        )
        sources.extend(ROOT.parent / name / (name + ".kicad_sch") for name in external)
        sources.extend(ROOT.glob("RMX_Power.pretty/*.kicad_mod"))
        sources.append(OUT / "part-selection.json")
        placement_path = OUT / "placement-verification.json"
        if placement_path.exists():
            placement = json.loads(placement_path.read_text())
            assert placement["revision"] == "E24" and placement["pcb_routed"] is False
            assert placement["nonrouting_drc_violations"] == placement["schematic_parity_issues"] == 0
            for path, digest in placement["source_sha256"].items():
                assert sha(ROOT / path) == digest, ("Rerun power_supply.check_placement", path)
            sources.append(placement_path)
        report = dict(
            revision="E14",
            load_update_revision="E21",
            checked_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            kicad_version=version,
            native_erc_violations=0,
            physical_components=len(parts),
            exact_exported_contracts=counts,
            linear_corner_cases=screen["linear_corner_cases"],
            raw_setpoint_corners=screen["power"]["raw_setpoint_corners"],
            interfaces=interfaces,
            footprint_library_sha256=footprints,
            raw_generation_schematic_implemented=True,
            precision_linear_generation_schematic_implemented=True,
            input_protection_implemented=False,
            input_protection_scope="Separate E15 sheet required at J1/J5; no protection on E14 sheet",
            guarded_enable_receiving_interface_implemented=True,
            source_outputs_separated_from_protected_rails=True,
            digital_source_nominal_v=5.004,
            downstream_overvoltage_disconnect_implemented=False,
            pcb_routed=False,
            pcb_placement_revision="E24" if placement_path.exists() else None,
            enclosure_placement_complete=False,
            physical_power_audio_verified=False,
            source_sha256=source_hashes(ROOT, sorted(sources)),
        )
        (OUT / "verification.json").write_text(json.dumps(report, indent=2) + "\n")
    print(
        f"KiCad{version}: zero ERC;157 exact component contracts;{screen['linear_corner_cases']} allocated linear corners; raw/buck/current/dropout interfaces checked. Physical power/protection/stability open."
    )


if __name__ == "__main__":
    main()
