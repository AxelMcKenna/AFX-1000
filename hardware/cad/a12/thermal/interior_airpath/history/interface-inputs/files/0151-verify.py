"""AP02 fresh native screening, source-bound and never overwriting evidence."""

import argparse
import json
import math
import subprocess
from pathlib import Path

from hardware.cad.a12.thermal.enlarged_base.verify import mesh

from .polygon_contract import primitive_contracts, primitive_errors
from .stage import MODEL, OUT, ROOT, sha, write


def specs():
    result = {}
    for n in [
        "inlet_area_gauge",
        "exhaust_area_gauge",
        "guard_area_gauge",
        "base_geometry",
        "carrier_geometry",
        "tray_geometry",
        "guard_geometry",
        "upper_gasket_geometry",
        "frame_gasket_geometry",
        "shim_geometry",
        "meter_plate_geometry",
        "meter_gasket_geometry",
        "fastener_seal_geometry",
    ]:
        result[n] = dict(role="part")
    for n in ["meter_fastener_receiving", "fan_receiving_geometry"]:
        result[n] = dict(role="review")
    for n in [
        "inlet_solid_void_collision",
        "exhaust_solid_void_collision",
        "new_pin_void_collision",
        "fan_baffle_collision",
        "meter_fan_collision",
        "pins_baffle_collision",
        "meter_pins_collision",
        "fan_tray_collision",
        "tray_base_collision",
        "new_added_case_collision",
        "floating_fan_hole_collision",
        "floating_tray_hole_collision",
        "floating_guard_hole_collision",
        "floating_shim_hole_collision",
        "matched_shim_min_collision",
        "matched_shim_max_collision",
        "nominal_pressure_boundary_void_collision",
    ] + ["new_added_obstacle_" + str(i) for i in range(5)]:
        result[n] = dict(role="empty")
    for n in [
        "old_plate_blockage_control",
        "old_floor_blockage_control",
        "old_wall_blockage_control",
        "protected_post_island_metal_control",
        "protected_post_island_floor_control",
        "post_island_join_control",
        "retained_pin_control",
        "void_fixture_metal_level_control",
        "void_fixture_floor_level_control",
        "meter_border_positive_control",
    ]:
        result[n] = dict(role="control", expected_volume=0.008)
    for n in ["fixed_axis_hole_failure_witness", "old_open_plenum_failure_witness"]:
        result[n] = dict(role="witness")
    return result


def row_errors(n, row, spec, folder):
    bad = []
    target = folder / (n + ".stl")
    log = (folder / (n + ".log")).read_text()
    if "WARNING" in log or "ERROR" in log:
        bad.append("native-warning/error")
    if spec["role"] == "empty":
        if (
            row["returncode"] != 1
            or "Current top level object is empty." not in log
            or target.exists()
            or row.get("statistics") is not None
        ):
            bad.append("actual-nonempty-or-failed-execution")
        return bad
    if row["returncode"] != 0 or not target.exists():
        return bad + ["missing-actual-required-solid"]
    m = mesh(target)
    if "NoError" not in log:
        if n in primitive_contracts() and "Top level object is a 3D object (PolySet)" in log:
            bad += primitive_errors(n, m)
        else:
            bad.append("missing-NoError-or-named-certified-primitive")
    if m != row.get("statistics") or m["volume_mm3"] <= 0.001:
        bad.append("wrong-actual-solid")
    if spec["role"] != "review" and (not m["closed_oriented_boundary"] or m["degenerate_triangles_excluded"]):
        bad.append("strict-part/control-topology")
    if "expected_volume" in spec and not math.isclose(m["volume_mm3"], spec["expected_volume"], abs_tol=2e-6):
        bad.append("wrong-positive-control")
    return bad


