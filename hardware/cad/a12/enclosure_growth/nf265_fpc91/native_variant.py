"""Separate source-bound native replay for named receiving-model variants."""

import argparse
import json
import subprocess
import time
from pathlib import Path

from hardware.cad.a12.thermal.enlarged_base.verify import mesh

from . import verify
from .capture import ROOT, closure, sha, write


def supplemental_specs():
    return {
        "actual_C401_C402_primary_body_geometry": dict(role="solid-review"),
        "actual_C401_C402_tail_margin_collision": dict(role="empty"),
        "actual_C401_body_positive_control": dict(role="control", expected_volume=0.008),
        "actual_force_minimum_bores_collision": dict(role="empty"),
        "actual_mount_minimum_bores_collision": dict(role="empty"),
        "actual_old_force_bore_failure_witness": dict(role="witness"),
    }


def run(variant, output, names=None):
    entry = ROOT / variant / "checks.scad"
    output = Path(output).resolve()
    if output.exists() or (ROOT / "handoff.json").exists():
        raise RuntimeError("Fresh output required")
    definitions = verify.specs() if variant == "tail_shape" else supplemental_specs()
    names = names or list(definitions)
    assert names and len(names) == len(set(names)) and all(n in definitions for n in names)
    source = closure(entry)
    for p in [
        Path(__file__),
        Path(verify.__file__),
        ROOT / "capture.py",
        ROOT / "tail_shape.py",
        ROOT / "receiving_contract.py",
        ROOT / "capture.json",
        ROOT / "generated/model.json",
        ROOT / "tail_shape/audit.json",
        ROOT / "tail_shape/model.json",
        ROOT / "supplement/contract.json",
        verify.ENGINE,
    ]:
        source[p] = sha(p)
    output.mkdir(parents=True)
    rows = {}
    version = subprocess.run([str(verify.ENGINE), "--version"], capture_output=True, text=True)
    assert version.returncode == 0 and "2026.10.27" in version.stdout + version.stderr
    for name in names:
        values = verify.variables(name if variant == "tail_shape" else "none")
        if variant != "tail_shape":
            values["su_case"] = name
        target = output / (name + ".stl")
        command = [
            str(verify.ENGINE),
            "--backend=Manifold",
            "--hardwarnings",
            "--export-format=binstl",
            "-o",
            str(target),
        ]
        for k, v in values.items():
            command += ["-D", k + "=" + json.dumps(v)]
        command += [str(entry)]
        t = time.time()
        result = subprocess.run(command, capture_output=True, text=True)
        (output / (name + ".log")).write_text(result.stdout + result.stderr)
        row = dict(
            role=definitions[name]["role"],
            returncode=result.returncode,
            command=command,
            elapsed_seconds=time.time() - t,
            statistics=mesh(target) if target.exists() else None,
        )
        row["errors"] = verify.errors(name, row, definitions[name], output)
        row["clear"] = not row["errors"]
        rows[name] = row
        changed = [str(p) for p, h in source.items() if not p.is_file() or sha(p) != h]
        report = dict(
            variant=variant,
            required_cases=names,
            cases=rows,
            complete_set=len(rows) == len(definitions) and set(rows) == set(definitions),
            input_sha256={str(p): h for p, h in source.items()},
            artifact_sha256={str(p): sha(p) for p in output.iterdir() if p.suffix in {".log", ".stl"}},
            changed_inputs=changed,
            all_requested_clear=len(rows) == len(names)
            and all(r["clear"] for r in rows.values())
            and not changed,
            engine_version=version.stdout + version.stderr,
            receiving_model_change_only=True,
            physical_qualified=False,
            electrical_qualified=False,
            full_harness_qualified=False,
            fabrication_released=False,
        )
        write(output / "verification.json", report)
        print(
            json.dumps(
                dict(
                    case=name,
                    clear=row["clear"],
                    errors=row["errors"],
                    volume=row["statistics"] and row["statistics"]["volume_mm3"],
                )
            ),
            flush=True,
        )
    return report


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--variant", choices=["tail_shape", "supplement"], required=True)
    p.add_argument("--outdir", type=Path, required=True)
    p.add_argument("--cases", nargs="+")
    a = p.parse_args()
    raise SystemExit(not run(a.variant, a.outdir, a.cases)["all_requested_clear"])
