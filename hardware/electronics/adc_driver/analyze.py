"""E12 exported-netlist linear model; not a transistor or codec switching model."""

import itertools
import math
from pathlib import Path

from ..common import circuits as shared
from ..common.netlists import number as component_number

ROOT = Path(__file__).resolve().parent


def number(value):
    token = value.split()[0]
    return float(token[:-1]) if token.endswith("R") else component_number(value)


class Circuit:
    def __init__(
        self,
        parts,
        pins,
        ch="L",
        f=1000,
        load="per_pin_ground",
        load_scale=(1, 1),
        overrides=None,
        finite=False,
        ft=135e6,
        second_pole=300e6,
        ro=20,
    ):
        self.ch = ch
        self.f = f
        self.pins = pins
        self.finite = finite
        ci = 0 if ch == "L" else 1
        self.index_channel = ci
        values = {r: number(c.findtext("value")) for r, c in parts.items() if r.startswith(("R", "C"))}
        values.update(overrides or {})
        self.values = values
        self.branches = []
        self.resistors = []
        for ref in [f"R{i + 16 * ci}" for i in range(1, 17)] + [f"C{i + 14 * ci}" for i in range(1, 15)]:
            a, b = (pins[ref][p] for p in ("1", "2"))
            # Pump, supply and PD networks are checked separately, not part of
            # this powered audio/reference model.
            if ref in [f"R{ci * 16 + i}" for i in (14, 15, 16)] or ref in [
                f"C{ci * 14 + i}" for i in range(8, 15)
            ]:
                continue
            value = values[ref]
            y = 1 / value if ref.startswith("R") else 2j * math.pi * f * value
            self.branches.append((a, b, y))
            if ref.startswith("R"):
                self.resistors.append((ref, a, b, value))
        self.pre = "PRE_OUT_" + ch
        self.p = "ADC_" + ch + "P"
        self.n = "ADC_" + ch + "N"
        self.ref = "REF_ADC" + str(ci + 1)
        self.branches.append(("SOURCE", self.pre, 1 / 33.2))
        self.resistors.append(("E10_SOURCE_R", "SOURCE", self.pre, 33.2))
        self.branches.append(
            ("VOCM_" + ch, "AGND", 2j * math.pi * f * 20e-12)
        )  # reverse-biased clamp-cap allocation
        if load == "differential":
            self.branches.append((self.p, self.n, 1 / (260 * load_scale[0])))
        else:
            ret = "ADC_INTERNAL_HALF" if load == "per_pin_reference" else "AGND"
            for node, scale in zip((self.p, self.n), load_scale):
                self.branches.append((node, ret, 1 / (260 * scale)))
        # Single-ended voltage-output amplifiers, actual package pins.
        up = pins["U3"]
        quad = pins["U4"]
        bp, bn, bo = ("3", "2", "1") if ci == 0 else ("5", "6", "7")
        rp, rn, reo = ("3", "2", "1") if ci == 0 else ("10", "9", "8")
        sp, sn, so = ("5", "6", "7") if ci == 0 else ("12", "13", "14")
        self.amps = [
            ("buffer", up[bp], up[bn], up[bo], 20e6),
            ("reference", quad[rp], quad[rn], quad[reo], 10e6),
            ("servo", quad[sp], quad[sn], quad[so], 10e6),
        ]
        fd = pins["U" + str(ci + 1)]
        self.fp = fd["8"]
        self.fn = fd["1"]
        self.op = fd["4"]
        self.on = fd["5"]
        self.cm = fd["2"]
        if finite:
            self.branches.extend([("FDIP", self.op, 1 / ro), ("FDIN", self.on, 1 / ro)])
            ip, on = "FDIP", "FDIN"
        else:
            ip, on = self.op, self.on
        self.internal_p = ip
        self.internal_n = on
        self.sources = ["SOURCE", self.ref, "ADC_INTERNAL_HALF"]
        nodes = {n for a, b, y in self.branches for n in (a, b)} | set(self.sources)
        nodes.update([self.fp, self.fn, self.op, self.on, self.cm, ip, on])
        for role, a, b, o, ft_amp in self.amps:
            nodes.update([a, b, o])
        self.nodes = sorted(nodes - {"AGND"})
        self.idx = {n: i for i, n in enumerate(self.nodes)}
        n = len(self.nodes)
        count = len(self.amps) + 2 + len(self.sources)
        self.size = n + count
        m = [[0j] * self.size for _ in range(self.size)]

        def add(row, node, value):
            if node != "AGND":
                m[row][self.idx[node]] += value

        for a, b, y in self.branches:
            if a != "AGND":
                add(self.idx[a], a, y)
                add(self.idx[a], b, -y)
            if b != "AGND":
                add(self.idx[b], b, y)
                add(self.idx[b], a, -y)
        self.rows = {}
        for i, (role, a, b, o, ft_amp) in enumerate(self.amps):
            row = n + i
            self.rows[role] = row
            add(self.idx[o], o, 0)
            m[self.idx[o]][row] = 1
            add(row, a, 1)
            add(row, b, -1)
            if finite:
                add(row, o, -(1 / 10 ** (120 / 20) + 1j * f / ft_amp))
        row = n + len(self.amps)
        self.rows["fda"] = row
        self.rows["cm"] = row + 1
        m[self.idx[ip]][row] = 1
        m[self.idx[on]][row + 1] = 1
        add(row, self.fp, 1)
        add(row, self.fn, -1)
        inv_a = (1 / 10 ** (125 / 20) + 1j * f / ft) * (1 + 1j * f / second_pole) if finite else 0
        add(row, ip, -inv_a)
        add(row, on, inv_a)
        # Internal common-mode loop sees amplifier output terminals, not raw ADC
        # pins. The slow external servo closes the remaining DC drop/error.
        add(row + 1, self.cm, 1)
        add(row + 1, self.op, -0.5)
        add(row + 1, self.on, -0.5)
        if finite:
            inv_cm = 1 / 1e5 + 1j * f / 40e6
            add(row + 1, ip, -0.5 * inv_cm)
            add(row + 1, on, -0.5 * inv_cm)
        self.source_rows = {}
        for i, node in enumerate(self.sources):
            r = row + 2 + i
            self.source_rows[node] = r
            m[self.idx[node]][r] = 1
            add(r, node, 1)
        self.lu = shared.LU(m)

    def solve(self, source=1, reference=0, offsets=None, currents=()):
        b = [0j] * self.size
        b[self.source_rows["SOURCE"]] = source
        b[self.source_rows[self.ref]] = reference
        b[self.source_rows["ADC_INTERNAL_HALF"]] = reference / 2
        for role, value in (offsets or {}).items():
            b[self.rows[role]] = -value
        for a, z, current in currents:
            if a != "AGND":
                b[self.idx[a]] += current
            if z != "AGND":
                b[self.idx[z]] -= current
        return self.lu.solve(b)

    def v(self, x, node):
        return 0j if node == "AGND" else x[self.idx[node]]

    def differential(self, x):
        return self.v(x, self.p) - self.v(x, self.n)

    def mean(self, x):
        return (self.v(x, self.p) + self.v(x, self.n)) / 2


