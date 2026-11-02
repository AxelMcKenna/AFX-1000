"""Independent circuit/geometry and drill screening for the R83 land candidate."""

import copy
import json
from pathlib import Path

from shapely.geometry import Point, box
from shapely.strtree import STRtree

from hardware.electronics.common.netlists import netlist
from hardware.electronics.common.sexpr import children, first, read_sexpr, sexpr
from hardware.fabrication.audit_candidate import geometry_delta, native_evidence_errors, sha
from hardware.fabrication.evidence_paths import recorded_path
from hardware.fabrication.rail_monitor_dc_paths import geometry

REPO = Path(__file__).resolve().parents[2]
STAGING = REPO / "hardware/fabrication/staging"
OLD = STAGING / "rail-monitor-reserved-closed-native-02"
NEW = STAGING / "rail-monitor-r83-land-native-01"


def ref(footprint):
    return next(p[2] for p in children(footprint, "property") if p[1] == "Reference")


def check():
    pcb_name = "rail_monitor.kicad_pcb"
    project = NEW / "rail_monitor.kicad_pro"
    receipt_path = NEW / "review.json"
    receipt = json.loads(receipt_path.read_text())
    assert not native_evidence_errors(project, receipt)
    assert receipt["status"]["native_closed"] and receipt["uncapped_open_connections"] == 0
    old, new = [read_sexpr((folder / pcb_name).read_text()) for folder in (OLD, NEW)]
    delta = geometry_delta(old, new)
    assert delta["other_root_geometry_exact"]
    for tag in ("segment", "via", "zone"):
        assert not any(delta[tag].values()), (tag, delta[tag])
    old_fps, new_fps = [{ref(f): f for f in children(tree, "footprint")} for tree in (old, new)]
    assert set(old_fps) == set(new_fps)
    assert not delta["footprint"]["added"] and not delta["footprint"]["removed"]
    assert delta["footprint"]["changed"] == [str(first(old_fps["R83"], "uuid")[1])]
    before, after = old_fps["R83"], new_fps["R83"]
    assert after[1] == "AFX_RailMonitor:Bourns_CRT0805"
    normalized = copy.deepcopy(after)
    normalized[1] = before[1]
    pads = {p[1]: p for p in children(after, "pad")}
    assert set(pads) == {"1", "2"}
    for number, center in (("1", -1.0), ("2", 1.0)):
        pad = pads[number]
        original = next(p for p in children(before, "pad") if p[1] == number)
        assert pad[2:4] == ["smd", "rect"]
        assert list(map(float, first(pad, "at")[1:])) == [center, 0]
        assert list(map(float, first(pad, "size")[1:])) == [1, 1.35]
        for tag in ("net", "uuid", "layers"):
            assert sexpr(first(pad, tag)) == sexpr(first(original, tag))
        normalized[normalized.index(next(p for p in children(normalized, "pad") if p[1] == number))] = copy.deepcopy(original)
    for rectangle in children(normalized, "fp_rect"):
        if first(rectangle, "layer")[1] == "F.CrtYd":
            assert list(map(float, first(rectangle, "start")[1:])) == [-1.75, -0.95]
            assert list(map(float, first(rectangle, "end")[1:])) == [1.75, 0.95]
            original = next(r for r in children(before, "fp_rect") if first(r, "layer")[1] == "F.CrtYd")
            normalized[normalized.index(rectangle)] = copy.deepcopy(original)
    assert sexpr(normalized) == sexpr(before), "Incidental R83 pose, property or graphic change"
    old_parts, old_pins = netlist(OLD / "netlist.xml")
    new_parts, new_pins = netlist(NEW / "netlist.xml")
    assert old_pins == new_pins and set(old_parts) == set(new_parts)
    assert all(old_parts[r].findtext("value") == new_parts[r].findtext("value") for r in old_parts)
    assert {r for r in old_parts if old_parts[r].findtext("footprint") != new_parts[r].findtext("footprint")} == {"R83"}
    capture_path = STAGING / "rail-monitor-dc-inputs-01/capture.json"
    capture = json.loads(capture_path.read_text())
    assert all(sha(recorded_path(name)) == digest for name, digest in capture["source_sha256"].items())
    # Only R83 changed. All other pad polygons retain the native outside-1um
    # capture, which conservatively enlarges copper for this drill-gap screen.
    sx, sy = map(float, first(after, "at")[1:])
    smd_pads = [o for o in capture["objects"] if o["kind"] == "PAD" and not any(o["drill_mm"]) and o["layers"]]
    shapes = []
    for pad in smd_pads:
        if pad["ref"] == "R83":
            px, py = map(float, first(pads[pad["pin"]], "at")[1:])
            shapes.append(box(sx+px-0.5, sy+py-0.675, sx+px+0.5, sy+py+0.675))
        else:
            shapes.append(geometry([polygon for polygons in pad["layers"].values() for polygon in polygons]))
    tree = STRtree(shapes)
    rows = []
    for via in children(new, "via"):
        position = list(map(float, first(via, "at")[1:]))
        drill = float(first(via, "drill")[1])
        point = Point(position)
        index = int(tree.nearest(point))
        gap = point.distance(shapes[index]) - drill / 2
        rows.append(dict(uuid=first(via, "uuid")[1], position_mm=position,
                         drill_mm=drill, nearest_SMD_ref=smd_pads[index]["ref"],
                         nearest_SMD_pin=smd_pads[index]["pin"], gap_mm=gap))
    assert len(rows) == 357 and min(row["gap_mm"] for row in rows) >= 0.1
    inputs = [OLD / pcb_name, NEW / pcb_name, OLD / "netlist.xml", NEW / "netlist.xml", receipt_path,
              capture_path, Path(__file__), STAGING / "rail-monitor-r83-land-01/construction.json"]
    return dict(source_sha256={str(p.relative_to(REPO)): sha(p) for p in inputs},
                changed_reference="R83", exact_parent_values_pin_nets_poses_and_all_other_parts=True,
                all_existing_tracks_vias_and_authored_zones_exact=True,
                recommended_copper_land_transcription_checked=True,
                pad_centers_x_mm=[-1, 1], pad_size_mm=[1, 1.35], inner_gap_mm=1,
                native_counts=receipt["status"]["counts"], native_checks_all_enabled=True,
                via_drill_screen=rows, minimum_drill_to_SMD_gap_mm=min(r["gap_mm"] for r in rows),
                mask_paste_drill_registration_and_assembly_accepted=False,
                exact_order_code_supply_confirmed=False, installed_error_budget_qualified=False,
                existing_mechanical_and_PDN_reviews_inherited=False,
                selected_parent_board_changed=False, fabrication_approved=False)


if __name__ == "__main__":
    report = check()
    path = NEW / "r83-land-review.json"
    with path.open("x") as stream:
        json.dump(report, stream, indent=2)
        stream.write("\n")
    print("R83-only land correction: zero native findings,", len(report["via_drill_screen"]),
          "via holes screened; minimum gap", report["minimum_drill_to_SMD_gap_mm"])
