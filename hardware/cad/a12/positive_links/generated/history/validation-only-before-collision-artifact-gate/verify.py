"""Source-bound native collision screens; failures remain reviewable evidence."""

import argparse
import json
import math
import struct
import subprocess
from pathlib import Path

from hardware.cad.a12.thermal.verify import binary_stl

from .generate import OUT, REPO, ROOT, sha


def stale_paths(hashes, base):
    return [
        path
        for path, expected in hashes.items()
        if not (base / path).is_file() or sha(base / path) != expected
    ]


COLLISION_CASES = (
    "case_collision",
    "electronics_collision",
    "returns_collision",
    "pair_collision",
    "support_case_collision",
    "support_electronics_collision",
    "support_returns_collision",
)
REQUIRED_CASES = ("copper", "positive_control", "support_positive_control")
CASE_NAMES = ("copper", *COLLISION_CASES, "support_positive_control", "positive_control")


def finite_volume(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
        and value >= 0
    )


def gate_errors(report, geometry):
    errors = []
    checks = report.get("native_checks", {})
    if set(checks) != set(CASE_NAMES):
        errors.append("native case inventory mismatch")
    for name in COLLISION_CASES:
        row = checks.get(name, {})
        volume = row.get("volume_mm3")
        if (
            row.get("result") not in ("empty", "valid native manifold")
            or not finite_volume(volume)
            or volume > 1e-6
        ):
            errors.append("failed collision: " + name)
    for name in REQUIRED_CASES:
        row = checks.get(name, {})
        if (
            row.get("result") != "valid native manifold"
            or not finite_volume(row.get("volume_mm3"))
            or row.get("volume_mm3", 0) <= 0
        ):
            errors.append("missing required geometry: " + name)
    try:
        volumes = [geometry[n + "-CU"]["volume_mm3"] for n in ("ANA", "DIG")]
        if any(not finite_volume(value) or value <= 0 for value in volumes):
            raise ValueError("invalid nominal Cu volume")
        expected = sum(volumes)
        actual = checks["copper"]["volume_mm3"]
        if (
            not finite_volume(expected)
            or expected <= 0
            or not finite_volume(actual)
            or abs(actual - expected) / expected >= 0.0005
        ):
            errors.append("copper volume mismatch")
    except (KeyError, TypeError, ValueError):
        errors.append("missing copper volume contract")
    for name in REQUIRED_CASES[1:]:
        value = checks.get(name, {}).get("volume_mm3")
        if not finite_volume(value) or not math.isclose(value, 0.008, rel_tol=0.005, abs_tol=1e-6):
            errors.append("failed positive control: " + name)
    if report.get("positive_control_detected") is not True:
        errors.append("positive controls not detected")
    for key in ("stale_sources", "native_inputs_changed_during_run", "native_failures", "collision_failures"):
        if report.get(key) != []:
            errors.append("failed evidence: " + key)
    return errors


