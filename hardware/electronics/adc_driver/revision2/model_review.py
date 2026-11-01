"""Isolate native-stage DC discrepancy without modifying the external TI model."""

import argparse
import json
from pathlib import Path

from ..qualification.audit import REPO, sha
from ..qualification.spice import MODEL_SHA256, Simulator, deck, source_circuit

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "generated/model-review"


def run(library, code_models, model):
    assert sha(model) == MODEL_SHA256
    OUT.mkdir(parents=True, exist_ok=True)
    simulator = Simulator(library, code_models)
    (OUT / "initialization.txt").write_text("\n".join(simulator.initialization_log) + "\n")
    parts, pins = source_circuit()
    cases = []
    for load_ref in [0, 0.825, 1.65]:
        lines = deck(parts, pins, model, analysis="dc", dc_start=0, dc_stop=0.1, dc_step=0.1)
        lines = [
            line.replace("RLP ADC_LP 0 ", "RLP ADC_LP LOADREF ").replace(
                "RLN ADC_LN 0 ", "RLN ADC_LN LOADREF "
            )
            for line in lines
        ]
        lines.insert(-1, f"VLOADREF LOADREF 0 {load_ref}")
        identity = "native-loadref-" + str(load_ref).replace(".", "p")
        names = [
            "ADC_LP",
            "ADC_LN",
            "DRV_LP",
            "DRV_LN",
            "VOCM_L",
            "xfda.MID",
            "xfda.AOLVOCM",
            "xfda.VOUT_CM",
            "xfda.N1242451",
        ]
        data = simulator.run(lines, names, "dc")
        log = data.pop("log")
        (OUT / (identity + ".cir")).write_text("\n".join(lines) + "\n")
        (OUT / (identity + ".json")).write_text(json.dumps(data, indent=2) + "\n")
        (OUT / (identity + "-log.txt")).write_text("\n".join(log) + "\n")

        def v(name):
            return data["nodes"][name][0][0]

        cm = (v("ADC_LP") + v("ADC_LN")) / 2
        cases.append(
            dict(
                id=identity,
                load_reference_v=load_ref,
                common_mode_v=cm,
                common_loop_error_v=v("xfda.N1242451") - v("xfda.VOUT_CM"),
                internal_common_control_above_mid_v=v("xfda.AOLVOCM") - v("xfda.MID"),
                solver_clean=data["convergence_clean"],
            )
        )
    # Exact public TI package fixture, with only explicit DC analysis appended.
    fixture = model.parent / "schematic1.net"
    lines = [line.replace("TC=0,0", "TC1=0 TC2=0") for line in fixture.read_text().splitlines()] + [
        ".dc V_V3 0 .1 .1",
        ".end",
    ]
    lines.insert(1, '.include "' + str(model) + '"')
    try:
        data = simulator.run(lines, ["OUT+", "OUT-", "VOCM"], "dc")
    except AssertionError:
        (OUT / "vendor-fixture-failure.txt").write_text("\n".join(simulator.logs) + "\n")
        raise
    log = data.pop("log")
    (OUT / "vendor-fixture.cir").write_text("\n".join(lines) + "\n")
    (OUT / "vendor-fixture.json").write_text(json.dumps(data, indent=2) + "\n")
    (OUT / "vendor-fixture-log.txt").write_text("\n".join(log) + "\n")
    cm = (data["nodes"]["OUT+"][0][0] + data["nodes"]["OUT-"][0][0]) / 2
    assert data["convergence_clean"] and abs(cm) < 0.001
    result = dict(
        model_sha256=sha(model),
        simulator_library_sha256=sha(Path(library)),
        code_models_sha256={p.name: sha(p) for p in simulator.code_models},
        vendor_fixture_sha256=sha(fixture),
        vendor_fixture_url="https://www.ti.com/lit/zip/sbomb92b",
        vendor_fixture_syntax_adaptation="Only resistor TC=0,0 replaced by equivalent TC1=0 TC2=0; external .include and DC analysis added",
        vendor_fixture_zero_input_common_mode_v=cm,
        model_modified=False,
        model_redistributed=False,
        cases=cases,
        explanation="Native-to-vendor terminals agree with the vendor fixture. Ground-referenced static loads force substantial common-mode DC current and drive the model common-mode control into its clamp; referencing loads to 1.65 V removes that burden. This explains the numerical branch discrepancy without proving real ADC load reference, common-mode source capability, switching behavior or physical headroom.",
        actual_ess_dc_input_reference_verified=False,
        full_board_stability_verified=False,
        physical_tests_performed=0,
        fabrication_released=False,
        build_ready=False,
        source_sha256={
            str(p.relative_to(REPO)): sha(p)
            for p in [
                Path(__file__),
                ROOT.parent / "qualification/spice.py",
                ROOT.parent / "qualification/generated/native-original/netlist.xml",
            ]
        },
        evidence_sha256={
            p.name: sha(p) for p in OUT.iterdir() if p.is_file() and p.name != "verification.json"
        },
    )
    (OUT / "verification.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result["cases"], indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--library", type=Path, required=True)
    parser.add_argument("--code-models", type=Path, required=True)
    parser.add_argument("--vendor-model", type=Path, required=True)
    args = parser.parse_args()
    run(args.library, args.code_models, args.vendor_model.resolve())


if __name__ == "__main__":
    main()
