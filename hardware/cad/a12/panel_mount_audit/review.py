"""Independent portable transform and captured-source checks."""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def errors(report=None, source_root=None):
    p = report if report is not None else json.loads((ROOT / "report.json").read_text())
    baseline = json.loads((ROOT / "baseline-other.json").read_text())
    problems = []
    expected_panel_boards = {"meter_board", "bpm_board", "settings_board", "release_select_board"}
    expected_panel_env = {
        "bpm_digits",
        "settings_switch",
        "release_select_switch",
        "input_pot",
        "output_pot",
        "low_pot",
        "mid_pot",
        "high_pot",
        "scene_depth_pot",
        "x_level_pot",
        "x_pitch_pot",
        "scene_time_pot",
        "scene_resonance_pot",
        "angle_sensor_board",
        "angle_sensor",
    }
    for key in ["boards", "envelopes", "board_mounts", "daughterboard_mounts"]:
        rows = p.get(key, [])
        if len(rows) != len(baseline[key]):
            problems.append(key + " coverage")
            continue
        for i, (r, b) in enumerate(zip(rows, baseline[key])):
            if (
                r.get("index") != i
                or r.get("collection") != key
                or r.get("id") != b[0]
                or r.get("baseline") != b
            ):
                problems.append(key + ": identity " + str(i))
                continue
            if key == "boards":
                expected = None if b[0] == "trill_craft" else 7.6 if b[0] in expected_panel_boards else 0
            elif key == "envelopes":
                expected = None if b[0] == "trill_components" else 7.6 if b[0] in expected_panel_env else 0
            elif key == "board_mounts":
                expected = 7.6 if b[0] == "lever" else 0
            else:
                expected = 0
            actual = r.get("translation_xyz_mm")
            want = None if expected is None else [0, 0, expected]
            if actual != want:
                problems.append(key + ": transform " + str(i))
            if expected is None:
                if r.get("candidate") is not None or r.get("classification") != "unknown":
                    problems.append(key + ": unknown " + str(i))
            else:
                new = list(b)
                new[3] = round(b[3] + expected, 10)
                if r.get("candidate") != new:
                    problems.append(key + ": candidate " + str(i))
            if not r.get("source_origin") or r.get("physical_qualified") is not False:
                problems.append(key + ": provenance/claim " + str(i))
    for claim in [
        "native_fit_qualified",
        "physical_qualified",
        "fabrication_released",
        "shared_sources_modified",
    ]:
        if p.get(claim) is not False:
            problems.append(claim)
    lever = p.get("lever_group", {})
    if lever.get("candidate_pivot_xyz_mm") != [316, 82, 31.6] or lever.get("translation_xyz_mm") != [
        0,
        0,
        7.6,
    ]:
        problems.append("lever pivot")
    if lever.get("coupled_envelope_ids") != ["angle_sensor_board", "angle_sensor"]:
        problems.append("lever sensor coupling")
    if lever.get("coupled_mount_indices") != [
        i for i, b in enumerate(baseline["board_mounts"]) if b[0] == "lever"
    ]:
        problems.append("lever mount coupling")
    modules = {r["id"]: r for r in p.get("panel_modules", [])}
    buttons = modules.get("a12_switch_electronics", {})
    if len(set(buttons.get("instance_ids", []))) != 29 or buttons.get("lead_solder_z_mm") != [
        [22.7, 27.2],
        [30.3, 34.8],
    ]:
        problems.append("controlled switch bank")
    if buttons.get("body_z_mm") != [[27.2, 31.7], [34.8, 39.3]]:
        problems.append("controlled switch body")
    if any(
        m.get("translation_xyz_mm") != [0, 0, 7.6] or m.get("qualification") is not False
        for m in modules.values()
    ):
        problems.append("panel module transforms")
    if p.get("fixed_rear", {}).get("translation_xyz_mm") != [0, 0, 0]:
        problems.append("rear moved")
    src = source_root or ROOT / "sources"
    for name, h in p.get("source_sha256", {}).items():
        f = src / name
        if not f.is_file() or hashlib.sha256(f.read_bytes()).hexdigest() != h:
            problems.append("captured source: " + name)
    if hashlib.sha256((ROOT / "baseline-other.json").read_bytes()).hexdigest() != p.get(
        "baseline_other_sha256"
    ):
        problems.append("baseline hash")
    return problems


if __name__ == "__main__":
    found = errors()
    print(json.dumps(dict(errors=found, source_geometry_classified=not found, physical_qualified=False)))
    raise SystemExit(bool(found))
