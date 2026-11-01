"""Optional coupled E12-R2 buffer/reference/common-mode vendor-model review.

This supplements the frozen R2 stage receipt. Ideal supplies, an assumed static
converter load and omitted clamp/pump/PD behavior preclude full qualification.
Vendor libraries remain external and unmodified.
"""

import argparse
import json
import multiprocessing
from pathlib import Path

from hardware.electronics.adc_driver.qualification.audit import REPO, sha
from hardware.electronics.adc_driver.qualification.spice import Simulator
from hardware.electronics.adc_driver.revision2.design import ROOT as ADC
from hardware.electronics.adc_driver.revision2.simulate import deck as stage_deck
from hardware.electronics.common.netlists import netlist, number

OUT = REPO / "hardware/validation/board-qualification/generated/r2-coupled"
MODELS = {
    "ths4551": (
        "https://www.ti.com/lit/zip/sbomb92b",
        "0a8c0db4398d7849ef46ba831bac4bc5f09352c9ead3a7be6a3a7e36d5a21527",
    ),
    "opa192": (
        "https://www.ti.com/lit/zip/sbom862f",
        "1c438e45e978ffaf5aa13c7e2bb18ad5da70259775522ec41f47633a5db99033",
    ),
    "opa1656": (
        "https://www.ti.com/lit/zip/sbomaw6c",
        "9847ed60c62e792ee6f1c84899278a3c11ce71a6d21804bdd88f51199f1ba055",
    ),
}


def deck(parts, pins, models, *, drive="signal", load_reference=1.65, servo_cap_scale=1, analysis="ac"):
    assert drive in {"signal", "reference"} and analysis in {"ac", "dc"}
    lines = stage_deck(parts, pins, models["ths4551"], analysis=analysis, load_reference=load_reference)
    lines[0] = "E12-R2 coupled buffer/reference/common-mode conditional model"
    lines = [line for line in lines if not line.startswith(("VC ", "VIN ", ".ac ", ".dc ", ".end"))]
    for key in ("opa192", "opa1656"):
        assert sha(models[key]) == MODELS[key][1]
        lines.append(f'.include "{models[key].resolve()}"')
    lines += [
        "VP12 P12 0 12",
        "VN12 N12 0 -12",
        "VIN PRE_OUT_L 0 DC 0 AC " + ("1" if drive == "signal" else "0"),
        "VREF REF_ADC1 0 DC 3.3 AC " + ("1" if drive == "reference" else "0"),
    ]

    def node(value):
        return "0" if value == "AGND" else value

    for ref in [f"R{i}" for i in range(7, 14)] + ["C6", "C7"]:
        value = number(parts[ref].findtext("value")) * (servo_cap_scale if ref == "C7" else 1)
        ends = [node(pins[ref][str(i)]) for i in (1, 2)]
        lines.append(f"{ref} {' '.join(ends)} {value:.12g}")
    for instance, ref, pin_order, model in (
        ("BUFFER", "U3", ["3", "2", "8", "4", "1"], "OPA1656"),
        ("REFHALF", "U4", ["3", "2", "4", "11", "1"], "OPAx192"),
        ("CMSERVO", "U4", ["5", "6", "4", "11", "7"], "OPAx192"),
    ):
        lines.append(f"X{instance} {' '.join(node(pins[ref][pin]) for pin in pin_order)} {model}")
    lines += [".ac dec 40 .01 100Meg" if analysis == "ac" else ".dc VIN 0 6 .25", ".end"]
    return lines


