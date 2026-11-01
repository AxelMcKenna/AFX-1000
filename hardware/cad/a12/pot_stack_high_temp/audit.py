"""Independent saved-native and axial/receiving-contract checks; no tools launched."""

import json
import math
from pathlib import Path

from hardware.cad.a12.thermal.enlarged_base_pot.stage import closure

from .contract import report
from .stage import FI, MODEL, OUT, ROOT, sha
from .verify import errors as row_errors
from .verify import specifications


def contract_errors(data):
    bad = []
    f = data["source_facts"]
    r = data["receiving_requirements_not_manufacturer_guarantees"]
    d = data["derived"]
    tip = [r["shoulder_z"][i] + r["shaft_L1"][i] for i in [0, 1]]
    flat_start = tip[1] - r["flat_length"][0]
    usable_end = tip[0] - .8  # Actual nominal C0.8 chamfer; its formal tolerance is still open.
    half = r["grub_axial_gauge_diameter"] / 2
    gauge = [r["knob_base_z"][0] + r["grub_axis_local"] - r["grub_axis_error"] - half,
        r["knob_base_z"][1] + r["grub_axis_local"] + r["grub_axis_error"] + half]
    reserve = r["axial_flat_reserve"]
    if gauge[0] < flat_start + reserve or gauge[1] > usable_end - reserve:
        bad.append("grub-gauge-outside-allocated-flat")
    if r["knob_base_z"][0] + r["blind_bore_depth"] - tip[1] < 1 - 1e-9:
        bad.append("less-than-required-tip-clearance")
    if r["knob_smallest_height"] - r["blind_bore_depth"] < 2:
        bad.append("less-than-required-knob-roof")
    for expected, actual in [(d["allocated_shaft_tip_z"], tip), (d["new_grub_gauge_z"], gauge)]:
        if any(not math.isclose(x, y, abs_tol=1e-10) for x, y in zip(expected, actual)):
            bad.append("declared-axial-corner-does-not-match")
    if not math.isclose(flat_start, d["allocated_flat_start_max_z"], abs_tol=1e-10):
        bad.append("wrong-flat-start-datum")
    if not math.isclose(43.6 - f["shoulder_to_substrate"], 33.6, abs_tol=1e-10):
        bad.append("wrong-substrate-datum")
    margin = .12 + r["geometry_radial_reserve"]
    x_extent = f["antirotation_lug_width"][1] / 2 + margin
    y_extent = [f["lug_radial_centre"][0] - f["lug_radial_thickness"][1] / 2 - margin,
        f["lug_radial_centre"][1] + f["lug_radial_thickness"][1] / 2 + margin]
    if x_extent > r["blind_lug_pocket_width"] / 2 or y_extent[0] < r["blind_lug_pocket_radial_y"][0] or y_extent[1] > r["blind_lug_pocket_radial_y"][1]:
        bad.append("lug-pocket-insufficient")
    if r["pocket_z"][1] < r["shoulder_z"][1] + f["antirotation_lug_projection"][1]:
        bad.append("lug-pocket-too-shallow")
    if f["temperature_c"] != [-10, 70] or f["all_metal_lugs_must_be_soldered_into_substrate"] is not True:
        bad.append("manufacturer-constraint-lost")
    for flag in ["physical_qualified", "thermal_qualified", "electrical_qualified", "fabrication_released", "adopted"]:
        if data[flag] is not False:
            bad.append("unsupported-approval:" + flag)
    return bad


def native_errors(data, folder, expected_names=None):
    bad = []
    specs = specifications()
    expected_names = list(specs) if expected_names is None else expected_names
    if list(data["cases"]) != expected_names or data["requested_cases"] != expected_names:
        bad.append("incomplete-or-reordered-native-coverage")
    if not data["all_requested_clear"] or data["changed_inputs"]:
        bad.append("failed-or-stale-native-receipt")
    if data["required_cases"] != list(specs) or data["complete_set"] != (expected_names == list(specs)):
        bad.append("incorrect-complete-set-claim")
    for name, row in data["cases"].items():
        if name not in specs:
            bad.append("unknown-case:" + name)
            continue
        spec = specs[name]
        if row["role"] != spec["role"] or not row["clear"] or row["errors"]:
            bad.append("failed-role-or-result:" + name)
        cmd = row["command"]
        for k, v in dict(ht_case=spec["value"], ht_i=spec.get("i", 0), ht_family=spec.get("family", 0)).items():
            if cmd.count(k + "=" + json.dumps(v)) != 1:
                bad.append("wrong-native-selector:" + name)
        bad += [name + ":" + e for e in row_errors(name, row, spec, folder)]
        if name.startswith("hardware_") and name.endswith("_control") and row.get("statistics"):
            bad += control_bounds_errors(name, row["statistics"])
    return bad