def saved_report_errors(report, geometry, folder):
    errors = gate_errors(report, geometry)
    for group in ("source_sha256", "geometry_sha256", "native_input_sha256", "native_evidence_sha256"):
        hashes = report.get(group)
        if not isinstance(hashes, dict) or not hashes:
            errors.append("missing hash group: " + group)
        else:
            errors.extend(group + ": " + p for p in stale_paths(hashes, REPO))
    for name in REQUIRED_CASES:
        path = folder / ("native-" + name + ".stl")
        try:
            actual = binary_stl(path)
            if any(report.get("native_checks", {}).get(name, {}).get(k) != v for k, v in actual.items()):
                errors.append("actual native STL disagrees: " + name)
        except (OSError, ValueError, AssertionError, struct.error):
            errors.append("missing/invalid actual native STL: " + name)
    return errors


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--openscad")
    parser.add_argument("--check-report", type=Path)
    parser.add_argument("--geometry", type=Path, default=OUT / "geometry.json")
    args = parser.parse_args(argv)
    if args.check_report:
        report = json.loads(args.check_report.read_text())
        geometry = json.loads(args.geometry.read_text())
        errors = saved_report_errors(report, geometry, args.check_report.parent)
        print(json.dumps({"validation_errors": errors, "accepted_native_evidence": not errors}))
        return 1 if errors else 0
    if not args.openscad:
        parser.error("--openscad is required for native execution")
    packet = json.loads((OUT / "obstacles.json").read_text())
    geometry = json.loads((OUT / "geometry.json").read_text())
    stale_before = stale_paths(packet["source_sha256"], REPO) + stale_paths(geometry["source_sha256"], ROOT)
    if stale_before:
        raise ValueError({"refuse_native_check_with_stale_snapshot": stale_before})
    geometry_hashes = {
        str(q.relative_to(REPO)): sha(q)
        for q in OUT.glob("*")
        if q.suffix in (".step", ".stl") and not q.name.startswith("native-")
    }
    checks = {}
    native_input_hashes = {
        str((OUT / "collisions.scad").relative_to(REPO)): sha(OUT / "collisions.scad"),
        **{path: value for path, value in geometry_hashes.items() if path.endswith(".stl")},
    }
    for name in CASE_NAMES:
        target = OUT / ("native-" + name + ".stl")
        target.unlink(missing_ok=True)
        cmd = [args.openscad, "--hardwarnings", "--backend", "Manifold", "--export-format", "binstl"]
        for value in ['part="positive_only"', 'thermal_part="positive_only"', f'positive_part="{name}"']:
            cmd += ["-D", value]
        cmd += ["-o", str(target), str(OUT / "collisions.scad")]
        try:
            run = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        except subprocess.TimeoutExpired as error:
            log = "Native subprocess exceeded180second budget; rejected without collision inference.\n" + str(
                error
            )
            (OUT / ("native-" + name + ".log")).write_text(log)
            checks[name] = dict(result="native timeout", accepted=False, timeout_seconds=180)
            continue
        log = run.stdout + run.stderr
        (OUT / ("native-" + name + ".log")).write_text(log)
        if (
            name in COLLISION_CASES
            and run.returncode == 1
            and "Current top level object is empty." in log
            and "WARNING" not in log
            and "ERROR" not in log
        ):
            checks[name] = dict(result="empty", volume_mm3=0)
        elif run.returncode == 0 and "NoError" in log and "WARNING" not in log and "ERROR" not in log:
            try:
                checks[name] = dict(result="valid native manifold", **binary_stl(target))
            except (OSError, ValueError, AssertionError, struct.error) as error:
                checks[name] = dict(
                    result="native failure", returncode=run.returncode, log=log, parse_error=str(error)
                )
        else:
            checks[name] = dict(result="native failure", returncode=run.returncode, log=log)
    failures = [
        name for name, row in checks.items() if name.endswith("collision") and row.get("volume_mm3", 1) > 1e-6
    ]
    positive = all(
        checks[key].get("volume_mm3", 0) > 0.007 for key in ("positive_control", "support_positive_control")
    )
    evidence_hashes = {
        str(q.relative_to(REPO)): sha(q) for q in OUT.glob("native-*") if q.suffix in (".log", ".stl")
    }
    stale = stale_paths(packet["source_sha256"], REPO) + stale_paths(geometry["source_sha256"], ROOT)
    changed_inputs = [
        path
        for path, expected in native_input_hashes.items()
        if not (REPO / path).is_file() or sha(REPO / path) != expected
    ]
    report = dict(
        native_checks=checks,
        geometry_sha256=geometry_hashes,
        native_input_sha256=native_input_hashes,
        native_evidence_sha256=evidence_hashes,
        native_inputs_changed_during_run=changed_inputs,
        simulator_version=subprocess.run(
            [args.openscad, "--version"], capture_output=True, text=True
        ).stderr.strip(),
        collision_failures=failures,
        native_failures=[
            key for key, row in checks.items() if row["result"] not in ("empty", "valid native manifold")
        ],
        positive_control_detected=positive,
        stale_sources=stale,
        source_sha256=packet["source_sha256"],
        all_component_mate_heights_approved=False,
        cover_and_restraint_qualified=False,
        electrical_joint_qualified=False,
        physical_fit_verified=False,
        fabrication_released=False,
        selected_for_production=False,
    )
    report["validation_errors"] = saved_report_errors(report, geometry, OUT)
    report["accepted_native_evidence"] = not report["validation_errors"]
    (OUT / "verification.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return 0 if report["accepted_native_evidence"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
