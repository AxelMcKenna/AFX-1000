"""Optional external TI-model/ngspice stage simulation, not full-board qualification."""

import argparse
import ctypes as ct
import datetime
import json
import math
from pathlib import Path

from ...common.netlists import netlist
from ..analyze import number
from ..verify import CONTRACT, VALUES
from .audit import OUT, PARENT, REPO, sha

MODEL_SHA256 = "0a8c0db4398d7849ef46ba831bac4bc5f09352c9ead3a7be6a3a7e36d5a21527"
MODEL_ORDER = ("IN+", "IN-", "OUT+", "OUT-", "VOCM", "VCC", "VEE")
MODEL_PIN_NUMBERS = ("8", "1", "4", "5", "2", "3", "6")


class Complex(ct.Structure):
    _fields_ = [("real", ct.c_double), ("imag", ct.c_double)]


class Vector(ct.Structure):
    _fields_ = [
        ("name", ct.c_char_p),
        ("kind", ct.c_int),
        ("flags", ct.c_short),
        ("real", ct.POINTER(ct.c_double)),
        ("complex", ct.POINTER(Complex)),
        ("length", ct.c_int),
    ]


class Simulator:
    """Synchronous shared-library calls; no downloaded code models are loaded."""

    def __init__(self, library, code_models):
        self.logs, self.loaded = [], False
        self.library = Path(library).resolve()
        self.ng = ct.CDLL(str(self.library))
        text = ct.CFUNCTYPE(ct.c_int, ct.c_char_p, ct.c_int, ct.c_void_p)
        terminate = ct.CFUNCTYPE(ct.c_int, ct.c_int, ct.c_bool, ct.c_bool, ct.c_int, ct.c_void_p)
        data = ct.CFUNCTYPE(ct.c_int, ct.c_void_p, ct.c_int, ct.c_int, ct.c_void_p)
        initialize = ct.CFUNCTYPE(ct.c_int, ct.c_void_p, ct.c_int, ct.c_void_p)
        background = ct.CFUNCTYPE(ct.c_int, ct.c_bool, ct.c_int, ct.c_void_p)
        self.callbacks = [
            text(lambda value, *_: self.logs.append(value.decode(errors="replace")) or 0),
            text(lambda *_: 0),
            terminate(lambda *_: 0),
            data(lambda *_: 0),
            initialize(lambda *_: 0),
            background(lambda *_: 0),
        ]
        self.ng.ngSpice_Init.argtypes = [text, text, terminate, data, initialize, background, ct.c_void_p]
        self.ng.ngSpice_Init.restype = ct.c_int
        assert self.ng.ngSpice_Init(*self.callbacks, None) == 0
        self.ng.ngSpice_Command.argtypes = [ct.c_char_p]
        self.ng.ngSpice_Command.restype = ct.c_int
        self.ng.ngSpice_Circ.argtypes = [ct.POINTER(ct.c_char_p)]
        self.ng.ngSpice_Circ.restype = ct.c_int
        self.ng.ngGet_Vec_Info.argtypes = [ct.c_char_p]
        self.ng.ngGet_Vec_Info.restype = ct.POINTER(Vector)
        self.command("set ngbehavior=ps")
        self.code_models = sorted(Path(code_models).resolve().glob("*.cm"))
        assert self.code_models, "Missing simulator-matched XSPICE code models"
        for path in self.code_models:
            self.command("codemodel " + str(path))
        self.command("version")
        self.initialization_log = list(self.logs)

    def command(self, value):
        assert self.ng.ngSpice_Command(value.encode()) == 0, (value, self.logs[-10:])

    def vector(self, name):
        pointer = self.ng.ngGet_Vec_Info(name.encode())
        assert pointer and pointer.contents.length > 0, ("Missing analysis vector", name, self.logs[-15:])
        vector = pointer.contents
        if vector.flags & 2:
            values = [complex(vector.complex[i].real, vector.complex[i].imag) for i in range(vector.length)]
        else:
            assert vector.flags & 1
            values = [complex(vector.real[i], 0) for i in range(vector.length)]
        assert all(math.isfinite(v.real) and math.isfinite(v.imag) for v in values), name
        return values

    def run(self, lines, names, analysis):
        if self.loaded:
            self.command("destroy all")
            self.command("remcirc")
        begin = len(self.logs)
        encoded = [line.encode() for line in lines]
        array = (ct.c_char_p * (len(encoded) + 1))(*encoded, None)
        assert self.ng.ngSpice_Circ(array) == 0, self.logs[begin:]
        self.loaded = True
        self.command("run")
        log = self.logs[begin:]
        errors = [line for line in log if "error" in line.lower() or "fatal" in line.lower()]
        assert not errors, errors
        axis = self.vector("frequency" if analysis == "ac" else "v-sweep")
        vectors = {name: self.vector("v(" + name.lower() + ")") for name in names}
        assert all(len(v) == len(axis) for v in vectors.values())
        warnings = [
            line
            for line in log
            if any(word in line.lower() for word in ("warning", "singular", "gmin", "failed"))
        ]
        return dict(
            axis=[v.real for v in axis],
            nodes={n: [[v.real, v.imag] for v in values] for n, values in vectors.items()},
            solver_warnings=warnings,
            log=log,
            completed=True,
            convergence_clean=not warnings,
            solver_comparison_eligible=not warnings,
        )


