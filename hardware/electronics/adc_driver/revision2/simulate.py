"""Conditional R2 Kelvin-interface stage simulation; no approved cable/codec model."""

import argparse
import json
from pathlib import Path

from ...common.netlists import netlist, number
from ..qualification.audit import REPO, sha
from ..qualification.spice import MODEL_PIN_NUMBERS, MODEL_SHA256, Simulator, nominal_transfer
from .design import CONTRACT, ROOT, VALUES

OUT = ROOT / "generated/spice"


def deck(
    parts,
    pins,
    model,
    *,
    line_r=0.001,
    line_nh=0.5,
    sense_pf=0,
    load_r=260,
    load_reference=1.65,
    analysis="ac",
):
    assert line_r > 0 and line_nh > 0 and sense_pf >= 0 and load_r > 0 and analysis in ("ac", "dc")
    assert pins == CONTRACT
    lines = [
        "E12-R2 declared Kelvin interface stage",
        f'.include "{model.resolve()}"',
        "V5 V5_REG 0 5",
        "VN NBIAS_L 0 -.23",
        "VC VOCM_L 0 1.65",
        "VIN BUF_L 0 DC 0 AC 1",
        f"VL LOADREF 0 {load_reference}",
    ]

    def node(n):
        return "0" if n == "AGND" else n

    for ref in [f"R{i}" for i in range(1, 7)] + [f"C{i}" for i in range(1, 6)]:
        assert parts[ref].findtext("value") == VALUES[ref]
        a, b = (node(pins[ref][str(i)]) for i in (1, 2))
        lines.append(f"{ref} {a} {b} {number(VALUES[ref]):.12g}")
    lines.append("XFDA " + " ".join(node(pins["U1"][p]) for p in MODEL_PIN_NUMBERS) + " THS4551")
    for p in ("P", "N"):
        lines += [
            f"RW{p} ADC_L{p} LINE{p} {line_r:.12g}",
            f"LW{p} LINE{p} SENSE_L{p} {line_nh * 1e-9:.12g}",
            f"RL{p} SENSE_L{p} LOADREF {load_r:.12g}",
        ]
        if sense_pf:
            lines.append(f"CP{p} FB_{p}_L 0 {sense_pf * 1e-12:.12g}")
    lines += [".temp 27", ".ac dec 20 10 100Meg" if analysis == "ac" else ".dc VIN 0 6 .25", ".end"]
    return lines


def run(args):
    assert sha(args.vendor_model) == MODEL_SHA256
    parts, pins = netlist(ROOT / "generated/netlist.xml")
    assert pins == CONTRACT
    OUT.mkdir(exist_ok=True)
    receipt = OUT / "verification.json"
    receipt.unlink(missing_ok=True)
    simulator = Simulator(args.library, args.code_models)
    (OUT / "initialization.txt").write_text("\n".join(simulator.initialization_log) + "\n")
    cases = []
    for scenario in [
        dict(id="co_location_hypothesis"),
        dict(id="line_10nh", line_r=0.1, line_nh=10),
        dict(id="line_50nh_1pf_sense", line_r=0.2, line_nh=50, sense_pf=1),
        dict(id="low_load", load_r=221),
        dict(id="dc_zero_start", analysis="dc"),
    ]:
        opts = dict(scenario)
        identity = opts.pop("id")
        lines = deck(parts, pins, args.vendor_model, **opts)
        path = OUT / (identity + ".cir")
        path.write_text("\n".join(lines) + "\n")
        analysis = opts.get("analysis", "ac")
        data = simulator.run(
            lines, ["SENSE_LP", "SENSE_LN", "ADC_LP", "ADC_LN", "DRV_LP", "DRV_LN"], analysis
        )
        (OUT / (identity + "-log.txt")).write_text("\n".join(data.pop("log")) + "\n")
        (OUT / (identity + ".json")).write_text(json.dumps(data, indent=2) + "\n")
        summary = dict(
            id=identity, parameters=opts, solver_clean=data["convergence_clean"], netlist_sha256=sha(path)
        )
        if analysis == "ac":
            # Receipt's generic transfer function reads ADC_LP/N: report actual converter-boundary nodes.
            transfer = dict(
                data,
                nodes=dict(data["nodes"], ADC_LP=data["nodes"]["SENSE_LP"], ADC_LN=data["nodes"]["SENSE_LN"]),
            )
            summary["at_1khz"] = nominal_transfer(transfer)
        else:
            summary["zero_input_pin_common_mode_v"] = (
                data["nodes"]["SENSE_LP"][0][0] + data["nodes"]["SENSE_LN"][0][0]
            ) / 2
        cases.append(summary)
    report = dict(
        revision="E12-R2",
        cases=cases,
        vendor_model_sha256=sha(args.vendor_model),
        model_modified=False,
        model_redistributed=False,
        simulator_library_sha256=sha(args.library),
        code_models_sha256={p.name: sha(p) for p in simulator.code_models},
        source_sha256={
            str(p.relative_to(REPO)): sha(p)
            for p in [Path(__file__), ROOT / "design.py", ROOT / "generated/netlist.xml"]
        },
        evidence_sha256={p.name: sha(p) for p in OUT.iterdir() if p.is_file() and p != receipt},
        approved_cable_length_mm=None,
        actual_codec_model_present=False,
        extracted_board_parasitics_present=False,
        servo_and_pump_models_present=False,
        phase_margin_verified=False,
        full_board_stability_verified=False,
        physical_tests_performed=0,
        build_ready=False,
        fabrication_released=False,
        limitations=[
            "Only native FDA R1-R6/C1-C5 stage with ideal fixed supplies/VOCM/buffer",
            "Load DC reference1.65V is a hypothesis; ESS input DCcurrent/reference remains missing",
            "Line R/L and added sense capacitance are illustrative, not validated cable limits",
            "Closed-loop frequency response is not return ratio or phase margin",
            "No harmonic distortion, real switching load, protection, startup, temperature or physical proof",
        ],
    )
    receipt.write_text(json.dumps(report, indent=2) + "\n")
    print(
        "R2 conditional manufacturer-model cases",
        len(cases),
        "; solver-clean",
        sum(c["solver_clean"] for c in cases),
    )


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ["library", "code-models", "vendor-model"]:
        p.add_argument("--" + name, type=Path, required=True)
    run(p.parse_args())


if __name__ == "__main__":
    main()
