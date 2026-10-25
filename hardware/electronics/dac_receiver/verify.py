#!/usr/bin/env python3
"""E08 native ERC, independent pin contract and loaded linear-circuit analysis.

Ideal and single-pole op-amp models are design screens, not semiconductor SPICE
or evidence of converter scale, phase margin, measured noise or fault safety.
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
import shutil
import subprocess
import tempfile
from pathlib import Path

from ..common.circuits import LU as LU
from ..common.reports import source_hashes
from ..output_stage import verify as e05

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "generated"

CONTRACT = {
    "U1": {
        "1": "IV_P_L",
        "2": "DAC_LP",
        "3": "BIAS_P_L",
        "4": "N12",
        "5": "BIAS_N_L",
        "6": "DAC_LN",
        "7": "IV_N_L",
        "8": "P12",
    },
    "U2": {
        "1": "IV_P_R",
        "2": "DAC_RP",
        "3": "BIAS_P_R",
        "4": "N12",
        "5": "BIAS_N_R",
        "6": "DAC_RN",
        "7": "IV_N_R",
        "8": "P12",
    },
    "U3": {
        "1": "CM_DRV_L",
        "2": "CM_SUM_L",
        "3": "AGND",
        "4": "N12",
        "5": "AGND",
        "6": "CM_SUM_R",
        "7": "CM_DRV_R",
        "8": "P12",
    },
    "U4": {
        "1": "RX_OUT_L",
        "2": "RX_NEG_L",
        "3": "RX_POS_L",
        "4": "N12",
        "5": "RX_POS_R",
        "6": "RX_NEG_R",
        "7": "RX_OUT_R",
        "8": "P12",
    },
    "U5": {
        "1": "BUF_OUT_L",
        "2": "BUF_OUT_L",
        "3": "BUF_IN_L",
        "4": "N12",
        "5": "BUF_IN_R",
        "6": "BUF_OUT_R",
        "7": "BUF_OUT_R",
        "8": "P12",
    },
    "J1": {"1": "DAC_LP", "2": "DAC_LN", "3": "AGND", "4": "DAC_RP", "5": "DAC_RN"},
    "J2": {"1": "RECV_L", "2": "AGND", "3": "RECV_R"},
    "J3": {"1": "P12", "2": "AGND", "3": "N12"},
}
EXPECTED = {}
for ci, ch in enumerate(("L", "R")):

    def n(s):
        return s + "_" + ch

    connections = [
        (f"DAC_{ch}P", n("IV_P")),
        (f"DAC_{ch}N", n("IV_N")),
        (n("CM_DRV"), n("BIAS_P")),
        (n("CM_DRV"), n("BIAS_N")),
        (n("IV_P"), n("CM_SUM")),
        (n("IV_N"), n("CM_SUM")),
        (n("CM_SUM"), n("CM_DRV")),
        (n("IV_P"), n("RX_NEG")),
        (n("IV_N"), n("RX_POS")),
        (n("RX_NEG"), n("RX_OUT")),
        (n("RX_POS"), "AGND"),
        (n("BUF_OUT"), n("RECV")),
    ]
    for j, (ends, value) in enumerate(
        zip(connections, [1800, 1800, 4.3, 4.3, 100000, 100000, 1200000, 499, 499, 499, 499, 33.2]), 1
    ):
        ref = f"R{ci * 12 + j}"
        CONTRACT[ref] = dict(zip(("1", "2"), ends))
        EXPECTED[ref] = value
    capends = [connections[i] for i in (0, 1, 6, 9, 10)]
    for j, (ends, value) in enumerate(zip(capends, [510e-12, 510e-12, 51e-12, 1e-9, 1e-9]), 1):
        ref = f"C{ci * 5 + j}"
        CONTRACT[ref] = dict(zip(("1", "2"), ends))
        EXPECTED[ref] = value
    for ref, ends, value in [
        (f"R{25 + ci}", (n("HP_NODE"), "AGND"), 33200),
        (f"R{27 + ci}", (n("HP_NODE"), n("BUF_IN")), 2740),
        (f"C{21 + ci}", (n("RX_OUT"), n("HP_NODE")), 2.2e-6),
    ]:
        CONTRACT[ref] = dict(zip(("1", "2"), ends))
        EXPECTED[ref] = value
for ci in range(4):
    for k, rail in enumerate(("P12", "N12")):
        ref = f"C{11 + 2 * ci + k}"
        CONTRACT[ref] = {"1": rail, "2": "AGND"}
        EXPECTED[ref] = 100e-9
for ref, rail, value in [
    ("C19", "P12", 10e-6),
    ("C20", "N12", 10e-6),
    ("C23", "P12", 100e-9),
    ("C24", "N12", 100e-9),
]:
    CONTRACT[ref] = {"1": rail, "2": "AGND"}
    EXPECTED[ref] = value


def number(value):
    token = value.split()[0]
    return float(token[:-1]) * 1e6 if token.endswith("M") else e05.number(value)


class Circuit:
    def __init__(
        self, parts, pins, ch, frequency, rdac=(390, 390), finite=False, overrides=None, load=100000, ft=40e6
    ):
        self.ch = ch
        self.frequency = frequency
        self.parts = parts
        self.pins = pins
        self.load = load
        ci = 0 if ch == "L" else 1
        overrides = overrides or {}
        self.values = {
            ref: number(c.findtext("value")) for ref, c in parts.items() if ref.startswith(("R", "C"))
        }
        self.values.update(overrides)
        refs = (
            [f"R{i}" for i in range(1 + 12 * ci, 13 + 12 * ci)]
            + [f"R{25 + ci}", f"R{27 + ci}"]
            + [f"C{i}" for i in range(1 + 5 * ci, 6 + 5 * ci)]
            + [f"C{21 + ci}"]
        )
        self.branches = []
        self.resistors = []
        for ref in refs:
            a, b = (pins[ref][p] for p in ("1", "2"))
            value = self.values[ref]
            self.branches.append(
                (a, b, 1 / value if ref.startswith("R") else 2j * math.pi * frequency * value)
            )
            if ref.startswith("R"):
                self.resistors.append((ref, a, b, value))
        self.branches.extend(
            [
                (f"DAC_{ch}P", "AGND", 1 / rdac[0]),
                (f"DAC_{ch}N", "AGND", 1 / rdac[1]),
                ("RECV_" + ch, "AGND", 1 / load),
            ]
        )
        self.resistors.append(("E05_INPUT_LOAD", "RECV_" + ch, "AGND", load))
        amp_iv = "U1" if ch == "L" else "U2"
        triplets = [("3", "2", "1"), ("5", "6", "7")]
        self.amps = [
            (amp_iv + "." + str(i + 1), *[pins[amp_iv][p] for p in triple])
            for i, triple in enumerate(triplets)
        ]
        self.amps.extend(
            (ref + "." + str(ci + 1), *[pins[ref][p] for p in triplets[ci]]) for ref in ("U3", "U4", "U5")
        )
        if finite:
            # Typical input impedances, not a worst-case transistor model.
            for ref, pos, neg, _ in self.amps:
                fet = ref.startswith("U5.")
                yc = (
                    (1 / 6e12 + 2j * math.pi * frequency * 1.9e-12)
                    if fet
                    else (1e-9 + 2j * math.pi * frequency * 2e-12)
                )
                yd = (
                    (1 / 100e6 + 2j * math.pi * frequency * 9.1e-12)
                    if fet
                    else (1 / 20000 + 2j * math.pi * frequency * 8e-12)
                )
                self.branches.extend([(pos, "AGND", yc), (neg, "AGND", yc), (pos, neg, yd)])
        self.nodes = sorted(
            (
                {n for a, b, _ in self.branches for n in (a, b)}
                | {n for _, p, m, o in self.amps for n in (p, m, o)}
            )
            - {"AGND"}
        )
        self.index = {n: i for i, n in enumerate(self.nodes)}
        self.count = len(self.nodes)
        self.size = self.count + len(self.amps)
        m = [[0j] * self.size for _ in range(self.size)]

        def add(row, col, value):
            if row in self.index and col in self.index:
                m[self.index[row]][self.index[col]] += value

        for a, b, y in self.branches:
            add(a, a, y)
            add(b, b, y)
            add(a, b, -y)
            add(b, a, -y)
        for i, (ref, pos, neg, out) in enumerate(self.amps):
            fet = ref.startswith("U5.")
            inverse_a = (
                (1 / 10 ** ((134 if fet else 110) / 20) + 1j * frequency / (ft * 0.5 if fet else ft))
                if finite
                else 0
            )
            row = self.count + i
            m[self.index[out]][row] += 1
            if pos in self.index:
                m[row][self.index[pos]] += 1
            if neg in self.index:
                m[row][self.index[neg]] -= 1
            m[row][self.index[out]] -= inverse_a
        self.lu = LU(m)

    def rhs(self, currents=(), offsets=None):
        b = [0j] * self.size
        for a, z, current in currents:
            if a in self.index:
                b[self.index[a]] += current
            if z in self.index:
                b[self.index[z]] -= current
        for i, (ref, *_) in enumerate(self.amps):
            b[self.count + i] = -(offsets or {}).get(ref, 0)
        return b

    def solve(self, idiff=0, icommon=0, dc_voltage=None, rdac=(390, 390), currents=(), offsets=None):
        currents = list(currents)
        currents.extend(
            [
                (
                    f"DAC_{self.ch}P",
                    "AGND",
                    idiff / 2 + icommon + (0 if dc_voltage is None else dc_voltage / rdac[0]),
                ),
                (
                    f"DAC_{self.ch}N",
                    "AGND",
                    -idiff / 2 + icommon + (0 if dc_voltage is None else dc_voltage / rdac[1]),
                ),
            ]
        )
        x = self.lu.solve(self.rhs(currents, offsets))
        return x

    def voltage(self, x, node):
        return x[self.index[node]] if node in self.index else 0j


def closed_form(v, f, rdac=(390, 390), ip=0.5, im=-0.5, load=100000):
    s = 2j * math.pi * f

    def z(r, c):
        return v[r] / (1 + s * v[r] * v[c])

    zp, zn, zc = z("R1", "C1"), z("R2", "C2"), z("R7", "C3")
    gp, gn = 1 + zp / rdac[0], 1 + zn / rdac[1]
    cm = zc * (zp * ip / v["R5"] + zn * im / v["R6"]) / (1 + zc * (gp / v["R5"] + gn / v["R6"]))
    vp, vn = gp * cm - zp * ip, gn * cm - zn * im
    zf, zs = z("R10", "C4"), z("R11", "C5")
    rx = (1 + zf / v["R8"]) * vn * zs / (v["R9"] + zs) - zf * vp / v["R8"]
    hp = 0 if f == 0 else s * v["C21"] * v["R25"] / (1 + s * v["C21"] * v["R25"])
    return rx * hp * load / (load + v["R12"])


def analysis(parts, pins, load):
    values = {ref: number(c.findtext("value")) for ref, c in parts.items() if ref.startswith(("R", "C"))}
    left = {
        r: values[r]
        for r in [*[f"R{i}" for i in range(1, 13)], "R25", "R27", *[f"C{i}" for i in range(1, 6)], "C21"]
    }
    assert all(values[f"R{i}"] == values[f"R{i + 12}"] for i in range(1, 13))
    assert all(values[f"C{i}"] == values[f"C{i + 5}"] for i in range(1, 6))
    assert (
        values["R25"] == values["R26"] and values["R27"] == values["R28"] and values["C21"] == values["C22"]
    )
    normalize = 2 / abs(closed_form(left, 1000, load=load))
    ac = []
    for ch in ("L", "R"):
        for rdac in [(390, 390), (195, 195), (390 * 0.85, 390 * 1.15), (195 * 1.15, 195 * 0.85)]:
            for f in (20, 1000, 20000):
                c = Circuit(parts, pins, ch, f, rdac=rdac, load=load)
                x = c.solve(idiff=normalize)
                actual = c.voltage(x, "RECV_" + ch)
                expected = closed_form(left, f, rdac=rdac, load=load) * normalize
                assert abs(actual - expected) < 1e-8, (ch, f, rdac, actual, expected)
                ac.append(
                    dict(
                        channel=ch,
                        frequency_hz=f,
                        dac_pin_shunts_ohm=rdac,
                        receiver_rms_v=abs(actual),
                        ideal_mna_vs_closed_form_error_v=abs(actual - expected),
                    )
                )
    # Both exported channels have the same actual numeric network. Enumerate all
    # 14 filter/gain/bias and independent DAC-shunt corners of that network once.
    tolerances = {
        "R1": 0.001,
        "R2": 0.001,
        "C1": 0.02,
        "C2": 0.02,
        "R8": 0.0001,
        "R9": 0.0001,
        "R10": 0.0001,
        "R11": 0.0001,
        "C4": 0.01,
        "C5": 0.01,
        "C21": 0.1,
        "R25": 0.001,
        "RDACP": 0.15,
        "RDACN": 0.15,
    }
    extrema = {f: [math.inf, -math.inf] for f in (20, 1000, 20000)}
    droop = [math.inf, -math.inf]
    for signs in itertools.product((-1, 1), repeat=len(tolerances)):
        v = dict(left)
        rd = [390, 390]
        for (ref, tol), sign in zip(tolerances.items(), signs):
            if ref == "RDACP":
                rd[0] *= 1 + sign * tol
            elif ref == "RDACN":
                rd[1] *= 1 + sign * tol
            else:
                v[ref] *= 1 + sign * tol
        gains = {f: abs(closed_form(v, f, rdac=rd, load=load)) * normalize for f in extrema}
        for f, gain in gains.items():
            extrema[f] = [min(extrema[f][0], gain), max(extrema[f][1], gain)]
        for f in (20, 20000):
            db = 20 * math.log10(gains[f] / gains[1000])
            droop = [min(droop[0], db), max(droop[1], db)]
    assert droop[0] > -0.1 and max(abs(20 * math.log10(v / 2)) for v in extrema[1000]) < 0.02, (
        droop,
        extrema,
    )
    finite = []
    for ch in ("L", "R"):
        for ft in (20e6, 40e6, 80e6):
            for f in (20, 1000, 20000):
                c = Circuit(parts, pins, ch, f, finite=True, load=load, ft=ft)
                x = c.solve(idiff=normalize)
                finite.append(
                    dict(
                        channel=ch,
                        frequency_hz=f,
                        assumed_unity_bandwidth_hz=ft,
                        receiver_rms_v=abs(c.voltage(x, "RECV_" + ch)),
                    )
                )
    # Steady DC is blocked upstream of the buffer even with strongly mismatched
    # modeled DAC legs. The buffer's own bias/offset and cap leakage remain.
    dc = []
    for ch in ("L", "R"):
        for base in (195, 390):
            for sp, sn in itertools.product((0.85, 1.15), repeat=2):
                rd = (base * sp, base * sn)
                for vcm in (0, 1.65):
                    c = Circuit(parts, pins, ch, 0, rdac=rd, finite=True, load=load)
                    x = c.solve(dc_voltage=vcm, rdac=rd)
                    assert abs(c.voltage(x, "RECV_" + ch)) < 1e-9
                    dc.append(
                        dict(
                            channel=ch,
                            dac_pin_shunts_ohm=rd,
                            assumed_raw_common_mode_v=vcm,
                            receiver_before_dc_block_v=c.voltage(x, "RX_OUT_" + ch).real,
                            output_after_dc_block_v=c.voltage(x, "RECV_" + ch).real,
                        )
                    )
    # Hot bias and leakage are explicit assembly/device qualification allocations,
    # not a guaranteed 125C limit extrapolated from the 25C bias table.
    ib, vos, leak = 100e-9, 1.2e-3, 100e-9
    steady_bound = (
        (ib * (values["R25"] + values["R27"]) * 1.001 + leak * values["R25"] * 1.001 + vos)
        * load
        / (load + values["R12"] * 0.999)
    )
    tau = values["C21"] * 1.1 * values["R25"] * 1.001
    max_step = 24 * 1.01
    allocation = 0.025
    minimum_blank = tau * math.log(max_step / (allocation - steady_bound))
    one_second_residual = max_step * math.exp(-1 / tau)
    assert steady_bound + one_second_residual < allocation and minimum_blank < 1
    limit_current = max_step / (values["R27"] * 0.999)
    assert limit_current < 0.01
    # Noise-density model, no converter-internal source. Factor once/frequency;
    # inject each physical resistor/amp noise source independently.
    frequencies = [20 * (1000 ** (i / 80)) for i in range(81)]
    integrals = {}
    previous = None
    for f in frequencies:
        c = Circuit(parts, pins, "L", f, finite=True, load=load)
        densities = {}

        def measure(name, rhs):
            x = c.lu.solve(rhs)
            densities[name] = abs(c.voltage(x, "RECV_L")) ** 2

        for ref, a, b, r in c.resistors:
            measure(ref, c.rhs([(a, b, math.sqrt(4 * 1.380649e-23 * 298.15 / r))]))
        for ref, pos, neg, out in c.amps:
            fet = ref.startswith("U5.")
            # A 1/f PSD plus 2.9nV white floor is normalized to the OPA1656 typical
            # 0.53uVrms 20Hz-20kHz figure; this is not a transistor noise model.
            flicker = (0.53e-6**2 - (2.9e-9) ** 2 * (20000 - 20)) / math.log(20000 / 20)
            en = math.sqrt((2.9e-9) ** 2 + flicker / f) if fet else 1.1e-9
            measure(ref + ".en", c.rhs(offsets={ref: en}))
            for tag, node in [("ip", pos), ("in", neg)]:
                measure(ref + "." + tag, c.rhs([(node, "AGND", 6e-15 if fet else 1.7e-12)]))
        if previous:
            pf, pd = previous
            for name, value in densities.items():
                integrals[name] = integrals.get(name, 0) + (f - pf) * (value + pd[name]) / 2
        previous = f, densities
    incremental = {f"R{i}" for i in range(8, 13)} | {"R25", "R27", "E05_INPUT_LOAD"}
    inc_power = sum(
        v for name, v in integrals.items() if name in incremental or name.startswith(("U4.", "U5."))
    )
    noise = dict(
        band_hz=[20, 20000],
        weighting="unweighted",
        temperature_k=298.15,
        frequency_points=len(frequencies),
        all_physical_analog_model_noise_uv=math.sqrt(sum(integrals.values())) * 1e6,
        receiver_dc_block_buffer_incremental_model_noise_uv=math.sqrt(inc_power) * 1e6,
        op_amp_models="OPA1612 flat 1.1nV/1.7pA densities; OPA1656 2.9nV floor plus 1/f normalized to 0.53uVrms typical, 6fA current density",
        contributions_uv={k: math.sqrt(v) * 1e6 for k, v in integrals.items()},
        excluded=[
            "DAC internal noise and active output-impedance noise",
            "OPA1612 1/f and resistor excess noise",
            "capacitor dielectric/leakage noise",
            "supplies, EMI, jitter, crosstalk and semiconductor distortion",
        ],
        interpretation="I/V and common-mode stages may overlap ESS EVM DNR figures; do not double-count or combine this unweighted estimate directly with A-weighted figures",
    )
    # Actual 1kHz full-scale currents, including I/V feedback and receiver load.
    c = Circuit(parts, pins, "L", 1000, finite=True, load=load)
    x = c.solve(idiff=normalize)
    current_screen = {ref: abs(x[c.count + i]) * math.sqrt(2) * 1000 for i, (ref, *_) in enumerate(c.amps)}
    assert max(current_screen.values()) < 15
    return dict(
        revision="E08",
        physical_components=len(parts),
        ideal_ac_cases=len(ac),
        ideal_ac=ac,
        dac_scale=dict(
            status="unresolved; current is normalized for circuit analysis, not inferred from the EVM 2Vrms table",
            differential_current_rms_a_for_2v_at_1khz=normalize,
            per_pin_signal_peak_a=normalize / math.sqrt(2),
            required_hardware_action="Measure raw DAC scale and obtain vendor impedance/DC conventions before fixing gain or calibration range",
        ),
        passive_tolerances=dict(
            cases=2 ** len(tolerances),
            scope="All 14 listed independent corners; numeric network equality verified in both exported channels",
            varied=tolerances,
            nominal_base_dac_shunt_ohm=390,
            receiver_rms_extrema_v=extrema,
            relative_endpoint_gain_extrema_db=droop,
            excluded="Common-mode feedback resistor/capacitor tolerance, supply, active-device and temperature spread; not a full hardware tolerance qualification",
        ),
        finite_gain_sensitivity=dict(
            cases=finite,
            model="Single pole: OPA1612 110dB, 20/40/80MHz; OPA1656 134dB, 10/20/40MHz; each has typical input impedances. No output impedance/slew/current limit",
            stable_hardware_verified=False,
        ),
        dc_block=dict(
            cases=dc,
            assumed_bias_current_a=ib,
            assumed_offset_v=vos,
            allowed_film_leakage_a=leak,
            output_dc_allocation_v=allocation,
            screened_steady_dc_bound_v=steady_bound,
            maximum_coupling_time_constant_s=tau,
            maximum_modeled_step_v=max_step,
            minimum_blank_to_dc_allocation_s=minimum_blank,
            required_stable_analog_qualification_s=1,
            one_second_residual_v=one_second_residual,
            input_current_limit_screen_a=limit_current,
            current_limiter_worst_initial_power_w=max_step**2 / (values["R27"] * 0.999),
            maximum_coupling_energy_j=0.5 * values["C21"] * 1.1 * max_step**2,
            limit="Current-limiting provision only; rail injection, brownout, raw DAC protection and power sequencing are not verified",
        ),
        analog_noise_screen=noise,
        audio_band_current_screen=dict(
            per_amp_peak_ma=current_screen,
            limit="Load/current estimate; OPA1612 2k swing/THD conditions do not qualify the heavier I/V load",
        ),
        quiescent_power_screen=dict(
            amplifier_units=10,
            rails_v=[12, -12],
            typical_total_w=(8 * 0.0036 + 2 * 0.0039) * 24,
            maximum_total_w=(8 * 0.0055 + 2 * 0.005) * 24,
            opa1612=dict(
                packages=4,
                maximum_a_per_unit=0.0055,
                maximum_quiescent_w_per_dual=2 * 24 * 0.0055,
                reference_soic_theta_ja_c_per_w=150,
                quiescent_temperature_rise_c=2 * 24 * 0.0055 * 150,
            ),
            opa1656=dict(
                packages=1,
                maximum_a_per_unit=0.005,
                maximum_quiescent_w_per_dual=2 * 24 * 0.005,
                reference_soic_theta_ja_c_per_w=119.9,
                quiescent_temperature_rise_c=2 * 24 * 0.005 * 119.9,
            ),
            excluded="Signal dissipation, actual PCB thermal paths and enclosed ambient; not thermal qualification",
        ),
        complete_converter=False,
        pcb_routed=False,
        physical_fit_verified=False,
        physical_audio_verified=False,
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kicad-cli", default="kicad-cli")
    parser.add_argument("--footprint-dir", type=Path)
    args = parser.parse_args()
    cli = Path(shutil.which(args.kicad_cli) or args.kicad_cli).resolve()
    fp = args.footprint_dir or cli.parents[1] / "SharedSupport/footprints"
    OUT.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="rmx-e08-") as tmp:
        tmp = Path(tmp)
        env = dict(os.environ, KICAD_CONFIG_HOME=str(tmp / "config"), KICAD10_FOOTPRINT_DIR=str(fp))
        if Path("/System/Library/Fonts").is_dir():
            (tmp / "cache").mkdir()
            font = tmp / "fonts.conf"
            font.write_text(
                '<?xml version="1.0"?><!DOCTYPE fontconfig SYSTEM "fonts.dtd"><fontconfig><dir>/System/Library/Fonts</dir><dir>/Library/Fonts</dir><cachedir>'
                + str(tmp / "cache")
                + "</cachedir></fontconfig>"
            )
            env["FONTCONFIG_FILE"] = str(font)

        def run(*command):
            r = subprocess.run([str(cli), *map(str, command)], capture_output=True, text=True, env=env)
            if r.returncode:
                raise RuntimeError(f"{command}: {r.returncode}\n{r.stdout}\n{r.stderr}")
            return r.stdout.strip()

        version = run("version")
        run(
            "sch",
            "erc",
            "--severity-all",
            "--exit-code-violations",
            "--format",
            "json",
            "-o",
            OUT / "erc.json",
            ROOT / "dac_receiver.kicad_sch",
        )
        assert not any(s["violations"] for s in json.loads((OUT / "erc.json").read_text())["sheets"])
        run(
            "sch",
            "export",
            "netlist",
            "--format",
            "kicadxml",
            "-o",
            OUT / "netlist.xml",
            ROOT / "dac_receiver.kicad_sch",
        )
        parts, pins = e05.netlist(OUT / "netlist.xml")
        assert pins == CONTRACT, (pins, CONTRACT)
        assert len(parts) == 60
        for ref, value in EXPECTED.items():
            assert math.isclose(number(parts[ref].findtext("value")), value, rel_tol=1e-12), (ref, value)
        for ref in ("U1", "U2", "U3", "U4"):
            assert parts[ref].findtext("value") == "OPA1612AID"
        assert parts["U5"].findtext("value") == "OPA1656ID"
        for ref in ("C21", "C22"):
            fields = {v.attrib["name"]: v.text for v in parts[ref].findall("fields/field")}
            assert fields["MPN"] == "MKS2C042201K00KSSD"
        other = ROOT.parent / "output_stage/output_stage.kicad_sch"
        run("sch", "export", "netlist", "--format", "kicadxml", "-o", tmp / "e05.xml", other)
        other_parts, other_pins = e05.netlist(tmp / "e05.xml")
        assert pins["J2"] == other_pins["J1"]
        loads = [number(other_parts[ref].findtext("value")) for ref in ("R17", "R18")]
        assert loads == [100000, 100000]
        results = analysis(parts, pins, loads[0])
        chain = []
        normalization = results["dac_scale"]["differential_current_rms_a_for_2v_at_1khz"]
        for ch in ("L", "R"):
            for send in (False, True):
                gains = {}
                for frequency in (20, 1000, 20000):
                    c = Circuit(parts, pins, ch, frequency, load=loads[0])
                    x = c.solve(idiff=normalization)
                    recv = c.voltage(x, "RECV_" + ch)
                    output = e05.ac_solve(other_parts, other_pins, frequency, send, ch)[ch] * recv
                    gains[frequency] = abs(output)
                    chain.append(
                        dict(
                            channel=ch,
                            mode="send_return" if send else "master",
                            frequency_hz=frequency,
                            receiver_rms_v=abs(recv),
                            line_output_rms_v=abs(output),
                            phase_degrees=math.degrees(cmath.phase(output)),
                        )
                    )
                for frequency in (20, 20000):
                    assert abs(20 * math.log10(gains[frequency] / gains[1000])) < 0.2
        downstream = e05.circuit_analysis(other_parts, other_pins)
        headroom = []
        for row in downstream["voltage_screen"]:
            dc = (
                results["dc_block"]["screened_steady_dc_bound_v"]
                + results["dc_block"]["one_second_residual_v"]
            )
            margin = row["screened_peak_margin_v"] - 0.025 * row["worst_feedback_tolerance_gain"]
            assert margin > 0
            headroom.append(
                dict(
                    mode=row["mode"],
                    channel=row["channel"],
                    receiver_dc_budget_v=0.025,
                    modeled_receiver_dc_plus_residual_v=dc,
                    remaining_peak_margin_with_full_dc_budget_v=margin,
                    caveat=row["caveat"],
                )
            )
        results["e08_e05_ideal_cascade"] = dict(
            cases=chain,
            headroom_screens=headroom,
            assumptions="E08 includes actual E05 R17/R18 loads; ideal E05 op-amp inputs have no further load. Normalize hypothetical DAC current to 2Vrms at 1kHz. No physical scale, noise, stability or clipping claim.",
        )
        (OUT / "circuit-analysis.json").write_text(json.dumps(results, indent=2) + "\n")
        footprints = {}
        for ref, c in parts.items():
            identifier = c.findtext("footprint")
            library, name = identifier.split(":")
            path = fp / (library + ".pretty") / (name + ".kicad_mod")
            text = path.read_text()
            pads = set(re.findall(r'\(pad\s+"([^"]+)"', text))
            assert set(pins[ref]) <= pads
            if ref in ("C21", "C22"):
                actual = re.findall(
                    r'\(pad\s+"([12])"\s+thru_hole\s+circle\s+\(at\s+([-0-9.]+)\s+([-0-9.]+)\)\s+\(size\s+[0-9.]+\s+[0-9.]+\)\s+\(drill\s+([0-9.]+)\)',
                    text,
                )
                assert actual == [("1", "0", "0", "0.8"), ("2", "5", "0", "0.8")], actual
            footprints[identifier] = hashlib.sha256(path.read_bytes()).hexdigest()
        run(
            "sch",
            "export",
            "svg",
            "--exclude-drawing-sheet",
            "-o",
            str(OUT) + os.sep,
            ROOT / "dac_receiver.kicad_sch",
        )
        files = [
            "generate.py",
            "verify.py",
            "dac_receiver.kicad_sch",
            "dac_receiver.kicad_pro",
            "RMX_E08.kicad_sym",
            "sym-lib-table",
            "fp-lib-table",
            "components.json",
            "bom.csv",
            "dependencies.json",
            "../output_stage/generate.py",
            "../output_stage/verify.py",
        ]
        report = dict(
            revision="E08",
            checked_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            kicad_version=version,
            physical_components=len(parts),
            native_erc_violations=0,
            exact_exported_pin_contract_matches=True,
            e05_interface_matches=True,
            e05_input_loads_ohm=loads,
            e05_schematic_sha256=hashlib.sha256(other.read_bytes()).hexdigest(),
            ideal_ac_cases=results["ideal_ac_cases"],
            passive_corner_cases=results["passive_tolerances"]["cases"],
            e08_e05_ideal_cascade_cases=len(chain),
            modeled_dc_cases=len(results["dc_block"]["cases"]),
            footprint_library_hashes=footprints,
            film_pad_pitch_mm=5,
            film_drill_mm=0.8,
            complete_converter=False,
            pcb_routed=False,
            assembled=False,
            physical_audio_verified=False,
            source_hashes=source_hashes(ROOT, files),
        )
        (OUT / "verification.json").write_text(json.dumps(report, indent=2) + "\n")
    print(
        f"E08 KiCad {version}: zero ERC; 60 exact component contracts, fresh E05 interface, {results['ideal_ac_cases']} AC cases and {results['passive_tolerances']['cases']} passive corners. Physical converter/PCB performance unverified."
    )


if __name__ == "__main__":
    main()
