"""Bounded isolated model comparisons; no physical-board stability claim."""

import argparse
import json
import multiprocessing
import time
from pathlib import Path

from .coupled_adc import REPO, _control_worker, sha

OUT = REPO / "hardware/validation/board-qualification/generated/r2-model-comparison"
VENDORS = {
    "opa192_tina": (
        "OPAx192",
        "https://www.ti.com/lit/zip/sbom860e",
        "c9be1f20a558abbd9abaebb2d37d9b26b103d9804cc369064f9db9744067ebf4",
    ),
    "opa1656_tina": (
        "OPA1656",
        "https://www.ti.com/lit/zip/sbomaw8",
        "bced33ad3d86413e7acbb5e53e727dea0bbf7819792d75aff91e085ba4a36bb1",
    ),
    "opa192_pspice": (
        "OPAx192",
        "https://www.ti.com/lit/zip/sbom862f",
        "1c438e45e978ffaf5aa13c7e2bb18ad5da70259775522ec41f47633a5db99033",
    ),
}


def run(args):
    OUT.mkdir(exist_ok=True)
    receipt = OUT / "verification.json"
    receipt.unlink(missing_ok=True)
    sources = [
        Path(__file__),
        Path(__file__).with_name("coupled_adc.py"),
        REPO / "hardware/electronics/adc_driver/qualification/spice.py",
    ]
    hashes = {str(path.relative_to(REPO)): sha(path) for path in sources}
    for key, (_, _, expected) in VENDORS.items():
        assert sha(getattr(args, key)) == expected, (key, "Not the reviewed unmodified model")
    jobs = []
    for key, feedback in (
        ("opa192_tina", 0),
        ("opa1656_tina", 0),
        ("opa192_tina", 0.001),
        ("opa192_pspice", 0.001),
    ):
        identity = key + ("_ideal_feedback" if feedback == 0 else "_1mohm_feedback_hypothesis")
        output = OUT / (identity + ".json")
        output.unlink(missing_ok=True)
        model = getattr(args, key).resolve()
        assert not any(char in str(model) for char in ('"', "\n", "\r"))
        lines = [
            identity,
            f'.include "{model}"',
            "VP P12 0 12",
            "VN N12 0 -12",
            "VIN IN 0 DC 1.65 AC 1",
            "RLOAD OUT 0 2000",
        ]
        if feedback:
            lines.append(f"RTRACE OUT FB {feedback}")
        lines += [
            f"XAMP IN {'FB' if feedback else 'OUT'} P12 N12 OUT {VENDORS[key][0]}",
            ".temp 27",
            ".ac dec 20 10 100Meg",
            ".end",
        ]
        (OUT / (identity + ".cir")).write_text("\n".join(lines) + "\n")
        process = multiprocessing.get_context("spawn").Process(
            target=_control_worker, args=(args.library, args.code_models, lines, ["OUT"], output)
        )
        process.start()
        jobs.append((identity, key, feedback, output, process, time.monotonic()))
    results = {}
    for identity, key, feedback, output, process, started in jobs:
        process.join(timeout=max(0, 30 - (time.monotonic() - started)))
        timed_out = process.is_alive()
        if timed_out:
            process.terminate()
            process.join(timeout=5)
            if process.is_alive():
                process.kill()
                process.join()
        if output.exists() and not timed_out:
            result = json.loads(output.read_text())
        else:
            result = dict(
                completed=False,
                convergence_clean=False,
                solver_comparison_eligible=False,
                timed_out=timed_out,
                worker_exitcode=process.exitcode,
            )
            output.write_text(json.dumps(result, indent=2) + "\n")
        results[identity] = dict(
            model=key,
            feedback_series_resistance_hypothesis_ohm=feedback,
            completed=result["completed"],
            solver_clean=result["convergence_clean"],
            accepted_for_numerical_comparison=result["solver_comparison_eligible"],
            timed_out=timed_out,
            worker_exitcode=process.exitcode,
        )
        print(identity, results[identity], flush=True)
    assert all(sha(REPO / name) == value for name, value in hashes.items()), (
        "Source changed during comparison"
    )
    report = dict(
        scope="Isolated official model comparison; no ADC-board or physical stability qualification",
        cases=results,
        source_sha256=hashes,
        vendor_models={
            key: dict(source=value[1], sha256=value[2], modified=False, redistributed=False)
            for key, value in VENDORS.items()
        },
        simulator_library_sha256=sha(args.library),
        code_models_sha256={path.name: sha(path) for path in sorted(args.code_models.glob("*.cm"))},
        separate_solver_process_per_case=True,
        compute_budget_seconds_per_case=30,
        feedback_resistance_is_extracted_board_parasitic=False,
        physical_tests_performed=0,
        full_board_stability_verified=False,
        build_ready=False,
        evidence_sha256={path.name: sha(path) for path in OUT.iterdir() if path.is_file()},
    )
    receipt.write_text(json.dumps(report, indent=2) + "\n")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ("library", "code_models", *VENDORS):
        parser.add_argument("--" + key.replace("_", "-"), required=True, type=Path)
    run(parser.parse_args())