def analyze(parts, pins):
    cases = []
    for ch, load, f in itertools.product(
        ("L", "R"), ("per_pin_ground", "differential", "per_pin_reference"), (20, 1000, 20000)
    ):
        c = Circuit(parts, pins, ch, f, load)
        x = c.solve()
        g = abs(c.differential(x))
        closed = 1210 / 2490 * 1e6 / (1e6 + 33.2)
        assert abs(g / closed - 1) < 0.001 and abs(c.v(x, c.pre)) > 0.9999
        cases.append(
            dict(
                channel=ch,
                load_hypothesis=load,
                frequency_hz=f,
                gain=g,
                phase_deg=math.degrees(math.atan2(c.differential(x).imag, c.differential(x).real)),
            )
        )
    # All four feedback-network resistor signs and both load signs are independent.
    # DC reference divider/servo signs are exercised below, separately.
    corners = []
    worst_current = 0
    minimum_driver = 99
    maximum_driver = -99
    input_low = 99
    input_high = -99
    cm_error = 0
    for signs in itertools.product((-1, 1), repeat=6):
        overrides = {f"R{i + 1}": (2490 if i < 2 else 1210) * (1 + signs[i] * 0.001) for i in range(4)}
        for load in ("per_pin_ground", "differential", "per_pin_reference"):
            ac = Circuit(
                parts,
                pins,
                f=20000,
                load=load,
                load_scale=(1 + signs[4] * 0.15, 1 + signs[5] * 0.15),
                overrides=overrides,
            )
            ax = ac.solve()
            gain = abs(ac.differential(ax))
            dc = Circuit(
                parts,
                pins,
                f=0,
                load=load,
                load_scale=(1 + signs[4] * 0.15, 1 + signs[5] * 0.15),
                overrides=overrides,
            )
            # Use a conservative4.06Vrms PRE_OUT full-scale allocation, including
            # E10 gain corners; reference3.2..3.4 is a qualification allocation.
            for ref, pre_dc in itertools.product((3.2, 3.4), (-0.025, 0.025)):
                dx = dc.solve(source=pre_dc, reference=ref)
                for node in (ac.op, ac.on):
                    amplitude = abs(ac.v(ax, node)) * 4.06 * math.sqrt(2)
                    minimum_driver = min(minimum_driver, dc.v(dx, node).real - amplitude)
                    maximum_driver = max(maximum_driver, dc.v(dx, node).real + amplitude)
                for node in (ac.fp, ac.fn):
                    amplitude = abs(ac.v(ax, node)) * 4.06 * math.sqrt(2)
                    input_low = min(input_low, dc.v(dx, node).real - amplitude)
                    input_high = max(input_high, dc.v(dx, node).real + amplitude)
                for node, raw, r in [(ac.op, ac.p, 3.32), (ac.on, ac.n, 3.32)]:
                    # Include current through local compensation C and DC/RF
                    # feedback by deriving actual amplifier output KCL.
                    ac_current = 0j
                    dc_current = 0j
                    for a, b, y in ac.branches:
                        if a == node:
                            ac_current += (ac.v(ax, a) - ac.v(ax, b)) * y
                        if b == node:
                            ac_current += (ac.v(ax, b) - ac.v(ax, a)) * y
                    for a, b, y in dc.branches:
                        if a == node:
                            dc_current += (dc.v(dx, a) - dc.v(dx, b)) * y
                        if b == node:
                            dc_current += (dc.v(dx, b) - dc.v(dx, a)) * y
                    worst_current = max(
                        worst_current, abs(dc_current) + abs(ac_current) * 4.06 * math.sqrt(2)
                    )
                cm_error = max(cm_error, abs(dc.mean(dx).real - ref / 2))
            corners.append(dict(load_hypothesis=load, gain_20k=gain))
    # These are screens against declared allocations, not guaranteed THD/swing
    # specs at the actual low-impedance codec load.
    assert worst_current < 0.020 and input_low > -0.16 and input_high < 4.9 - 1.3
    assert minimum_driver > -0.1838 + 0.30 and maximum_driver < 4.9 - 0.30, (
        minimum_driver,
        maximum_driver,
        worst_current,
        input_low,
        input_high,
    )
    dc_cases = []
    max_cm_error = 0
    max_dc = 0
    for signs in itertools.product((-1, 1), repeat=7):
        overrides = {
            "R8": 1e6 * (1 + signs[0] * 0.001),
            "R9": 1e6 * (1 + signs[1] * 0.001),
            "R10": 1e5 * (1 + signs[2] * 0.001),
            "R11": 1e5 * (1 + signs[3] * 0.001),
        }
        c = Circuit(parts, pins, f=0, load="per_pin_ground", overrides=overrides)
        # OPA4192 hot5nA/Vos75uV; servo film leakage100nA allocated
        # separately (not inferred from a typical film insulation value).
        x = c.solve(
            source=signs[4] * 0.025,
            reference=3.3,
            offsets={
                "reference": signs[5] * 75e-6,
                "servo": signs[6] * 75e-6,
                "fda": signs[5] * 400e-6,
                "buffer": signs[6] * 1.2e-3,
            },
            currents=[
                ("REF_DIV_L", "AGND", signs[5] * 5e-9),
                ("CM_SENSE_L", "AGND", signs[6] * (5e-9 + 100e-9)),
            ],
        )
        error = c.mean(x).real - 1.65
        diff = c.differential(x).real
        max_cm_error = max(max_cm_error, abs(error))
        max_dc = max(max_dc, abs(diff))
        dc_cases.append(dict(common_mode_error_v=error, raw_differential_dc_v=diff))
    # Independent signs for each error source are bounded by superposition
    # (sum of magnitudes), at all eight resistor-tolerance signs and both
    # reference endpoints. This also includes FDA hot input bias/offset current.
    dc_bounds = []
    for signs in itertools.product((-1, 1), repeat=8):
        overrides = {f"R{i + 1}": (2490 if i < 2 else 1210) * (1 + signs[i] * 0.001) for i in range(4)}
        overrides.update(
            {f"R{i}": (1e6 if i < 10 else 1e5) * (1 + signs[i - 4] * 0.001) for i in range(8, 12)}
        )
        c = Circuit(parts, pins, f=0, overrides=overrides)
        for ref in (3.2, 3.4):
            base = c.solve(source=0, reference=ref)
            errors = [
                c.solve(source=0.025),
                c.solve(source=0, offsets={"buffer": 1.2e-3}),
                c.solve(source=0, offsets={"reference": 75e-6}),
                c.solve(source=0, offsets={"servo": 75e-6}),
                c.solve(source=0, offsets={"fda": 400e-6}),
                c.solve(source=0, currents=[("REF_DIV_L", "AGND", 5e-9)]),
                c.solve(source=0, currents=[("CM_SENSE_L", "AGND", 5e-9)]),
                c.solve(source=0, currents=[("CM_SENSE_L", "CM_DRIVE_L", 100e-9)]),
                c.solve(source=0, currents=[(c.fp, "AGND", 2e-6), (c.fn, "AGND", 2e-6)]),
                c.solve(source=0, currents=[(c.fp, "AGND", 39e-9), (c.fn, "AGND", -39e-9)]),
            ]
            cm = abs(c.mean(base) - ref / 2) + sum(abs(c.mean(x)) for x in errors)
            diff = abs(c.differential(base)) + sum(abs(c.differential(x)) for x in errors)
            dc_bounds.append(dict(common_mode_error_bound_v=cm, raw_differential_dc_bound_v=diff))
            max_cm_error = max(max_cm_error, cm)
            max_dc = max(max_dc, diff)
    assert max_cm_error < 0.020 and max_dc < 0.025
    assert minimum_driver - max_cm_error - max_dc / 2 > -0.1838 + 0.30
    assert maximum_driver + max_cm_error + max_dc / 2 < 4.9 - 0.30
    clipping_margin = 2 * math.sqrt(2) - 4.06 * max(v["gain_20k"] for v in corners) * math.sqrt(2) - max_dc
    assert clipping_margin > 0
    sensitivities = []
    for load, ft, pole, ro in itertools.product(
        ("per_pin_ground", "differential"), (100e6, 135e6, 180e6), (150e6, 300e6), (4, 20, 40)
    ):
        responses = []
        for f in (20, 1000, 20000):
            c = Circuit(parts, pins, f=f, load=load, finite=True, ft=ft, second_pole=pole, ro=ro)
            responses.append(abs(c.differential(c.solve())))
        flatness = max(abs(20 * math.log10(h / responses[1])) for h in responses)
        assert flatness < 0.05
        sensitivities.append(
            dict(load=load, ft_hz=ft, second_pole_hz=pole, assumed_output_r_ohm=ro, flatness_db=flatness)
        )
    # Reference half filter + servo dominant response. The10k VOCM resistor
    # loads the150k typical input; servo DC gain and pole include that loss.
    half_tau = 0.5e6 * 150e-9
    servo_tau = (1e5 / 2) * 1.1e-6 * (1 + 10000 / 150000)
    residual = 3.4 / 2 * (math.exp(-1.2 / half_tau) + math.exp(-1.2 / servo_tau))
    assert residual < 5e-6
    return dict(
        revision="E12",
        ideal_ac_cases=len(cases),
        ideal_ac=cases,
        mode_resistor_load_corners=len(corners),
        corner_variable_signs=6,
        corner_results=corners,
        allocated_dc_cases=len(dc_cases),
        allocated_dc=dc_cases,
        independent_dc_superposition_bounds=dict(
            resistor_reference_corners=len(dc_bounds),
            independent_sources=10,
            results=dc_bounds,
            method="Magnitude sum of independent linear error responses, plus baseline; eight resistor signs and two reference endpoints",
        ),
        voltage_current_screen=dict(
            preamp_full_scale_allocation_rms_v=4.06,
            reference_allocation_v=[3.2, 3.4],
            minimum_driver_output_v=minimum_driver,
            maximum_driver_output_v=maximum_driver,
            minimum_fda_input_v=input_low,
            maximum_fda_input_v=input_high,
            maximum_output_current_a=worst_current,
            continuous_abs_current_limit_a=0.020,
            additional_dc_and_model_current_allocation_a=0.001,
            output_headroom_after_dc_error_allocation_v=minimum_driver
            - max_cm_error
            - max_dc / 2
            - (-0.1838 + 0.30),
            output_rail_headroom_allocation_v=0.30,
            minimum_bias_rail_for_screen_v=-0.1838,
            maximum_dc_common_mode_error_v=max_cm_error,
            maximum_differential_dc_v=max_dc,
            conditional_peak_margin_to_typical_2vrms_adc_v=clipping_margin,
            amplifier_actual_load_headroom_thd_verified=False,
        ),
        finite_model_sensitivity=dict(
            cases=len(sensitivities),
            results=sensitivities,
            interpretation="Hypothetical two-pole FDA/current-output-resistance sensitivity only; not manufacturer macromodel, gain/phase margin or transient stability proof",
        ),
        settling_screen=dict(
            required_after_input_connect_s=1.2,
            reference_filter_tau_max_s=half_tau,
            servo_tau_max_typical_vocm_load_s=servo_tau,
            residual_reference_step_v=residual,
            limited_model="Two allocated dominant exponential terms; no saturated-startup, clock kickback, nonlinear cap or power-sequence proof",
        ),
        load_hypotheses=[
            "260Ohm+-15% per pin to ground",
            "260Ohm+-15% differential",
            "260Ohm+-15% per pin to ideal reference/2",
        ],
        actual_adc_impedance_model_confirmed=False,
        adc_scale_calibrated=False,
        pcb_routed=False,
        negative_bias_window_monitor_implemented=False,
        physical_audio_verified=False,
    )


