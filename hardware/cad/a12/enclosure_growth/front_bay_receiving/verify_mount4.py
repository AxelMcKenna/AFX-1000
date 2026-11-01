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
    result = {
        n: dict(role="part")
        for n in ["new_carrier_geometry", "new_lid_geometry"]
        + ["keeper_" + str(i) for i in range(4)]
        + ["column_" + str(i) for i in range(4)]
    }
    result["screw_receiving_geometry"] = dict(role="review")
    for n in [
        "new_parts_components_collision",
        "new_parts_rear_tails_collision",
        "new_parts_mates_collision",
        "own_PCB_seats_collision",
        "keeper_carrier_collision",
        "screw_carrier_receiving_collision",
        "screw_keeper_receiving_collision",
        "screw_lid_bore_collision",
        "new_parts_existing_electronics_collision",
        "new_parts_existing_controls_collision",
        "new_parts_power_wire_collision",
    ]:
        result[n] = dict(role="empty")
    for n in ["keeper_head_positive_control", "toe_positive_control"]:
        result[n] = dict(role="control", expected_volume=0.008)
    for n in ["uncut_seat_keeper_failure", "unbored_lid_screw_failure"]:
        result[n] = dict(role="witness")
    return result


def checked_row_errors(name, row, definition, output):
    bad = row_errors(name, row, definition, output)
    if name != "new_receiving_inlet_shadow" or bad != ["missing-NoError-or-named-certified-primitive"]:
        return bad
    p = json.loads((ROOT / "generated/port-shadow.json").read_text())
    stats = row["statistics"]
    expected = (
        p["NF233_receiving_body_projection_overlap_mm2"] + p["FPC84_receiving_body_projection_overlap_mm2"]
    ) * 0.1
    if (
        abs(stats["volume_mm3"] - expected) < 0.002
        and stats["closed_oriented_boundary"]
        and not stats["degenerate_triangles_excluded"]
        and all(
            abs(x - y) < 1e-5
            for a, b in zip([stats["min_mm"], stats["max_mm"]], [[38, 168.5, 0], [276.5, 183, 0.1]])
            for x, y in zip(a, b)
        )
    ):
        return []
    return bad


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
    source = closure(ROOT / "mount_variant4/checks.scad")
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
            fr_case="none",
            mount_case=n,
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
        command += ["-o", str(target), str(ROOT / "mount_variant4/checks.scad")]
        result = subprocess.run(command, capture_output=True, text=True)
        (output / (n + ".log")).write_text(result.stdout + result.stderr)
        row = dict(
            role=definitions[n]["role"],
            command=command,
            returncode=result.returncode,
            statistics=mesh(target) if target.exists() else None,
        )
        row["errors"] = checked_row_errors(n, row, definitions[n], output)
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
