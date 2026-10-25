#!/usr/bin/env python3
"""Native E10 ERC/interfaces and independent loaded preamplifier screens.

Linear and allocation checks are not transistor, surge, distortion or bench
evidence. This circuit does not implement the ADC driver or input precharge.
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

from ..common import circuits as shared
from ..common import footprints as relay
from ..common import netlists as eda
from ..common.reports import source_hashes

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "generated"

CONTRACT = {
    "U1": {
        "1": "BUF_OUT_L",
        "2": "GAIN_FB_L",
        "3": "BUF_IN_L",
        "4": "N12",
        "5": "BUF_IN_R",
        "6": "GAIN_FB_R",
        "7": "BUF_OUT_R",
        "8": "P12",
    },
    "K1": {
        "1": "5V",
        "8": "GAIN_LOW",
        "3": "RANGE_L",
        "2": "ATTN_L",
        "4": "PROC_IN_L",
        "6": "RANGE_R",
        "7": "ATTN_R",
        "5": "PROC_IN_R",
    },
    "J1": {"1": "PROC_IN_L", "2": "AGND", "3": "PROC_IN_R"},
    "J2": {"1": "PRE_OUT_L", "2": "AGND", "3": "PRE_OUT_R"},
    "J3": {"1": "P12", "2": "AGND", "3": "N12"},
    "J4": {"1": "5V", "2": "GAIN_LOW"},
}
EXPECTED = {}
for ci, ch in enumerate(("L", "R")):

    def n(s):
        return s + "_" + ch

    ends = [
        (n("PROC_IN"), n("ATTN")),
        (n("ATTN"), "AGND"),
        (n("RANGE"), n("HP_SRC")),
        (n("BUF_IN"), "AGND"),
        (n("GAIN_FB"), n("BUF_OUT")),
        (n("GAIN_FB"), "AGND"),
        (n("BUF_OUT"), n("PRE_OUT")),
    ]
    for i, (pair, value) in enumerate(zip(ends, [33200, 13700, 4990, 68000, 365, 1000, 33.2]), 1):
        ref = f"R{7 * ci + i}"
        CONTRACT[ref] = dict(zip(("1", "2"), pair))
        EXPECTED[ref] = value
    for i, pair, value in [(1, (n("HP_SRC"), n("BUF_IN")), 1e-6), (2, (n("BUF_IN"), "AGND"), 47e-12)]:
        ref = f"C{2 * ci + i}"
        CONTRACT[ref] = dict(zip(("1", "2"), pair))
        EXPECTED[ref] = value
for ref, rail, value in [
    ("C5", "P12", 100e-9),
    ("C6", "N12", 100e-9),
    ("C7", "P12", 10e-6),
    ("C8", "N12", 10e-6),
]:
    CONTRACT[ref] = {"1": rail, "2": "AGND"}
    EXPECTED[ref] = value


class Circuit:
    def __init__(self, parts, pins, ch, mode, f, source=100, load=100000, overrides=None, finite=False):
        self.ch = ch
        self.mode = mode
        self.f = f
        self.source = source
        self.load = load
        ci = 0 if ch == "L" else 1
        self.refs = [f"R{i}" for i in range(1 + ci * 7, 8 + ci * 7)] + [f"C{1 + ci * 2}", f"C{2 + ci * 2}"]
        self.values = {ref: eda.number(parts[ref].findtext("value")) for ref in self.refs}
        self.values.update(overrides or {})
        contact = ("3", "2", "4") if ch == "L" else ("6", "7", "5")
        common, nc, no = (pins["K1"][p] for p in contact)
        selected = nc if mode == "Master" else no
        self.alias = lambda node: selected if node == common else node
        self.branches = []
        self.resistors = []
        for ref in self.refs:
            a, b = (self.alias(pins[ref][p]) for p in ("1", "2"))
            value = self.values[ref]
            self.branches.append((a, b, 1 / value if ref.startswith("R") else 2j * math.pi * f * value))
            if ref.startswith("R"):
                self.resistors.append((ref, a, b, value))
        for ref, a, b, r in [
            ("SOURCE_R", "SOURCE", "PROC_IN_" + ch, source),
            ("DRIVER_LOAD", "PRE_OUT_" + ch, "AGND", load),
        ]:
            self.branches.append((a, b, 1 / r))
            self.resistors.append((ref, a, b, r))
        triple = ("3", "2", "1") if ch == "L" else ("5", "6", "7")
        self.pos, self.neg, self.out = (pins["U1"][p] for p in triple)
        if finite:
            self.branches.extend(
                [
                    (self.pos, "AGND", 1 / 6e12 + 2j * math.pi * f * 1.9e-12),
                    (self.pos, self.neg, 1 / 100e6 + 2j * math.pi * f * 9.1e-12),
                ]
            )
        self.nodes = sorted(
            ({n for a, b, y in self.branches for n in (a, b)} | {self.pos, self.neg, self.out}) - {"AGND"}
        )
        self.index = {n: i for i, n in enumerate(self.nodes)}
        self.size = len(self.nodes) + 2
        m = [[0j] * self.size for _ in range(self.size)]

        def add(a, b, y):
            if a in self.index and b in self.index:
                m[self.index[a]][self.index[b]] += y

        for a, b, y in self.branches:
            add(a, a, y)
            add(b, b, y)
            add(a, b, -y)
            add(b, a, -y)
        self.amp_row = len(self.nodes)
        self.source_row = self.amp_row + 1
        m[self.index[self.out]][self.amp_row] = 1
        m[self.amp_row][self.index[self.pos]] = 1
        m[self.amp_row][self.index[self.neg]] = -1
        if finite:
            m[self.amp_row][self.index[self.out]] = -(1 / 10 ** (134 / 20) + 1j * f / 20e6)
        m[self.index["SOURCE"]][self.source_row] = 1
        m[self.source_row][self.index["SOURCE"]] = 1
        self.lu = shared.LU(m)

    def solve(self, source=1, offset=0, currents=()):
        b = [0j] * self.size
        b[self.source_row] = source
        b[self.amp_row] = -offset
        for a, z, current in currents:
            a = self.alias(a)
            z = self.alias(z)
            if a in self.index:
                b[self.index[a]] += current
            if z in self.index:
                b[self.index[z]] -= current
        return self.lu.solve(b)

    def v(self, x, node):
        return 0j if node == "AGND" else x[self.index[self.alias(node)]]

    def output(self, x):
        return self.v(x, "PRE_OUT_" + self.ch)

    def impedance(self, x):
        return self.v(x, "PROC_IN_" + self.ch) / (-x[self.source_row])

    def closed_form(self):
        ci = 0 if self.ch == "L" else 1
        rt, rb, rp, rbias, rf, rg, ro = [self.values[f"R{i + 7 * ci}"] for i in range(1, 8)]
        c = self.values[f"C{1 + ci * 2}"]
        crf = self.values[f"C{2 + ci * 2}"]
        s = 2j * math.pi * self.f
        zi = 1 / (1 / rbias + s * crf)
        post = rp + 1 / (s * c) + zi
        if self.mode == "Master":
            low = 1 / (1 / rb + 1 / post)
            zin = rt + low
            transfer = low / (self.source + zin) * zi / post
        else:
            zin = 1 / (1 / (rt + rb) + 1 / post)
            transfer = zin / (self.source + zin) * zi / post
        return transfer * (1 + rf / rg) * self.load / (ro + self.load), zin


def noise(parts, pins, mode):
    k = 1.380649e-23
    temperature = 298.15
    f0 = 20
    f1 = 20000
    count = 81
    freqs = [f0 * (f1 / f0) ** (i / (count - 1)) for i in range(count)]
    white = (2.9e-9) ** 2
    flicker = ((0.53e-6) ** 2 - white * (f1 - f0)) / math.log(f1 / f0)
    contributions = {}
    previous = None
    for f in freqs:
        circuit = Circuit(parts, pins, "L", mode, f)
        density = {}
        for ref, a, b, r in circuit.resistors:
            h = circuit.output(circuit.solve(source=0, currents=[(a, b, 1)]))
            density[ref] = abs(h) ** 2 * 4 * k * temperature / r
        en = abs(circuit.output(circuit.solve(source=0, offset=1))) ** 2
        density["U1.en"] = en * (white + flicker / f)
        for suffix, node in [("ip", circuit.pos), ("in", circuit.neg)]:
            density["U1." + suffix] = (
                abs(circuit.output(circuit.solve(source=0, currents=[(node, "AGND", 1)]))) ** 2 * (6e-15) ** 2
            )
        if previous:
            oldf, old = previous
            for ref, value in density.items():
                contributions[ref] = contributions.get(ref, 0) + (value + old[ref]) * (f - oldf) / 2
        previous = f, density
    gain = abs(Circuit(parts, pins, "L", mode, 1000).closed_form()[0])
    own = sum(v for k, v in contributions.items() if k not in ("SOURCE_R", "DRIVER_LOAD"))
    return dict(
        own_output_referred_uv=math.sqrt(own) * 1e6,
        own_input_referred_uv=math.sqrt(own) / gain * 1e6,
        all_modeled_output_referred_uv=math.sqrt(sum(contributions.values())) * 1e6,
        contributions_output_uv={k: math.sqrt(v) * 1e6 for k, v in contributions.items()},
    )


def analyze(parts, pins):
    cases = []
    fullscale = {"Master": 0.775 * 10 ** (4 / 20) * 10, "SendReturn": math.sqrt(10)}
    for ch, mode, f, load in itertools.product(("L", "R"), fullscale, (20, 1000, 20000), (100000, 1000000)):
        circuit = Circuit(parts, pins, ch, mode, f, load=load)
        x = circuit.solve()
        h = circuit.output(x)
        formula, z = circuit.closed_form()
        assert abs(h - formula) < 1e-10 and abs(circuit.impedance(x) - z) < 1e-5
        assert abs(z) > 22000 and z.real > 22000
        cases.append(
            dict(
                channel=ch,
                mode=mode,
                frequency_hz=f,
                load_ohm=load,
                gain=abs(h),
                phase_deg=math.degrees(cmath.phase(h)),
                input_impedance_real_ohm=z.real,
                input_impedance_magnitude_ohm=abs(z),
                preamp_full_scale_rms_v=abs(h) * fullscale[mode],
            )
        )
    # Independent signs for all seven resistors, coupling C and RF C, per channel.
    # One-channel bounds apply independently to either stereo channel.
    corners = []
    worst_z = 1e99
    max_peak = 0
    max_input = 0
    for signs in itertools.product((-1, 1), repeat=9):
        overrides = {f"R{i + 1}": EXPECTED[f"R{i + 1}"] * (1 + signs[i] * 0.001) for i in range(7)}
        overrides.update(C1=EXPECTED["C1"] * (1 + signs[7] * 0.10), C2=EXPECTED["C2"] * (1 + signs[8] * 0.05))
        for mode in fullscale:
            responses = []
            for f in (20, 1000, 20000):
                c = Circuit(parts, pins, "L", mode, f, overrides=overrides)
                x = c.solve()
                h = abs(c.output(x))
                z = c.impedance(x)
                formula, _ = c.closed_form()
                assert abs(c.output(x) - formula) < 1e-10
                worst_z = min(worst_z, z.real, abs(z))
                responses.append(h)
                voltage = Circuit(parts, pins, "L", mode, f, source=1, overrides=overrides)
                vx = voltage.solve()
                max_peak = max(max_peak, abs(voltage.v(vx, "BUF_OUT_L")) * fullscale[mode] * math.sqrt(2))
                max_input = max(max_input, abs(voltage.v(vx, "BUF_IN_L")) * fullscale[mode] * math.sqrt(2))
            corners.append(
                dict(
                    mode=mode,
                    gain_1k=responses[1],
                    low_db=20 * math.log10(responses[0] / responses[1]),
                    high_db=20 * math.log10(responses[2] / responses[1]),
                )
            )
    assert worst_z > 22000
    # Assumed 1% regulated rails; 1.3V output reserve conservatively uses the
    # OPA1656 600Ohm open-loop test range, not a guaranteed swing specification.
    available = 12 * 0.99 - 1.3
    cm_limit = 12 * 0.99 - 2.25
    assert max_peak + 0.025 < available and max_input + 0.014 < cm_limit
    sensitivities = []
    for mode, source, load in itertools.product(fullscale, (1, 100, 1000), (100000, 1000000)):
        for f in (20, 1000, 20000):
            ideal = Circuit(parts, pins, "L", mode, f, source=source, load=load)
            finite = Circuit(parts, pins, "L", mode, f, source=source, load=load, finite=True)
            delta = 20 * math.log10(abs(finite.output(finite.solve()) / ideal.output(ideal.solve())))
            assert abs(delta) < 0.05
            sensitivities.append(
                dict(mode=mode, source_ohm=source, load_ohm=load, frequency_hz=f, finite_vs_ideal_db=delta)
            )
    # Cold/unpowered clamp-current screen for a conservative 48V polarity step.
    rp = 4990 * 0.999
    current = 48 / rp
    power = 48**2 / rp
    energy = 0.5 * 1.1e-6 * 48**2
    assert current < 0.010 and power < 1
    # Worst post-coupling time constant includes source<=1k, Master divider Rth,
    # all relevant resistor signs and +10% C. DC allocations are not measured.
    tau = 0
    for mode, st, sb, sp, sbias in itertools.product(fullscale, (-1, 1), (-1, 1), (-1, 1), (-1, 1)):
        rt = 33200 * (1 + st * 0.001)
        rb = 13700 * (1 + sb * 0.001)
        rth = 1 / (1 / (1000 + rt) + 1 / rb) if mode == "Master" else 1 / (1 / 1000 + 1 / (rt + rb))
        series = rth + 4990 * (1 + sp * 0.001)
        bias = 68000 * (1 + sbias * 0.001)
        cap = 1.1e-6
        rf_cap = 47e-12 * 1.05
        a = (series + bias) * cap + bias * rf_cap
        b = series * bias * cap * rf_cap
        tau = max(tau, (a + math.sqrt(a * a - 4 * b)) / 2)
    gain = 1 + 365 * 1.001 / (1000 * 0.999)
    dc = gain * ((100e-9 + 100e-9) * 68000 * 1.001 + 1.2e-3) + 100e-9 * 365 * 1.001
    residue = 48 * gain * math.exp(-1.2 / tau)
    assert dc + residue < 0.025
    dc_cases = []
    for ch, mode in itertools.product(("L", "R"), fullscale):
        c = Circuit(parts, pins, ch, mode, 0)
        x = c.solve(source=24)
        assert abs(c.output(x)) < 1e-10
        for sv, sib, sl, sn in itertools.product((-1, 1), repeat=4):
            x = c.solve(
                source=24,
                offset=sv * 1.2e-3,
                currents=[(c.pos, "AGND", sib * 100e-9 + sl * 100e-9), (c.neg, "AGND", sn * 100e-9)],
            )
            value = c.output(x).real
            assert abs(value) <= dc
            dc_cases.append(
                dict(
                    channel=ch,
                    mode=mode,
                    offset_sign=sv,
                    bias_sign=sib,
                    leakage_sign=sl,
                    negative_input_bias_sign=sn,
                    steady_preamp_output_v=value,
                )
            )
    bounds = {
        mode: dict(
            gain_1k_min=min(v["gain_1k"] for v in corners if v["mode"] == mode),
            gain_1k_max=max(v["gain_1k"] for v in corners if v["mode"] == mode),
            low_db_min=min(v["low_db"] for v in corners if v["mode"] == mode),
            high_db_min=min(v["high_db"] for v in corners if v["mode"] == mode),
        )
        for mode in fullscale
    }
    noise_report = {mode: noise(parts, pins, mode) for mode in fullscale}
    return dict(
        revision="E10",
        boundary="Single-ended PRE_OUT; not raw ADC input",
        ideal_ac_cases=len(cases),
        ideal_ac=cases,
        corner_cases=len(corners),
        corner_sign_variables=9,
        corner_frequency_solves=len(corners) * 3,
        additional_voltage_corner_solves=len(corners) * 3,
        corner_ac_source_ohm=100,
        corner_bounds=bounds,
        allocated_dc_cases=len(dc_cases),
        allocated_dc=dc_cases,
        minimum_screened_input_impedance_ohm=worst_z,
        voltage_screen=dict(
            rail_tolerance_fraction=0.01,
            output_reserve_v=1.3,
            source_ohm=1,
            available_peak_v=available,
            maximum_preamp_peak_v=max_peak,
            output_dc_allocation_v=0.025,
            remaining_peak_margin_v=available - max_peak - 0.025,
            input_cm_positive_limit_v=cm_limit,
            maximum_input_peak_v=max_input,
            bench_verified=False,
        ),
        finite_gain_sensitivity=dict(
            cases=len(sensitivities),
            results=sensitivities,
            model="single-pole134dB DC gain,20MHz unity bandwidth; typical input parasitics; no phase-margin/THD proof",
        ),
        current_limit_screen=dict(
            assumed_step_v=48,
            minimum_series_ohm=rp,
            maximum_initial_input_current_a=current,
            initial_resistor_power_w=power,
            maximum_capacitor_step_energy_j=energy,
            part_pulse_qualification=False,
            interpretation="OPA1656 10mA absolute input-current bound screen only; no ADC raw-pin, ESD/surge, reverse-power or assembled fault proof",
        ),
        input_precharge=dict(
            required_independent_interval_s=1.2,
            maximum_time_constant_s=tau,
            allocated_hot_input_bias_a=100e-9,
            allocated_film_leakage_a=100e-9,
            allocated_offset_v=1.2e-3,
            steady_preamp_dc_bound_v=dc,
            residual_48v_step_after_interval_v=residue,
            combined_bound_v=dc + residue,
            preamp_dc_allocation_v=0.025,
            independent_sequence_implemented=False,
            conflict="E02/E03 input-isolation and output-selection coils currently share BYPASS_LOW; E09 DAC timer before engagement does not provide this input precharge",
        ),
        analog_noise_screen=dict(
            band_hz=[20, 20000],
            weighting="unweighted",
            temperature_k=298.15,
            frequency_points=81,
            modes=noise_report,
            model="OPA1656 2.9nV white plus1/f normalized to0.53uVrms typical20..20k,6fA current; Johnson resistors",
            excluded=[
                "Source active-device noise",
                "ADC driver/reference/internal converter noise",
                "Rail/EMI/clock/crosstalk/THD",
                "Capacitor/resistor excess and dielectric/leakage noise",
            ],
            complete_system_snr_established=False,
        ),
        quiescent_power_screen=dict(
            dual_typ_at_nominal_rails_w=24 * 2 * 0.0039,
            dual_hot_max_at_nominal_rails_w=24 * 2 * 0.005,
            dual_hot_max_at_high_rails_w=24.24 * 2 * 0.005,
            signal_thermal_verified=False,
        ),
        adc_boundary_review=dict(
            source_numbered_page=176,
            figure=42,
            reference_output_series_ohm=536,
            reference_output_shunt_ohm=432,
            raw_adc_common_mode_requirement="VREF_BUF_ADC/2 (datasheet Table44)",
            illustrative_reference_v=3.3,
            illustrative_adc_common_mode_v=1.65,
            conditional_amplifier_common_mode_v=1.65 * (1 + 536 / 432),
            conditional_external_BiasD_v=2 * 1.65 * (1 + 536 / 432),
            dc_condition="Illustration assumes no net ADC DC current at its target common mode; does not establish the actual ADC DC input model or reference loading",
            balanced_low_frequency_differential_gains={
                name: 2 / (1 + 536 / (1 / (1 / 432 + 1 / r)))
                for name, r in [("260Ohm_per_pin", 260), ("260Ohm_differential", 130)]
            },
            status="Do not connect PRE_OUT directly to E09. Resolve raw-pin bias, AC/DC load models, protection and loaded driver rail/headroom before implementing the ADC driver.",
        ),
        adc_driver_implemented=False,
        adc_scale_calibrated=False,
        pcb_routed=False,
        enclosure_placement_complete=False,
        physical_audio_verified=False,
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kicad-cli", type=Path, required=True)
    parser.add_argument(
        "--footprints",
        type=Path,
        default=Path("/private/tmp/rmx-kicad/KiCad/KiCad.app/Contents/SharedSupport/footprints"),
    )
    args = parser.parse_args()
    OUT.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="rmx-e10-") as temp:
        temp = Path(temp)
        env = os.environ.copy()
        env["KICAD_CONFIG_HOME"] = str(temp / "config")
        env["KICAD10_FOOTPRINT_DIR"] = str(args.footprints)
        font = ROOT.parents[2] / "build-hardware/kicad-fonts.conf"
        if font.exists():
            env["FONTCONFIG_FILE"] = str(font)

        def run(*command):
            result = subprocess.run(
                [str(args.kicad_cli), *map(str, command)], capture_output=True, text=True, env=env
            )
            if result.returncode:
                raise RuntimeError(f"{command}\n{result.stdout}\n{result.stderr}")
            return result.stdout.strip()

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
            ROOT / "input_range.kicad_sch",
        )
        erc = json.loads((OUT / "erc.json").read_text())
        assert all(not s["violations"] for s in erc["sheets"])
        run(
            "sch",
            "export",
            "netlist",
            "--format",
            "kicadxml",
            "-o",
            OUT / "netlist.xml",
            ROOT / "input_range.kicad_sch",
        )
        parts, pins = eda.netlist(OUT / "netlist.xml")
        assert pins == CONTRACT, (pins, CONTRACT)
        assert len(parts) == 28
        assert (
            parts["U1"].findtext("value") == "OPA1656ID" and parts["K1"].findtext("value") == "G6K-2F-Y DC5"
        )
        for ref, value in EXPECTED.items():
            assert math.isclose(eda.number(parts[ref].findtext("value")), value, rel_tol=1e-12)
        external = {}
        for name in ("audio_bypass", "bypass", "output_stage"):
            sheet = ROOT.parent / name / (name + ".kicad_sch")
            target = temp / (name + ".xml")
            run("sch", "export", "netlist", "--format", "kicadxml", "-o", target, sheet)
            otherparts, other = eda.netlist(target)
            if name == "audio_bypass":
                assert pins["J1"] == {str(i): other["J3"][str(i)] for i in (1, 2, 3)}
                assert (
                    other["K1"]["8"] == other["K2"]["8"] == "BYPASS_LOW"
                )  # Detect actual sequencing conflict.
            else:
                assert pins["J4"] == other["J5" if name == "bypass" else "J3"]
            external[name] = dict(
                schematic_sha256=hashlib.sha256(sheet.read_bytes()).hexdigest(), pin_interface_matches=True
            )
        footprints = {}
        for ref, part in parts.items():
            identifier = part.findtext("footprint")
            library, name = identifier.split(":")
            path = args.footprints / (library + ".pretty") / (name + ".kicad_mod")
            text = path.read_text()
            pads = set(re.findall(r'\(pad\s+"([^"]+)"', text))
            assert set(pins[ref]) <= pads, (ref, identifier)
            footprints[identifier] = hashlib.sha256(path.read_bytes()).hexdigest()

        relay_review = relay.footprint_review(
            args.footprints / "Relay_SMD.pretty/Relay_DPDT_Omron_G6K-2F-Y.kicad_mod"
        )
        film_path = args.footprints / "Capacitor_THT.pretty/C_Rect_L7.2mm_W5.0mm_P5.00mm.kicad_mod"
        text = film_path.read_text()
        assert re.search(r"\(start -1\.1 -2\.5\)\s*\(end 6\.1 2\.5\)", text)
        pads = {}
        for n, x, y, drill in re.findall(
            r'\(pad "([12])" thru_hole circle\s*\(at ([-.0-9]+) ([-.0-9]+)\).*?\(drill ([-.0-9]+)\)',
            text,
            re.S,
        ):
            pads[n] = [float(x), float(y), float(drill)]
        assert pads == {"1": [0, 0, 0.75], "2": [5, 0, 0.75]}, pads
        analysis = analyze(parts, pins)
        plan = json.loads((ROOT / "integration.json").read_text())
        assert (
            plan["required_independent_input_precharge_s"]
            == analysis["input_precharge"]["required_independent_interval_s"]
        )
        assert (
            plan["minimum_driver_input_impedance_ohm"] == 100000
            and plan["qualified_line_source_maximum_ohm"] == 1000
        )
        assert plan["preamp_output_dc_allocation_v"] == analysis["input_precharge"]["preamp_dc_allocation_v"]
        for key in (
            "independent_input_precharge_implemented",
            "adc_driver_implemented",
            "adc_scale_calibrated",
            "pcb_routed",
            "enclosure_placement_complete",
            "physical_audio_verified",
        ):
            assert plan[key] is False
        (OUT / "circuit-analysis.json").write_text(json.dumps(analysis, indent=2) + "\n")
        run(
            "sch",
            "export",
            "svg",
            "--exclude-drawing-sheet",
            "-o",
            str(OUT) + os.sep,
            ROOT / "input_range.kicad_sch",
        )
        files = [
            "spec.py",
            "generate.py",
            "verify.py",
            "input_range.kicad_sch",
            "input_range.kicad_pro",
            "RMX_E10.kicad_sym",
            "sym-lib-table",
            "fp-lib-table",
            "components.json",
            "bom.csv",
            "dependencies.json",
            "integration.json",
            "../dac_receiver/verify.py",
            "../output_stage/verify.py",
            "../audio_bypass/verify.py",
        ]
        report = dict(
            revision="E10",
            checked_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            kicad_version=version,
            physical_components=28,
            native_erc_violations=0,
            exact_exported_pin_value_contract=True,
            external_interfaces=external,
            ideal_ac_cases=analysis["ideal_ac_cases"],
            corner_cases=analysis["corner_cases"],
            allocated_dc_cases=analysis["allocated_dc_cases"],
            corner_frequency_solves=analysis["corner_frequency_solves"],
            native_footprint_library_hashes=footprints,
            relay_land_pattern_review=relay_review,
            film_nominal_body_mm=[7.2, 5, 10],
            film_pads_and_drill_mm=pads,
            independent_input_precharge_implemented=False,
            adc_driver_implemented=False,
            adc_scale_calibrated=False,
            pcb_routed=False,
            enclosure_placement_complete=False,
            physical_audio_verified=False,
            source_hashes=source_hashes(ROOT, files),
        )
        (OUT / "verification.json").write_text(json.dumps(report, indent=2) + "\n")
    print(
        f"KiCad {version}: zero ERC;28 pin/value contracts;24 ideal AC /64 allocated DC cases;1024 mode/corner cases;fresh E02/E03/E05 interfaces. ADC driver and independent input precharge remain open."
    )


if __name__ == "__main__":
    main()
