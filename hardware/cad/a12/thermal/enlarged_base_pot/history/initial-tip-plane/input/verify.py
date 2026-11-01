"""CP01 captured-source native replay; sealed outputs cannot be overwritten."""

import argparse
import json
import math
import subprocess
from pathlib import Path

from hardware.cad.a12.thermal.enlarged_base.verify import mesh

from .stage import EB, OUT, ROOT, sha, write


def guard_output(output, root=ROOT):
    output = Path(output).resolve()
    if (root / "handoff.json").exists() and output.is_relative_to(root.resolve()):
        raise RuntimeError("Sealed candidate is read-only. Supply a NEW --outdir outside this packet.")
    if (output / "verification.json").exists():
        raise RuntimeError(
            "Replay output already has a receipt. Use a NEW --outdir; evidence is never overwritten."
        )
    return output


def inputs():
    capture = json.loads((ROOT / "capture.json").read_text())
    paths = [ROOT / n for n in capture["derived_context_sha256"]]
    paths += [
        ROOT / n
        for n in [
            "capture.json",
            "stage.py",
            "verify.py",
            "geometry.scad",
            "parent-audit.json",
            "EB01-erratum.json",
        ]
    ]
    paths += [OUT / n for n in ["context-derived.scad", "parts.scad", "config.json", "cases.json"]]
    paths += [EB / "verify.py", EB / "stage.py"]
    return {str(p): sha(p) for p in paths}


def row_errors(name, row, spec, output):
    bad = []
    target = output / (name + ".stl")
    lp = output / (name + ".log")
    if not lp.exists():
        return [name + ": missinglog"]
    log = lp.read_text()
    if "WARNING" in log or "ERROR" in log:
        bad.append(name + ": nativewarning/error")
    if spec["role"] == "empty":
        if (
            row["returncode"] != 1
            or "Current top level object is empty." not in log
            or target.exists()
            or row.get("statistics") is not None
        ):
            bad.append(name + ": actualcollision notempty")
    else:
        if row["returncode"] != 0 or "NoError" not in log or not target.exists():
            return bad + [name + ": missingrequiredNoErrorsolid"]
        actual = mesh(target)
        if actual != row.get("statistics"):
            bad.append(name + ": actualSTL/row mismatch")
        if actual["volume_mm3"] <= 0.001:
            bad.append(name + ": missingvolume")
        if spec["role"] != "review" and (
            not actual["closed_oriented_boundary"] or actual["degenerate_triangles_excluded"]
        ):
            bad.append(name + ": production/control topology failure")
        if spec["expected_volume"] is not None and not math.isclose(
            actual["volume_mm3"], spec["expected_volume"], abs_tol=2e-6
        ):
            bad.append(name + ": wrongpositivecontrol volume")
    return bad


def replay(executable, output=OUT):
    output = guard_output(output)
    output.mkdir(parents=True, exist_ok=True)
    bindings = inputs()
    capture = json.loads((ROOT / "capture.json").read_text())
    assert all(sha(ROOT / n) == h for n, h in capture["derived_context_sha256"].items()), (
        "Captured context changed"
    )
    cases = json.loads((OUT / "cases.json").read_text())
    cfg = json.loads((OUT / "config.json").read_text())
    rows = {}
    for name, spec in cases.items():
        target = output / (name + ".stl")
        assert not target.exists(), "Replay refuses pre-existing output"
        values = dict(
            part="cp_only",
            thermal_part="cp_only",
            positive_part="cp_only",
            candidate_case="cp_only",
            trial="cp_only",
            ui_case="cp_only",
            eb_case="cp_only",
            ps_case="cp_only",
            cp_case="cp_only",
            body_width=334,
            body_depth=188.4,
            shell_height=45.6,
            panel_z=43.6,
            fasteners=cfg["fasteners"],
            board_mounts=cfg["mounts"],
            rear_ports=cfg["rear_ports"],
            openings=cfg["openings"],
        )
        values[spec["selector"]] = spec["value"]
        cmd = [str(executable), "--hardwarnings", "--backend", "Manifold", "--export-format", "binstl"]
        for k, v in values.items():
            cmd += ["-D", k + "=" + json.dumps(v)]
        cmd += ["-o", str(target), str(OUT / "context-derived.scad")]
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        (output / (name + ".log")).write_text(p.stdout + p.stderr)
        row = dict(
            returncode=p.returncode,
            statistics=mesh(target) if p.returncode == 0 and target.exists() else None,
            command=cmd,
            role=spec["role"],
        )
        row["errors"] = row_errors(name, row, spec, output)
        row["clear"] = not row["errors"]
        rows[name] = row
        changed = [n for n, h in bindings.items() if sha(Path(n)) != h]
        result = dict(
            scope=__doc__,
            cases=rows,
            required_cases=list(cases),
            complete_required_set=len(rows) == len(cases),
            input_sha256=bindings,
            changed_inputs=changed,
            all_native_checks_clear=not changed and all(r["clear"] for r in rows.values()),
            artifact_sha256={
                str(p): sha(p)
                for n in rows
                for p in [output / (n + ".log"), output / (n + ".stl")]
                if p.exists()
            },
            fused_whole_as_one_part_valid=False,
            complete_review_requires_component_assembly=True,
            physical_qualified=False,
            thermal_qualified=False,
            fabrication_released=False,
        )
        write(output / "verification.json", result)
        print(
            json.dumps(
                dict(
                    case=name,
                    clear=row["clear"],
                    errors=row["errors"],
                    volume=row["statistics"]["volume_mm3"] if row["statistics"] else None,
                )
            ),
            flush=True,
        )
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--openscad", required=True)
    parser.add_argument("--outdir", type=Path, default=OUT)
    args = parser.parse_args()
    r = replay(args.openscad, args.outdir)
    raise SystemExit(0 if r["all_native_checks_clear"] and r["complete_required_set"] else 1)
