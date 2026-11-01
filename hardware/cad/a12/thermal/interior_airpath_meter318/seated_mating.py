"""Fresh scoped-contact proof plus guarded penetration controls; no part edits."""

import argparse
import json
import subprocess
from pathlib import Path

from .mating import CONTROLS, EMPTY
from .seated_stage import EXTRA
from .stage import OUT, ROOT, sha, write
from .verify import mesh, row_errors


def run(output):
    output = Path(output).resolve()
    if output.exists() or ((ROOT / "handoff.json").exists() and output.is_relative_to(ROOT)):
        raise RuntimeError("Seated proof requires a new output directory")
    main = json.loads((OUT / "current-native/verification.json").read_text())
    assert main["complete_set"] and main["all_requested_clear"] and not main["changed_inputs"]
    contract = json.loads((OUT / "mating-seat-contract.json").read_text())
    assert contract["test_only_guard_mm"] == 0.00002
    assert contract["deliberate_penetration_mm"] == 0.02
    assert not contract["raw_source_or_actual_AP03_parts_modified"]
    assert sha(OUT / "mating-seated.scad") == contract["fixture_sha256"]
    bindings = dict(main["input_sha256"])
    for n in [
        "seated_mating.py",
        "seated_stage.py",
        "mating.py",
        "mating.scad",
        "mating_guards.scad",
        "generated/mating-seated.scad",
        "generated/mating-seat-contract.json",
        "generated/current-native/verification.json",
        "generated/raw-mating-surface-audit.json",
        "generated/raw-mating-bolt-domain-audit.json",
        "generated/mating-raw/verification.json",
    ]:
        bindings[str(ROOT / n)] = sha(ROOT / n)
    assert all(sha(Path(n)) == h for n, h in bindings.items())
    original = main["cases"]["tray_geometry"]["command"]
    base = original[: original.index("-o")]
    base[base.index('ap_case="tray_geometry"')] = 'ap_case="none"'
    output.mkdir(parents=True)
    names = EMPTY + CONTROLS + EXTRA
    rows = {}
    for name in names:
        spec = dict(role="empty" if name in EMPTY else "control" if name in CONTROLS else "witness")
        if name in CONTROLS:
            spec["expected_volume"] = 0.0016
        target = output / (name + ".stl")
        cmd = base + [
            "-D",
            'mate_case="none"',
            "-D",
            "mate_seated_case=" + json.dumps(name),
            "-o",
            str(target),
            str(OUT / "mating-seated.scad"),
        ]
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        (output / (name + ".log")).write_text(p.stdout + p.stderr)
        row = dict(
            role=spec["role"],
            returncode=p.returncode,
            command=cmd,
            statistics=mesh(target) if target.exists() else None,
        )
        row["errors"] = row_errors(name, row, spec, output)
        row["clear"] = not row["errors"]
        rows[name] = row
        result = dict(
            cases=rows,
            required_cases=names,
            input_sha256=bindings,
            changed_inputs=[n for n, h in bindings.items() if sha(Path(n)) != h],
            artifact_sha256={
                str(p): sha(p)
                for n in rows
                for p in [output / (n + ".log"), output / (n + ".stl")]
                if p.exists()
            },
            all_requested_clear=all(r["clear"] for r in rows.values()),
            actual_AP03_parts_modified=False,
            guarded_positive_controls=CONTROLS + EXTRA,
            physical_qualified=False,
            thermal_qualified=False,
            fabrication_released=False,
        )
        result["all_requested_clear"] &= not result["changed_inputs"]
        write(output / "verification.json", result)
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
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--outdir", type=Path, required=True)
    args = parser.parse_args()
    raise SystemExit(not run(args.outdir)["all_requested_clear"])