def run(executable, output, names=None):
    output = Path(output).resolve()
    if output.exists() or ((ROOT / "handoff.json").exists() and output.is_relative_to(ROOT)):
        raise RuntimeError("Native output requires a new destination")
    capture = json.loads((ROOT / "capture.json").read_text())
    assert all(sha(ROOT / n) == h for n, h in capture["private_model_sha256"].items())
    runner = Path(executable).resolve()
    sealpath = runner.parent / "handoff.json"
    runnerseal = json.loads(sealpath.read_text())
    assert runnerseal["fresh_controls_passed"] and all(
        sha(runner.parent / n) == h for n, h in runnerseal["files_sha256"].items()
    )
    files = [p for p in MODEL.rglob("*") if p.is_file()]
    files += [
        ROOT / n
        for n in [
            "capture.json",
            "stage.py",
            "plan.py",
            "geometry.scad",
            "verify.py",
            "polygon_contract.py",
            "fan_geometry.py",
            "common_land.py",
            "gasket-source.json",
        ]
    ]
    files += [
        OUT / n
        for n in [
            "checks.scad",
            "source-tray.scad",
            "config.json",
            "analysis.json",
            "nominal-frame-land.stl",
            "nominal-common-land.stl",
            "fan-geometry.json",
            "common-land.json",
        ]
    ]
    files += [runner.parent / n for n in runnerseal["files_sha256"]] + [sealpath]
    bindings = {str(p): sha(p) for p in files}
    cfg = json.loads((OUT / "config.json").read_text())
    definitions = specs()
    names = names or list(definitions)
    assert all(n in definitions for n in names)
    output.mkdir(parents=True)
    rows = {}
    for n in names:
        sp = definitions[n]
        v = {
            k: "cp_only"
            for k in [
                "part",
                "thermal_part",
                "positive_part",
                "candidate_case",
                "trial",
                "ui_case",
                "eb_case",
                "ps_case",
                "cp_case",
            ]
        }
        v.update(
            fi_case="fi_only",
            fi_fa_case="fi_only",
            ht_case="none",
            ap_case=n,
            body_width=334,
            body_depth=188.4,
            shell_height=45.6,
            panel_z=43.6,
            fasteners=cfg["fasteners"],
            board_mounts=cfg["mounts"],
            rear_ports=cfg["rear_ports"],
            openings=cfg["openings"],
        )
        cmd = [str(runner), "--hardwarnings", "--backend", "Manifold", "--export-format", "binstl"]
        for k, value in v.items():
            cmd += ["-D", k + "=" + json.dumps(value)]
        target = output / (n + ".stl")
        cmd += ["-o", str(target), str(OUT / "checks.scad")]
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        (output / (n + ".log")).write_text(p.stdout + p.stderr)
        row = dict(
            role=sp["role"],
            returncode=p.returncode,
            command=cmd,
            statistics=mesh(target) if target.exists() else None,
        )
        row["errors"] = row_errors(n, row, sp, output)
        row["clear"] = not row["errors"]
        rows[n] = row
        record = dict(
            cases=rows,
            requested_cases=names,
            required_cases=list(definitions),
            complete_set=names == list(definitions),
            input_sha256=bindings,
            changed_inputs=[p for p, h in bindings.items() if sha(Path(p)) != h],
            artifact_sha256={
                str(p): sha(p)
                for name in rows
                for p in [output / (name + ".log"), output / (name + ".stl")]
                if p.exists()
            },
            all_requested_clear=all(r["clear"] for r in rows.values()),
            runner_handoff_sha256=sha(sealpath),
            runner_image=runnerseal["image"],
            physical_qualified=False,
            thermal_qualified=False,
            installed_airflow_verified=False,
            fabrication_released=False,
        )
        record["all_requested_clear"] &= not record["changed_inputs"]
        write(output / "verification.json", record)
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
    return record


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--openscad", required=True)
    parser.add_argument("--outdir", type=Path, required=True)
    parser.add_argument("--cases", nargs="+")
    args = parser.parse_args()
    raise SystemExit(not run(args.openscad, args.outdir, args.cases)["all_requested_clear"])
