"""Pinned-native receiving fit; failed geometry and unknown dimensions stay explicit."""

import argparse
import json
import subprocess
from pathlib import Path

from hardware.cad.a12.enclosure_growth.r1_local.stage import closure
from hardware.cad.a12.thermal.interior_airpath.verify import mesh, row_errors

from .capture import ROOT, UA, sha

RUNNER = ROOT.parent / "r1_local/linux_runner/openscad.py"


def specs():
    result = {}
    for ident in ["NF233", "FPC84"]:
        for name in ["PCB_geometry", "components_geometry"]:
            result[ident + "_" + name] = dict(role="review")
        for name in [
            "body_case_collision",
            "body_electronics_collision",
            "body_controls_collision",
            "body_power_collision",
            "body_wires_collision",
            "short_bundle_case_collision",
            "short_bundle_electronics_collision",
            "short_bundle_power_controls_collision",
            "mate_other_components_collision",
            "mate_mutual_collision",
            "nominal_native_drill_calibration_collision",
        ]:
            result[ident + "_" + name] = dict(role="empty")
    result["boards_and_receivers_mutual_collision"] = dict(role="empty")
    for name in ["NF_PCB_positive_control", "FPC_PCB_positive_control"]:
        result[name] = dict(role="control", expected_volume=0.008)
    result["new_receiving_inlet_shadow"] = dict(role="review")
    return result


def run(output, names=None):
    output = Path(output).resolve()
    if output.exists() or (ROOT / "handoff.json").exists():
        raise RuntimeError("New output required")
    for filename, key in [
        ("capture.json", "copied_input_sha256"),
        ("NF233-delta-capture.json", "copied_input_sha256"),
    ]:
        d = json.loads((ROOT / filename).read_text())
        assert all(sha(ROOT / n) == h for n, h in d[key].items())
    parent = json.loads((UA / "handoff.json").read_text())
    assert all(sha(UA / n) == h for n, h in parent["files_sha256"].items())
    runner = json.loads((RUNNER.parent / "handoff.json").read_text())
    assert all(sha(RUNNER.parent / n) == h for n, h in runner["files_sha256"].items())
    source = closure(ROOT / "checks.scad")
    for p in ROOT.rglob("*"):
        if (
            p.is_file()
            and "__pycache__" not in p.parts
            and "history" not in p.parts
            and not p.is_relative_to(ROOT / "generated/native")
        ):
            source[p] = sha(p)
    for p in [UA / "handoff.json", RUNNER.parent / "handoff.json"]:
        source[p] = sha(p)
    for n in runner["files_sha256"]:
        source[RUNNER.parent / n] = sha(RUNNER.parent / n)
    cfg = json.loads((UA / "model/config.json").read_text())
    source[UA / "model/config.json"] = sha(UA / "model/config.json")
    definitions = specs()
    names = names or list(definitions)
    if any(n not in definitions for n in names):
        raise ValueError("Unknown receiving case")
    output.mkdir(parents=True)
    rows = {}
    for n in names:
        variables = {
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
            ]
        }
        variables.update(
            fr_case=n,
            body_width=334,
            body_depth=188.4,
            shell_height=45.6,
            panel_z=43.6,
            fasteners=cfg["fasteners"],
            board_mounts=cfg["mounts"],
            rear_ports=cfg["rear_ports"],
            openings=cfg["openings"],
        )
        command = [str(RUNNER), "--hardwarnings", "--backend", "Manifold", "--export-format", "binstl"]
        for k, v in variables.items():
            command += ["-D", k + "=" + json.dumps(v)]
        target = output / (n + ".stl")
        command += ["-o", str(target), str(ROOT / "checks.scad")]
        result = subprocess.run(command, capture_output=True, text=True)
        (output / (n + ".log")).write_text(result.stdout + result.stderr)
        row = dict(
            role=definitions[n]["role"],
            command=command,
            returncode=result.returncode,
            statistics=mesh(target) if target.exists() else None,
        )
        row["errors"] = row_errors(n, row, definitions[n], output)
        row["clear"] = not row["errors"]
        rows[n] = row
        changed = [str(p) for p, h in source.items() if sha(p) != h]
        data = dict(
            required_cases=names,
            cases=rows,
            complete_set=names == list(definitions),
            changed_inputs=changed,
            input_sha256={str(p): h for p, h in source.items()},
            artifact_sha256={str(p): sha(p) for p in output.iterdir() if p.suffix in [".log", ".stl"]},
            all_requested_clear=all(r["clear"] for r in rows.values()) and not changed,
            NF_parts=233,
            FPC_parts=84,
            NF_source="copied9fe0966b priorUUIDsnapshot",
            FPC_source="copied9a4c6046 placementcheckpoint",
            later_FPC_routing_incorporated=False,
            projected_shadow_not_airflow_proof=True,
            physical_qualified=False,
            thermal_qualified=False,
            electrical_qualified=False,
            fabrication_released=False,
            full_harness_qualified=False,
        )
        (output / "verification.json").write_text(json.dumps(data, indent=2) + "\n")
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
    return data


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--outdir", required=True, type=Path)
    p.add_argument("--cases", nargs="+")
    a = p.parse_args()
    raise SystemExit(not run(a.outdir, a.cases)["all_requested_clear"])