def noise(parts, pins):
    """Own-circuit noise only; do not add ADC-load Johnson noise to EVM DNR."""
    result = {}
    previous = None
    for k in range(81):
        f = 20 * (1000 ** (k / 80))
        c = Circuit(parts, pins, f=f)
        density = {}
        for ref, a, b, r in c.resistors:
            h = c.differential(c.solve(source=0, currents=[(a, b, 1)]))
            density[ref] = abs(h) ** 2 * 4 * 1.380649e-23 * 298.15 / r
        for role, white, knee in [
            ("buffer", 2.9e-9, 1000),
            ("reference", 5.5e-9, 300),
            ("servo", 5.5e-9, 300),
            ("fda", 3.3e-9, 150),
        ]:
            # OPA1656 colored model follows E10's typical integrated0.53uV.
            psd = white**2 * (1 + knee / f)
            if role == "buffer":
                psd = white**2 + ((0.53e-6) ** 2 - white**2 * 19980) / math.log(1000) / f
            h = c.differential(c.solve(source=0, offsets={role: 1}))
            density[role + ".en"] = abs(h) ** 2 * psd
        for role, nodes, white, knee in [
            ("fda", (c.fp, c.fn), 0.5e-12, 10000),
            ("buffer", (c.pre, "BUF_L"), 6e-15, 0),
            ("reference", ("REF_DIV_L", "REF_HALF_L"), 1.5e-15, 0),
            ("servo", ("REF_HALF_L", "CM_SENSE_L"), 1.5e-15, 0),
        ]:
            for i, node in enumerate(nodes):
                h = c.differential(c.solve(source=0, currents=[(node, "AGND", 1)]))
                density[role + ".i" + str(i)] = abs(h) ** 2 * white**2 * (1 + knee / f)
        if previous:
            oldf, old = previous
            for name, value in density.items():
                result[name] = result.get(name, 0) + (value + old[name]) * (f - oldf) / 2
        previous = f, density
    own = sum(v for name, v in result.items() if name != "E10_SOURCE_R")
    return dict(
        band_hz=[20, 20000],
        weighting="unweighted",
        frequency_points=81,
        own_raw_differential_rms_uv=math.sqrt(own) * 1e6,
        contributions_raw_differential_uv={name: math.sqrt(v) * 1e6 for name, v in result.items()},
        assumptions="Typical white+1/f voltage/current models; ideal nominal resistor matching; no pump/rail noise or aliasing; not measured SNR",
        excluded=[
            "ADC intrinsic/reference noise and EVM ADC driver overlap",
            "LM7705 ripple/PSRR and digital/clock coupling",
            "Resistor/capacitor excess noise and leakage",
            "Nonlinear ADC switching/aliasing, distortion and temperature",
        ],
        complete_system_weighted_noise_closed=False,
    )