def source_circuit():
    path = OUT / "native-original/netlist.xml"
    assert path.exists(), "Run qualification.native first"
    parts, pins = netlist(path)
    assert pins == CONTRACT, "Native circuit pin contract changed"
    for ref, expected in VALUES.items():
        assert parts[ref].findtext("value") == expected, ref
    return parts, pins


def deck(
    parts,
    pins,
    model,
    *,
    analysis="ac",
    load="per_pin_ground",
    resistance=260,
    extra_input_pf=0,
    extra_output_pf=0,
    positive_v=5,
    negative_v=-0.23,
    vocm_v=1.65,
    dc_start=-6,
    dc_stop=6,
    dc_step=0.25,
):
    assert analysis in ("ac", "dc") and load in ("per_pin_ground", "differential")
    assert resistance > 0 and extra_input_pf >= 0 and extra_output_pf >= 0
    assert dc_step != 0 and (dc_stop - dc_start) * dc_step > 0
    assert 2.7 <= positive_v - negative_v <= 5.4
    assert pins["U1"] == CONTRACT["U1"], "FDA native-to-vendor pin mapping changed"
    path = str(Path(model).resolve())
    assert not any(c in path for c in ("\n", "\r", '"'))

    def node(value):
        return "0" if value == "AGND" else value

    lines = [
        "E12 native THS4551 left-stage conditional vendor simulation",
        '.include "' + path + '"',
        f"V5 V5_REG 0 {positive_v:.12g}",
        f"VNEG NBIAS_L 0 {negative_v:.12g}",
        f"VCM VOCM_L 0 {vocm_v:.12g}",
        "VIN BUF_L 0 DC 0 AC 1",
    ]
    for ref in [f"R{i}" for i in range(1, 7)] + [f"C{i}" for i in range(1, 6)]:
        assert pins[ref] == CONTRACT[ref], (ref, "Native stage connection changed")
        a, b = (node(pins[ref][str(i)]) for i in (1, 2))
        lines.append(f"{ref} {a} {b} {number(parts[ref].findtext('value')):.12g}")
    lines.append("XFDA " + " ".join(node(pins["U1"][p]) for p in MODEL_PIN_NUMBERS) + " THS4551")
    if load == "per_pin_ground":
        lines += [f"RLP ADC_LP 0 {resistance:.12g}", f"RLN ADC_LN 0 {resistance:.12g}"]
    else:
        lines.append(f"RLD ADC_LP ADC_LN {resistance:.12g}")
    for value, nodes, stem in [
        (extra_input_pf, ("FB_P_L", "FB_N_L"), "CPARIN"),
        (extra_output_pf, ("ADC_LP", "ADC_LN"), "CPAROUT"),
    ]:
        if value:
            lines += [f"{stem}{i} {name} 0 {value * 1e-12:.12g}" for i, name in enumerate(nodes)]
    lines += [
        ".temp 27",
        ".ac dec 20 10 100Meg"
        if analysis == "ac"
        else f".dc VIN {dc_start:.12g} {dc_stop:.12g} {dc_step:.12g}",
        ".end",
    ]
    return lines


def scalar_complex(value):
    return complex(*value)


