"""Required nonempty geometry, empty collision and positive-control native checks."""

import argparse
import json
import math
import subprocess

from hardware.cad.a12.thermal.generate import REPO, sha
from hardware.cad.a12.thermal.verify import binary_stl

from .generate import OUT, ROOT


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--openscad", required=True)
    args = parser.parse_args()
    geometry = json.loads((OUT / "geometry.json").read_text())
    source_paths = [
        ROOT / "generate.py",
        ROOT / "verify.py",
        ROOT / "synthesize.py",
        OUT / "checks.scad",
        ROOT.parent / "u10/sources/context/hardware/cad/a12/positive_links/generated/positive-links.stl",
        OUT / "LAND.stl",
        OUT / "TIM.stl",
        OUT / "obstacles.json",
    ]
    source_paths += [REPO / p for p in geometry["source_sha256"]]
    sources = {str(p.relative_to(REPO)): sha(p) for p in sorted(set(source_paths))}
    # Every external obstacle byte must still match the captured generation packet.
    stale = [p for p, h in geometry["reference_shared_source_sha256"].items() if sha(REPO / p) != h]
    native = {}
    failures = []
    for case in [
        "geometry",
        "component_collision",
        "link_collision",
        "case_collision",
        "positive_control",
        "source_front_witness",
        "J106_tail_witness",
    ]:
        target = OUT / (case + ".stl")
        target.unlink(missing_ok=True)
        run = subprocess.run(
            [
                args.openscad,
                "--hardwarnings",
                "--backend",
                "Manifold",
                "--export-format",
                "binstl",
                "-D",
                f'trial="{case}"',
                "-D",
                'part="u10only"',
                "-D",
                'thermal_part="u10only"',
                "-D",
                'positive_part="u10only"',
                "-o",
                str(target),
                str(OUT / "checks.scad"),
            ],
            capture_output=True,
            text=True,
            timeout=180,
        )
        log = run.stdout + run.stderr
        (OUT / (case + ".log")).write_text(log)
        empty = run.returncode == 1 and "Current top level object is empty." in log and not target.exists()
        if case.endswith("collision") and empty and not any(v in log for v in ("WARNING", "ERROR")):
            native[case] = dict(result="empty", returncode=run.returncode)
        elif (
            run.returncode == 0
            and "NoError" in log
            and target.exists()
            and not any(v in log for v in ("WARNING", "ERROR"))
        ):
            row = dict(result="valid native manifold", returncode=run.returncode, **binary_stl(target))
            native[case] = row
            if case.endswith("collision") and row["volume_mm3"] > 1e-6:
                failures.append(case)
            if case == "geometry" and not math.isclose(
                row["volume_mm3"], sum(geometry["volumes_mm3"].values()), rel_tol=0.0005
            ):
                failures.append(case)
            if (case == "positive_control" or case.endswith("witness")) and not math.isclose(
                row["volume_mm3"], 0.008, rel_tol=0.005, abs_tol=1e-6
            ):
                failures.append(case)
        else:
            native[case] = dict(result="rejected", returncode=run.returncode)
            failures.append(case)
    changed = [p for p, h in sources.items() if sha(REPO / p) != h]
    report = dict(
        native_checks=native,
        failed_cases=failures,
        stale_inputs=stale,
        changed_inputs=changed,
        source_sha256=sources,
        native_engine=subprocess.run(
            [args.openscad, "--version"], capture_output=True, text=True, check=True
        ).stderr.strip(),
        evidence_sha256={
            str(p.relative_to(REPO)): sha(p) for p in OUT.iterdir() if p.suffix in {".stl", ".step", ".log"}
        },
        accepted_native_evidence=not (failures or stale or changed),
        physical_fit_verified=False,
        thermal_path_qualified=False,
        fabrication_released=False,
    )
    (OUT / "verification.json").write_text(json.dumps(report, indent=2) + "\n")
    return 0 if report["accepted_native_evidence"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