def control_bounds_errors(name, stats):
    text=(MODEL / "context-derived.scad").read_text()
    line=next(l for l in text.splitlines() if l.startswith("ps_centres="))
    centres=json.loads(line.split("=",1)[1].rstrip(";"))
    i=int(name.split("_")[1])
    p=centres[i]
    expected=[[p[0]+3.9,p[1]-.1,47],[p[0]+4.1,p[1]+.1,47.2]]
    if any(abs(a-b)>1e-4 for points,actual in zip(expected,[stats["min_mm"],stats["max_mm"]]) for a,b in zip(points,actual)):
        return ["wrong-index-control-bounds:"+name]
    return []


def errors():
    bad = contract_errors(report())
    capture = json.loads((ROOT / "capture.json").read_text())
    if sha(FI / "handoff.json") != capture["parent_handoff_sha256"]:
        bad.append("parent-seal-changed")
    parent = json.loads((FI / "handoff.json").read_text())
    for n, h in parent["files_sha256"].items():
        if sha(FI / n) != h:
            bad.append("parent-file-changed:" + n)
    for n, h in capture["captured_model_sha256"].items():
        if sha(ROOT / n) != h:
            bad.append("captured-model-changed:" + n)
    for p in closure(OUT / "checks.scad"):
        if not p.is_relative_to(ROOT):
            bad.append("uncaptured-SCAD-dependency:" + str(p))
    s = (MODEL / "context-derived.scad").read_text()
    if "h=min(10.8,h-2)+0.1" not in s or "translate([0,0,5]) rotate" not in s or "translate([6,0,5]) rotate" not in s:
        bad.append("missing-revised-inner-knob-geometry")
    cfg = json.loads((OUT / "config.json").read_text())
    original_cfg = json.loads((FI / "generated/config.json").read_text())
    if cfg != original_cfg:
        bad.append("unexpected-global-XY-panel-or-board-change")
    if json.loads((OUT / "analysis.json").read_text()) != report():
        bad.append("source-contract-report-differs")
    for folder, names in [(OUT / "full", None), (OUT / "preflight", None)]:
        d = json.loads((folder / "verification.json").read_text())
        bad += native_errors(d, folder, list(d["requested_cases"]) if folder.name == "preflight" else names)
        for key in ["input_sha256", "artifact_sha256"]:
            for n, h in d[key].items():
                if sha(Path(n)) != h:
                    bad.append("native-source-or-artifact-changed:" + n)
    drawing=json.loads((OUT / "drawing-provenance.json").read_text())
    for n,h in drawing["source_sha256"].items():
        if sha(ROOT/n)!=h:
            bad.append("drawing-source-changed:"+n)
    for n,h in drawing["artifacts_sha256"].items():
        if sha(OUT/n)!=h:
            bad.append("drawing-artifact-changed:"+n)
    webs=json.loads((OUT / "panel-webs.json").read_text())
    for n,h in webs["source_sha256"].items():
        if sha(ROOT/n)!=h:
            bad.append("panel-web-source-changed:"+n)
    if len(webs["rows"])!=10 or not math.isclose(webs["min_own_bore_web_mm"],.35,abs_tol=1e-10) or webs["min_other_planar_gap_mm"]<=0 or webs["strength_or_process_qualified"] is not False:
        bad.append("incorrect-panel-web-or-strength-claim")
    return bad


if __name__ == "__main__":
    result = errors()
    print(json.dumps(dict(errors=result)))
    raise SystemExit(bool(result))
