"""Fresh native receiving fit; missing material or failed execution never passes."""

import argparse
import json
import math
import subprocess
import time
from pathlib import Path

from hardware.cad.a12.thermal.enlarged_base.verify import mesh

from .capture import ROOT, closure, sha, write

ENGINE = Path("/Users/axelmckrnna/Applications/OpenSCAD-2026.10.27.app/Contents/MacOS/OpenSCAD")


def specs():
    out = {}
    for board in ["NF265", "FPC91"]:
        for n in ["PCB_geometry", "components_geometry", "tails_geometry", "mates_geometry"]:
            out[board + "_" + n] = dict(role="solid-review")
        for n in [
            "body_case_collision",
            "body_electronics_collision",
            "body_controls_collision",
            "body_power_collision",
            "body_wires_collision",
            "mate_other_components_collision",
            "mate_mutual_collision",
            "rear_tail_component_collision",
        ]:
            out[board + "_" + n] = dict(role="empty")
        out[board + "_PCB_positive_control"] = dict(role="control", expected_volume=0.008)
    out["strain_geometry"] = dict(role="solid-review")
    for n in [
        "boards_and_receivers_mutual_collision",
        "strain_case_collision",
        "strain_electronics_collision",
        "strain_controls_collision",
        "strain_power_collision",
        "strain_wires_collision",
        "strain_other_board_collision",
        "strain_NF_components_collision",
        "strain_NF_rear_tails_collision",
        "strain_NF_mates_collision",
        "new_mount_components_collision",
        "new_mount_rear_tails_collision",
        "new_mount_mates_collision",
        "new_mount_strain_collision",
        "new_mount_own_PCB_seats_collision",
        "stripped_force_min_bore_collision",
        "strain_mount_min_bore_collision",
    ]:
        out[n] = dict(role="empty")
    for n in ["strain_positive_control", "new_mount_positive_control", "FPC_U401_positive_control"]:
        out[n] = dict(role="control", expected_volume=0.008)
    return out


def errors(name, row, spec, output):
    bad = []
    log = (output / (name + ".log")).read_text()
    target = output / (name + ".stl")
    if "WARNING" in log or "ERROR" in log:
        bad.append("native-warning-or-error")
    if spec["role"] == "empty":
        if (
            row["returncode"] != 1
            or "Current top level object is empty." not in log
            or target.exists()
            or row.get("statistics") is not None
        ):
            bad.append("nonempty-or-execution-failed")
        return bad
    if row["returncode"] != 0 or not target.is_file():
        return bad + ["required-solid-missing"]
    stat = mesh(target)
    if stat != row.get("statistics") or stat["volume_mm3"] <= 0.001:
        bad.append("actual-saved-solid-mismatch")
    if "NoError" not in log:
        bad.append("Boolean-status-not-NoError")
    if not stat["closed_oriented_boundary"] or stat["degenerate_triangles_excluded"]:
        bad.append("not-strict-closed-oriented-nonzero-mesh")
    if "expected_volume" in spec and not math.isclose(
        stat["volume_mm3"], spec["expected_volume"], abs_tol=2e-6
    ):
        bad.append("positive-control-volume")
    return bad


def variables(name):
    cfg = json.loads(
        (ROOT / "inputs/hardware/cad/a12/enclosure_growth/unified_airpath/model/config.json").read_text()
    )
    values = {
        k: "none"
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
            "fi_case",
            "fi_fa_case",
            "ht_case",
            "ap_case",
            "ua_case",
            "fr_case",
            "mount_case",
            "case_name",
        ]
    }
    values.update(
        nf_case=name,
        body_width=334,
        body_depth=188.4,
        shell_height=45.6,
        panel_z=43.6,
        fasteners=cfg["fasteners"],
        board_mounts=cfg["mounts"],
        rear_ports=cfg["rear_ports"],
        openings=cfg["openings"],
    )
    return values


def run(output, names=None):
    output = Path(output).resolve()
    if output.exists() or (ROOT / "handoff.json").exists():
        raise RuntimeError("New output required; captured replay never overwrites")
    cap = json.loads((ROOT / "capture.json").read_text())
    assert all(sha(ROOT / n) == h for n, h in cap["copied_input_sha256"].items())
    model = json.loads((ROOT / "generated/model.json").read_text())
    assert model["electrical_parts"] == 356 and model["total_native_FPs"] == 358
    bound = closure(ROOT / "checks.scad")
    for n in [
        "capture.json",
        "model.py",
        "verify.py",
        "checks.scad",
        "generated/model.json",
        "generated/derived-model-replacement.json",
    ]:
        bound[ROOT / n] = sha(ROOT / n)
    for n, h in cap["copied_input_sha256"].items():
        bound[ROOT / n] = h
    bound[ENGINE] = sha(ENGINE)
    definitions = specs()
    names = names or list(definitions)
    assert len(names) == len(set(names)) and all(n in definitions for n in names)
    output.mkdir(parents=True)
    v = subprocess.run([str(ENGINE), "--version"], text=True, capture_output=True)
    assert v.returncode == 0 and "2026.10.27" in v.stdout + v.stderr
    rows = {}
    for name in names:
        target = output / (name + ".stl")
        command = [
            str(ENGINE),
            "--backend=Manifold",
            "--hardwarnings",
            "--export-format=binstl",
            "-o",
            str(target),
        ]
        for k, value in variables(name).items():
            command += ["-D", k + "=" + json.dumps(value)]
        command += [str(ROOT / "checks.scad")]
        started = time.time()
        result = subprocess.run(command, text=True, capture_output=True)
        (output / (name + ".log")).write_text(result.stdout + result.stderr)
        row = dict(
            returncode=result.returncode,
            command=command,
            elapsed_seconds=time.time() - started,
            statistics=mesh(target) if target.exists() else None,
        )
        row["errors"] = errors(name, row, definitions[name], output)
        row["clear"] = not row["errors"]
        rows[name] = row
        changed = [str(p) for p, h in bound.items() if not p.is_file() or sha(p) != h]
        report = dict(
            required_cases=names,
            cases=rows,
            complete_set=names == list(definitions) and len(rows) == len(names),
            changed_inputs=changed,
            input_sha256={str(p): h for p, h in bound.items()},
            artifact_sha256={str(p): sha(p) for p in output.iterdir() if p.suffix in {".log", ".stl"}},
            all_requested_clear=len(rows) == len(names)
            and all(r["clear"] for r in rows.values())
            and not changed,
            engine_version=v.stdout + v.stderr,
            electrical_parts=356,
            native_FPs=358,
            source_NF_opens=499,
            scope="actual356parts receiving geometry; oldUAcase/P03/E28explicit capture; local connector wiring only",
            physical_qualified=False,
            electrical_qualified=False,
            thermal_qualified=False,
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
    parser = argparse.ArgumentParser()
    parser.add_argument("--outdir", required=True, type=Path)
    parser.add_argument("--cases", nargs="+")
    a = parser.parse_args()
    raise SystemExit(not run(a.outdir, a.cases)["all_requested_clear"])