def run(args):
    models = {key: getattr(args, key) for key in MODELS}
    assert all(sha(models[key]) == meta[1] for key, meta in MODELS.items())
    parts, pins = netlist(ADC / "generated/netlist.xml")
    sources = [
        Path(__file__),
        ADC / "generated/netlist.xml",
        ADC / "design.py",
        ADC / "simulate.py",
        ADC.parent / "qualification/spice.py",
        REPO / "hardware/electronics/common/netlists.py",
    ]
    hashes = {str(path.relative_to(REPO)): sha(path) for path in sources}
    OUT.mkdir(exist_ok=True)
    receipt = OUT / "verification.json"
    receipt.unlink(missing_ok=True)
    sim = Simulator(args.library, args.code_models)
    (OUT / "initialization.txt").write_text("\n".join(sim.initialization_log) + "\n")
    cases = []
    for scenario in [
        dict(id="signal_nominal"),
        dict(id="reference_nominal", drive="reference"),
        dict(id="servo_cap_low", drive="reference", servo_cap_scale=0.9),
        dict(id="servo_cap_high", drive="reference", servo_cap_scale=1.1),
        dict(id="dc_zero_start", analysis="dc"),
    ]:
        options = dict(scenario)
        identity = options.pop("id")
        lines = deck(parts, pins, models, **options)
        path = OUT / (identity + ".cir")
        path.write_text("\n".join(lines) + "\n")
        data = sim.run(
            lines,
            ["BUF_L", "REF_HALF_L", "CM_DRIVE_L", "VOCM_L", "SENSE_LP", "SENSE_LN"],
            options.get("analysis", "ac"),
        )
        (OUT / (identity + "-log.txt")).write_text("\n".join(data.pop("log")) + "\n")
        (OUT / (identity + ".json")).write_text(json.dumps(data, indent=2) + "\n")
        summary = dict(
            id=identity,
            parameters=options,
            solver_clean=data["convergence_clean"],
            accepted_for_numerical_comparison=data["solver_comparison_eligible"],
            deck_sha256=sha(path),
        )
        if options.get("analysis") == "dc":
            summary["zero_input_common_mode_v"] = (
                data["nodes"]["SENSE_LP"][0][0] + data["nodes"]["SENSE_LN"][0][0]
            ) / 2
            summary["vocm_interval_v"] = [
                min(v[0] for v in data["nodes"]["VOCM_L"]),
                max(v[0] for v in data["nodes"]["VOCM_L"]),
            ]
        else:
            index = min(range(len(data["axis"])), key=lambda i: abs(data["axis"][i] - 1000))
            p, n = [complex(*data["nodes"][name][index]) for name in ("SENSE_LP", "SENSE_LN")]
            summary["at_1khz"] = dict(differential_gain_abs=abs(p - n), common_mode_gain_abs=abs((p + n) / 2))
        cases.append(summary)
        print(identity, "solver clean:", data["convergence_clean"], flush=True)
    assert all(sha(REPO / name) == value for name, value in hashes.items()), (
        "Source changed during simulation"
    )
    report = dict(
        revision="E12-R2 coupled conditional review",
        cases=cases,
        all_cases_solver_clean=all(case["solver_clean"] for case in cases),
        accepted_case_count=sum(case["accepted_for_numerical_comparison"] for case in cases),
        vendor_models={
            key: dict(source=meta[0], sha256=meta[1], modified=False, redistributed=False)
            for key, meta in MODELS.items()
        },
        source_sha256=hashes,
        evidence_sha256={p.name: sha(p) for p in OUT.iterdir() if p.is_file() and p != receipt},
        simulator_library_sha256=sha(args.library),
        code_models_sha256={p.name: sha(p) for p in sim.code_models},
        buffer_reference_and_external_common_mode_servo_present=True,
        ideal_supply_sources=True,
        actual_codec_model_present=False,
        pump_and_bias_monitor_and_pd_models_present=False,
        vocm_clamp_model_present=False,
        extracted_board_parasitics_present=False,
        return_ratio_or_phase_margin_verified=False,
        full_board_stability_verified=False,
        physical_tests_performed=0,
        fabrication_released=False,
        build_ready=False,
        limitation="One left channel, ideal3.3V converter reference and static260ohm per-pin loads to1.65V; actual ESS DC/switched load is unavailable. Models exclude diode-clamp conduction/capacitance, pump/PD/power sequences and package/shared-supply coupling. Closed-loop transfer and solver cleanliness are not stability or noise qualification.",
    )
    receipt.write_text(json.dumps(report, indent=2) + "\n")
    return report


def _control_worker(library, code_models, lines, nodes, output):
    """A fresh solver process prevents one vendor circuit contaminating another."""
    logfile = output.with_name(output.stem + "-log.txt")
    logfile.write_text("")

    class EventLog(list):
        def append(self, message):
            super().append(message)
            with logfile.open("a") as handle:
                handle.write(message + "\n")

    try:
        sim = Simulator(library, code_models)
        logfile.write_text("\n".join(sim.logs) + "\n")
        sim.logs = EventLog(sim.logs)
        result = sim.run(lines, nodes, "ac")
        result.pop("log")
    except Exception as error:
        result = dict(
            completed=False, convergence_clean=False, solver_comparison_eligible=False, failure=repr(error)
        )
    output.write_text(json.dumps(result, indent=2) + "\n")