def nominal_transfer(result):
    index = min(range(len(result["axis"])), key=lambda i: abs(result["axis"][i] - 1000))
    actual = scalar_complex(result["nodes"]["ADC_LP"][index]) - scalar_complex(
        result["nodes"]["ADC_LN"][index]
    )
    return dict(
        frequency_hz=result["axis"][index],
        differential_gain=abs(actual),
        differential_phase_deg=math.degrees(math.atan2(actual.imag, actual.real)),
        transfer_real=actual.real,
        transfer_imag=actual.imag,
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--library", type=Path, required=True)
    parser.add_argument("--code-models", type=Path, required=True)
    parser.add_argument("--vendor-model", type=Path, required=True)
    args = parser.parse_args()
    model = args.vendor_model.resolve()
    assert sha(model) == MODEL_SHA256, "Different vendor model requires independent review"
    signature = next(
        line.split()[2:]
        for line in model.read_text().splitlines()
        if line.lower().startswith(".subckt ths4551 ")
    )
    assert tuple(signature) == MODEL_ORDER
    out = OUT / "vendor-spice"
    out.mkdir(exist_ok=True)
    result_path = out / "verification.json"
    result_path.unlink(missing_ok=True)
    simulator = Simulator(args.library, args.code_models)
    smoke = simulator.run(
        [
            "Independent RC simulator smoke",
            "VIN IN 0 AC 1",
            "R1 IN OUT 1000",
            "C1 OUT 0 10n",
            ".ac lin 1 15915.494309189535 15915.494309189535",
            ".end",
        ],
        ["OUT"],
        "ac",
    )
    assert abs(scalar_complex(smoke["nodes"]["OUT"][0]) - complex(0.5, -0.5)) < 1e-9
    (out / "initialization.txt").write_text("\n".join(simulator.initialization_log) + "\n")
    (out / "rc-smoke.json").write_text(json.dumps(smoke, indent=2) + "\n")
    parts, pins = source_circuit()
    cases = []
    scenarios = [
        dict(id="nominal"),
        dict(id="low_resistance", resistance=221),
        dict(id="high_resistance", resistance=299),
        dict(id="differential_load", load="differential"),
        dict(id="extra_0p5pf_input", extra_input_pf=0.5),
        dict(id="extra_0p5pf_input_22pf_output", extra_input_pf=0.5, extra_output_pf=22),
    ]
    scenarios += [
        dict(id="dc_nominal", analysis="dc"),
        dict(id="dc_low_supply", analysis="dc", positive_v=4.9, negative_v=-0.1838),
        dict(id="dc_differential_low_load", analysis="dc", load="differential", resistance=221),
        dict(id="dc_zero_forward", analysis="dc", dc_start=0, dc_stop=6),
        dict(id="dc_zero_reverse", analysis="dc", dc_start=0, dc_stop=-6, dc_step=-0.25),
        dict(
            id="dc_zero_forward_low_supply",
            analysis="dc",
            positive_v=4.9,
            negative_v=-0.1838,
            dc_start=0,
            dc_stop=6,
        ),
    ]
    for scenario in scenarios:
        parameters = dict(scenario)
        identity = parameters.pop("id")
        lines = deck(parts, pins, model, **parameters)
        net_path = out / (identity + ".cir")
        net_path.write_text("\n".join(lines) + "\n")
        analysis = parameters.get("analysis", "ac")
        try:
            data = simulator.run(lines, ["BUF_L", "ADC_LP", "ADC_LN", "DRV_LP", "DRV_LN"], analysis)
        except AssertionError:
            (out / (identity + "-failure.txt")).write_text("\n".join(simulator.logs) + "\n")
            raise
        (out / (identity + "-log.txt")).write_text("\n".join(data.pop("log")) + "\n")
        (out / (identity + ".json")).write_text(json.dumps(data, indent=2) + "\n")
        summary = dict(
            id=identity,
            parameters=parameters,
            analysis=analysis,
            points=len(data["axis"]),
            completed=data["completed"],
            convergence_clean=data["convergence_clean"],
            solver_comparison_eligible=data["solver_comparison_eligible"],
            solver_warnings=data["solver_warnings"],
            netlist_sha256=sha(net_path),
        )
        if analysis == "ac":
            summary["at_1khz"] = nominal_transfer(data)
            gains = [
                abs(scalar_complex(p) - scalar_complex(n))
                for p, n in zip(data["nodes"]["ADC_LP"], data["nodes"]["ADC_LN"])
            ]
            summary["maximum_swept_closed_loop_gain"] = max(gains)
            summary["closed_loop_phase_is_not_loop_phase_margin"] = True
        else:
            summary["raw_pin_voltage_span_v"] = [
                min(v[0] for name in ("ADC_LP", "ADC_LN") for v in data["nodes"][name]),
                max(v[0] for name in ("ADC_LP", "ADC_LN") for v in data["nodes"][name]),
            ]
            summary["sweep_axis_v"] = [data["axis"][0], data["axis"][-1]]
            zero = min(range(len(data["axis"])), key=lambda i: abs(data["axis"][i]))
            assert abs(data["axis"][zero]) < 1e-8
            common = (data["nodes"]["ADC_LP"][zero][0] + data["nodes"]["ADC_LN"][zero][0]) / 2
            expected = parameters.get("vocm_v", 1.65)
            if parameters.get("load", "per_pin_ground") == "per_pin_ground":
                expected /= 1 + number(parts["R5"].findtext("value")) / parameters.get("resistance", 260)
            summary["zero_input_common_mode_v"] = common
            summary["ideal_static_common_mode_estimate_v"] = expected
            summary["common_mode_residual_v"] = common - expected
            summary["dc_hardware_headroom_interpretation_accepted"] = False
        cases.append(summary)
    nominal = cases[0]["at_1khz"]
    assert abs(nominal["frequency_hz"] - 1000) < 1e-5
    assert abs(nominal["differential_gain"] - 1210 / 2490) < 0.001, "Unexpected nominal vendor transfer"
    sources = [
        Path(__file__),
        PARENT / "verify.py",
        PARENT / "analyze.py",
        OUT / "native-original/netlist.xml",
    ]
    result = dict(
        revision="E12-Q01-conditional-vendor-stage",
        checked_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        scope="Native left THS4551 resistor/capacitor stage with ideal buffered source, fixed VOCM, explicit DC supplies and declared static load/parasitic scenarios",
        vendor_model=dict(
            url="https://www.ti.com/lit/zip/sbomb92b",
            archive_sha256="10922b527027603f0c047c1070c6ffd3504a9ecf8d9ce1127ade2965e3863602",
            path=str(model),
            sha256=sha(model),
            subcircuit_pin_order=list(MODEL_ORDER),
            model_modified=False,
            redistributed=False,
        ),
        simulator_library=dict(
            path=str(simulator.library),
            sha256=sha(simulator.library),
            initialization_log="initialization.txt",
            code_models_sha256={p.name: sha(p) for p in simulator.code_models},
        ),
        independent_rc_smoke_passed=True,
        model_compatibility_passed=True,
        cases=cases,
        clean_cases=sum(c["convergence_clean"] for c in cases),
        rejected_solver_cases=[c["id"] for c in cases if not c["solver_comparison_eligible"]],
        actual_codec_input_switching_model_present=False,
        full_board_analog_stability_verified=False,
        phase_margin_verified=False,
        servo_reference_buffer_and_pumps_simulated=False,
        power_down_pin_modeled=False,
        temperature_c=27,
        dc_common_mode_load_discrepancy_resolved=False,
        physical_tests_performed=0,
        fabrication_released=False,
        build_ready=False,
        limitations=[
            "Static loads and additional parasitics are illustrative hypotheses, not measured/extracted codec or PCB models",
            "Ideal fixed VOCM excludes the actual slow servo and its correction of output-resistor DC drops",
            "Only the left FDA stage is simulated; buffer/reference/pump/supervision and partial power are omitted",
            "Closed-loop AC phase/gain is not a return-ratio or phase-margin measurement",
            "DC sweep does not establish physical clipping/THD, switching kickback, enable timing or thermal limits",
            "Solver-warning DC branches are retained and rejected; finite vectors alone do not prove valid operating points",
            "Even clean ground-load DC runs show unexpected zero-input common mode near 1.21 V versus ideal static estimate near 1.629 V; model/load compatibility remains unresolved and DC headroom interpretation is rejected",
        ],
        source_sha256={str(p.relative_to(REPO)): sha(p) for p in sources},
        evidence_sha256={p.name: sha(p) for p in out.iterdir() if p.is_file() and p != result_path},
    )
    result_path.write_text(json.dumps(result, indent=2) + "\n")
    print(
        "Vendor model stage:",
        len(cases),
        "conditional AC/DC cases completed; nominal gain",
        nominal["differential_gain"],
        "no full-board stability or physical approval",
    )


if __name__ == "__main__":
    main()
