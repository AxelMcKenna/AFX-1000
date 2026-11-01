"""New supplementary actual mate fixture, preserving AP02's70-case source."""

import argparse
import json
import subprocess
from pathlib import Path

from .stage import OUT, ROOT, sha, write
from .verify import mesh, row_errors

EMPTY = [
    "M3_hardware_nominal_mates",
    "M2_hardware_nominal_mates",
    "upper_gasket_base",
    "upper_gasket_tray",
    "frame_gasket_tray",
    "frame_gasket_fan",
    "meter_gasket_wall_plate",
    "feedthrough_wall",
    "new_hardware_base_pins",
    "new_parts_feet_spacers",
    "meter_plate_other_new_parts",
]
CONTROLS = [
    "M3_directseal_overlap_control",
    "M2_directseal_overlap_control",
    "upper_seal_tray_overlap_control",
    "upper_seal_base_overlap_control",
    "frame_seal_tray_overlap_control",
    "frame_seal_fan_overlap_control",
    "meter_seal_plate_overlap_control",
    "meter_seal_wall_overlap_control",
]


def run(output):
    output = Path(output).resolve()
    if output.exists() or ((ROOT / "handoff.json").exists() and output.is_relative_to(ROOT)):
        raise RuntimeError("Mating proof requires a fresh output destination")
    main = json.loads((OUT / "current-native/verification.json").read_text())
    assert main["complete_set"] and main["all_requested_clear"] and not main["changed_inputs"]
    bindings = dict(main["input_sha256"])
    for p in [OUT / "current-native/verification.json", ROOT / "mating.py", ROOT / "mating.scad"]:
        bindings[str(p)] = sha(p)
    assert all(sha(Path(n)) == h for n, h in bindings.items())
    base = main["cases"]["tray_geometry"]["command"]
    base = base[: base.index("-o")]
    base[base.index('ap_case="tray_geometry"')] = 'ap_case="none"'
    output.mkdir(parents=True)
    rows = {}
    for n in EMPTY + CONTROLS:
        spec = dict(role="empty" if n in EMPTY else "control")
        if n in CONTROLS:
            spec["expected_volume"] = 0.0016
        target = output / (n + ".stl")
        cmd = base + ["-D", "mate_case=" + json.dumps(n), "-o", str(target), str(ROOT / "mating.scad")]
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        (output / (n + ".log")).write_text(p.stdout + p.stderr)
        row = dict(
            returncode=p.returncode,
            role=spec["role"],
            command=cmd,
            statistics=mesh(target) if target.exists() else None,
        )
        row["errors"] = row_errors(n, row, spec, output)
        row["clear"] = not row["errors"]
        rows[n] = row
        result = dict(
            cases=rows,
            required_cases=EMPTY + CONTROLS,
            input_sha256=bindings,
            changed_inputs=[n for n, h in bindings.items() if sha(Path(n)) != h],
            artifact_sha256={
                str(p): sha(p)
                for name in rows
                for p in [output / (name + ".log"), output / (name + ".stl")]
                if p.exists()
            },
            all_requested_clear=all(r["clear"] for r in rows.values()),
            original70_case_inputs_modified=False,
            physical_qualified=False,
            thermal_qualified=False,
            fabrication_released=False,
        )
        result["all_requested_clear"] &= not result["changed_inputs"]
        write(output / "verification.json", result)
        print(
            json.dumps(
                dict(
                    case=n,
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
    parser.add_argument("--outdir", required=True, type=Path)
    args = parser.parse_args()
    raise SystemExit(not run(args.outdir)["all_requested_clear"])