def model_controls(args):
    """Isolate model/solver behavior before interpreting the coupled circuit."""
    output = OUT.with_name("r2-coupled-model-controls")
    output.mkdir(exist_ok=True)
    models = {key: getattr(args, key) for key in MODELS}
    assert all(sha(models[key]) == meta[1] for key, meta in MODELS.items())
    parts, pins = netlist(ADC / "generated/netlist.xml")
    source_paths = [
        Path(__file__),
        ADC / "generated/netlist.xml",
        ADC / "design.py",
        ADC / "simulate.py",
        ADC.parent / "qualification/spice.py",
    ]
    hashes = {str(path.relative_to(REPO)): sha(path) for path in source_paths}
    cases = [("ths4551_stage", stage_deck(parts, pins, models["ths4551"]), ["ADC_LP", "ADC_LN"])]
    for key, name in (("opa192", "OPAx192"), ("opa1656", "OPA1656")):
        cases.append(
            (
                key + "_unity_follower",
                [
                    key + " isolated unity follower control",
                    f'.include "{models[key].resolve()}"',
                    "VP P12 0 12",
                    "VN N12 0 -12",
                    "VIN IN 0 DC 1.65 AC 1",
                    "RLOAD OUT 0 2000",
                    f"XAMP IN OUT P12 N12 OUT {name}",
                    ".temp 27",
                    ".ac dec 20 10 100Meg",
                    ".end",
                ],
                ["OUT"],
            )
        )
    report = {}
    for name, lines, nodes in cases:
        (output / (name + ".cir")).write_text("\n".join(lines) + "\n")
        result_path = output / (name + ".json")
        result_path.unlink(missing_ok=True)
        process = multiprocessing.get_context("spawn").Process(
            target=_control_worker, args=(args.library, args.code_models, lines, nodes, result_path)
        )
        process.start()
        process.join(timeout=30)
        timed_out = process.is_alive()
        if timed_out:
            process.terminate()
            process.join(timeout=5)
            if process.is_alive():
                process.kill()
                process.join()
        if result_path.exists() and not timed_out:
            result = json.loads(result_path.read_text())
        else:
            result = dict(
                completed=False,
                convergence_clean=False,
                solver_comparison_eligible=False,
                timed_out=timed_out,
                worker_exitcode=process.exitcode,
                failure="Solver control exceeded its 30 second compute budget"
                if timed_out
                else "Solver worker exited without a result",
            )
            result_path.write_text(json.dumps(result, indent=2) + "\n")
        report[name] = dict(
            completed=result["completed"],
            solver_clean=result["convergence_clean"],
            accepted_for_numerical_comparison=result["solver_comparison_eligible"],
            timed_out=timed_out,
            worker_exitcode=process.exitcode,
        )
        print(name, report[name], flush=True)
    assert all(sha(REPO / name) == value for name, value in hashes.items()), "Control source changed"
    receipt = output / "verification.json"
    receipt.unlink(missing_ok=True)
    data = dict(
        scope="Isolated vendor-model solver controls, not board qualification",
        cases=report,
        source_sha256=hashes,
        model_sha256={key: meta[1] for key, meta in MODELS.items()},
        simulator_library_sha256=sha(args.library),
        code_models_sha256={path.name: sha(path) for path in sorted(args.code_models.glob("*.cm"))},
        separate_solver_process_per_case=True,
        compute_budget_per_case_seconds=30,
        evidence_sha256={path.name: sha(path) for path in output.iterdir() if path.is_file()},
        full_board_stability_verified=False,
        physical_tests_performed=0,
        build_ready=False,
    )
    receipt.write_text(json.dumps(data, indent=2) + "\n")
    return data


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("library", "code-models", *MODELS):
        parser.add_argument("--" + name, required=True, type=Path)
    parser.add_argument("--model-controls", action="store_true")
    args = parser.parse_args()
    (model_controls if args.model_controls else run)(args)
