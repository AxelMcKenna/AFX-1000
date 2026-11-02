"""Replay a bounded three-part move, power cleanup and real native closures."""

import argparse
import copy
import json
import math
import re
from collections import Counter
from pathlib import Path

from shapely.geometry import LineString, Point, Polygon
from shapely.ops import unary_union

from hardware.electronics.common.netlists import netlist
from hardware.electronics.common.sexpr import a, children, first, read_sexpr, sexpr
from hardware.electronics.output_stage.check_placement import courtyard
from hardware.fabrication.audio_main_control_routes import CONTROL_NETS
from hardware.fabrication.audio_main_local_routes import relative_hashes, verify_hashes
from hardware.fabrication.audit_audio_main_global_controls import check as parent_check
from hardware.fabrication.audit_audio_main_global_controls import verify_terminals
from hardware.fabrication.audit_audio_main_placement import verify_geometry
from hardware.fabrication.audit_audio_main_supplies import without_fill
from hardware.fabrication.audit_audio_main_supply_completion import verify_native
from hardware.fabrication.audit_candidate import sha
from hardware.fabrication.route_nf_surface import shape

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "staging/audio-main-controls-02"
OUT = ROOT / "staging/audio-main-watchdog-repack-01"
CAPTURE = ROOT / "staging/audio-main-controls-03/native-inputs.json"
REFS = {"U601", "C601", "C602"}
MOVED = {
    "454d801c-358b-5e13-b5a9-28b3ee11427c", "74783295-71bc-5087-9f68-497a210600b6",
    "73022e0a-43a9-555f-9fff-55fb073532ae", "d978821a-e321-58bf-b5ef-42e9036447d9",
    "c3ce335a-534a-53df-866b-10fc744d7643",
}
REMOVED = {
    "51b2a192-7ac5-5f76-ae22-0c0cb63e4d75", "6ee82995-4a8c-576f-b572-afdcd9dabe6c",
    "57273fb3-bee7-5322-9f49-ee6b0f4213cf", "605ace16-c406-5358-b577-9042f9661b31",
    "b9dd63e9-fcfe-5479-b203-dbf484149f3e", "131bee6c-c2e1-5564-b09b-f79a3796dd2f",
    "b39213a9-47ee-5cee-b17b-c5b4f0e0e8b7", "b8db1771-f46c-5c92-a4df-c85f094136f7",
    "edae5e91-e915-5842-a19c-d1223388be00", "79c8faa3-9b8d-5d85-97bb-e4d2fb507b00",
    "d8f867d9-ae38-58bd-abdd-93c2086a5d7c", "8c6e06c3-5945-5547-85b0-4cb25779fa7a",
}


def fps(board):
    return {next(p[2] for p in children(fp, "property") if p[1] == "Reference"): fp for fp in children(board, "footprint")}


def shift(point):
    return [round(float(point[0])-35.5, 8), round(float(point[1])+4.5, 8)]


def verify_pruning(record, captured):
    objects = copy.deepcopy(captured["objects"])
    objects = [o for o in objects if o["uuid"] not in REMOVED]
    for obj in objects:
        if obj.get("ref") in REFS or obj["uuid"] in MOVED:
            for polygons in obj["layers"].values():
                for polygon in polygons:
                    polygon["outer"] = [shift(p) for p in polygon["outer"]]
                    polygon["holes"] = [[shift(p) for p in ring] for ring in polygon["holes"]]
            obj["position_mm"] = shift(obj["position_mm"])
            if "end_mm" in obj:
                obj["end_mm"] = shift(obj["end_mm"])
    assert len(record["pruned_abandoned_power_copper_uuids"]) == 7
    for ident in record["pruned_abandoned_power_copper_uuids"]:
        obj = next(o for o in objects if o["uuid"] == ident)
        assert obj["kind"] == "PCB_TRACK" and obj["net"] == "V3V3_IO", "Non-power copper pruned"
        abandoned = False
        for endpoint in (obj["position_mm"], obj["end_mm"]):
            faces = set(obj["layers"])
            for via in objects:
                if via["kind"] == "PCB_VIA" and via["net"] == "V3V3_IO" and math.dist(endpoint, via["position_mm"]) < 1e-7:
                    faces.update(via["layers"])
            point = Point(endpoint)
            contacts = [o for o in objects if o["uuid"] != ident and o["net"] == "V3V3_IO" and
                        o["kind"] in ("PAD", "PCB_TRACK") and any(ps and layer in faces and shape(ps).covers(point)
                        for layer, ps in o["layers"].items())]
            if not contacts:
                abandoned = True
        assert abandoned, "Pruning removes a branch between real terminals"
        objects.remove(obj)


def verify_delta(board, record):
    parent = read_sexpr((SOURCE / "audio_core.kicad_pcb").read_text())
    expected = copy.deepcopy(parent)
    assert set(record["declared_pose_changes"]) == REFS, "Unexpected component move"
    originals, updated = fps(parent), fps(expected)
    for ref, row in record["declared_pose_changes"].items():
        before = list(map(float, first(originals[ref], "at")[1:4]))
        after = [*shift(before[:2]), before[2]]
        assert row == dict(before=before, after=after), "Watchdog rigid translation changed"
        first(updated[ref], "at")[1:4] = after
    assert set(record["translated_copper_uuids"]) == MOVED and set(record["removed_copper_uuids"]) == REMOVED
    pruned = set(record["pruned_abandoned_power_copper_uuids"])
    assert not pruned & REMOVED
    rebuilt = []
    for node in expected:
        if isinstance(node, list) and node and node[0] in ("segment", "via"):
            ident = first(node, "uuid")[1]
            if ident in REMOVED | pruned:
                continue
            if ident in MOVED:
                assert node[0] == "segment"
                for key in ("start", "end"):
                    first(node, key)[1:3] = shift(first(node, key)[1:3])
        rebuilt.append(node)
    assert without_fill(board[:len(rebuilt)]) == without_fill(read_sexpr(sexpr(rebuilt))), "Unexpected analog, power, footprint, hole or authored-zone edit"
    added = board[len(rebuilt):]
    assert len(added) == len(record["additions"])
    nets = {str(n[2]): n[1] for n in children(board, "net")}
    allowed = {"AGND", "V3V3_IO", "/BYPASS/CWD", "/BYPASS/HEARTBEAT", "/BYPASS/LOCAL_OK"}
    wide = []
    for node, row in zip(added, record["additions"]):
        assert row["net"] in allowed, "Unrelated net added"
        if row["kind"] == "via":
            assert row["diameter_mm"] == .6 and row["drill_mm"] == .3, "Repack drill changed"
            wanted = [a("via"), [a("at"), *row["xy_mm"]], [a("size"), .6], [a("drill"), .3],
                      [a("layers"), "F.Cu", "B.Cu"], [a("net"), nets[row["net"]]], [a("uuid"), row["uuid"]]]
        else:
            assert row["kind"] == "segment"
            width = .6 if row["purpose"] == "watchdog_wide_power_branch" else .2
            assert row["width_mm"] == width, "Repack trace width changed"
            assert row["layer"] in ("F.Cu", "B.Cu", "In2.Cu")
            if width == .6:
                assert row["net"] == "V3V3_IO"
                wide.append((row["layer"], row["start_mm"], row["end_mm"]))
            wanted = [a("segment"), [a("start"), *row["start_mm"]], [a("end"), *row["end_mm"]], [a("width"), width],
                      [a("layer"), row["layer"]], [a("net"), nets[row["net"]]], [a("uuid"), row["uuid"]]]
        assert node == read_sexpr(sexpr(wanted)), "Actual new copper differs from construction"
    expected_wide = []
    for row in record["replacement_power_paths_mm"]:
        assert abs(LineString(row["points_mm"]).length-row["planar_length_mm"]) < 1e-7
        assert row["planar_length_mm"] <= 30, "Replacement supply loop too long"
        expected_wide += [(row["layer"], start, end) for start, end in zip(row["points_mm"], row["points_mm"][1:])]
    assert wide == expected_wide
    timing = [r for r in record["additions"] if r["purpose"] == "private_watchdog_timing" and r["kind"] == "segment"]
    assert len(timing) == 2 and sum(math.dist(r["start_mm"], r["end_mm"]) for r in timing) <= 3.5, "Watchdog timing path length"
    assert {r["net"] for r in record["routes"]} == {"/BYPASS/HEARTBEAT", "/BYPASS/LOCAL_OK"}
    return dict(tracks=len(children(board, "segment")), vias=len(children(board, "via")),
                watchdog_added_control_pairs=2, watchdog_private_timing_pair_connected=True)


def verify_witnesses(report, extra, record, captured):
    verify_terminals(report, record, captured)
    previous = json.loads((SOURCE / "terminal-connectivity-review.json").read_text())
    assert extra["retained_global_control_witnesses"] == previous["new_route_witnesses"], "Prior global control closure lost"
    assert extra["private_timing_connection"] == dict(net="/BYPASS/CWD", endpoints=[["U601", "2"], ["C601", "1"]], native_connected=True)
    assert extra["reserved_control_escapes"] == [dict(ref=r["ref"], pin=r["pin"], net=r["net"], via_mm=r["via"], native_connected=True)
                                                 for r in record["reserved_control_escapes"]]


def check():
    parent = parent_check()
    names = ("distribution-construction.json", "native-refill.json", "terminal-connectivity-review.json",
             "additional-terminal-review.json", "current-native-pads.json", "placement-native-review.json", "plan.json")
    reports = {name: json.loads((OUT / name).read_text()) for name in names}
    for report in reports.values():
        verify_hashes(report["source_sha256"])
    record = reports["distribution-construction.json"]
    assert sha(OUT / "distribution-input.kicad_pcb") == record["authored_PCB_sha256"]
    refill = reports["native-refill.json"]
    assert sha(OUT / "audio_core.kicad_pcb") == refill["filled_PCB_sha256"] and sha(OUT / "native-refill-export.kicad_pcb") == refill["native_export_sha256"]
    captured = json.loads(CAPTURE.read_text())
    verify_hashes(captured["source_sha256"])
    verify_pruning(record, captured)
    board = read_sexpr((OUT / "audio_core.kicad_pcb").read_text())
    assert without_fill(board) == without_fill(read_sexpr((OUT / "distribution-input.kicad_pcb").read_text()))
    proof = verify_delta(board, record)
    report, extra = reports["terminal-connectivity-review.json"], reports["additional-terminal-review.json"]
    verify_witnesses(report, extra, record, captured)
    native = verify_native(OUT)
    assert native["uncapped_open_connections"] == report["uncapped_open_connections"] == extra["uncapped_open_connections"] == 216
    assert proof["tracks"] == report["tracks"] and proof["vias"] == report["vias"]
    plan = reports["plan.json"]
    expected_plan = json.loads((SOURCE / "plan.json").read_text())
    for ref in REFS:
        before = expected_plan["poses"][ref]
        expected_plan["poses"][ref] = [*shift(before[:2]), *before[2:]]
        side = first(fps(board)[ref], "layer")[1][0]
        expected_plan["expanded_receiving_bounds_mm"][ref] = courtyard(fps(board)[ref], side+".CrtYd")
    for cell in expected_plan["local_cells"]:
        if cell["owner"] in REFS:
            for terminal in cell["terminals"]:
                terminal["owner_position_mm"] = shift(terminal["owner_position_mm"])
    expected_plan["source_sha256"].update(relative_hashes([OUT / "applied-repack.py.txt", SOURCE / "plan.json"]))
    assert plan == expected_plan, "Receiving requirement or local-cell limit changed"
    geometry_board = [n for n in board if not isinstance(n, list) or not n or n[0] not in ("segment", "via", "zone")]
    geometry_board += [children(board, "zone")[0]]
    parts, pins = netlist(OUT / "native-netlist.xml")
    geometry = verify_geometry(geometry_board, plan, parts, pins)
    assert geometry == record["receiving_geometry"]
    for p in SOURCE.rglob("*"):
        if p.is_file() and (p.suffix in (".kicad_sch", ".kicad_pro", ".kicad_sym", ".kicad_dru", ".kicad_mod") or p.name in ("fp-lib-table", "sym-lib-table")):
            assert (OUT / p.relative_to(SOURCE)).read_bytes() == p.read_bytes()
    pads = reports["current-native-pads.json"]["objects"]
    assert len(pads) == 930
    smd = [shape(ps) for p in pads if not any(p["drill_mm"]) for layer, ps in p["layers"].items() if layer in ("F.Cu", "B.Cu") and ps]
    minimum = min(Point(list(map(float, first(v, "at")[1:3]))).distance(g)-float(first(v, "drill")[1])/2
                  for v in children(board, "via") for g in smd)
    assert minimum >= .16-1e-7, "Actual drill-to-SMD gap violated"
    export = read_sexpr((OUT / "native-refill-export.kicad_pcb").read_text())
    fills = {first(z, "uuid")[1]: children(z, "filled_polygon") for z in children(export, "zone") if not children(z, "keepout")}
    polygons = []
    for zone in children(board, "zone"):
        if children(zone, "keepout"):
            continue
        assert children(zone, "filled_polygon") == fills[first(zone, "uuid")[1]]
        for fill in children(zone, "filled_polygon"):
            polygons.append(Polygon([tuple(map(float, p[1:3])) for p in children(first(fill, "pts"), "xy")]).buffer(0))
    counts = Counter(re.search(r"\[([^]]+)\]", row["items"][0]["description"]).group(1)
                     for row in json.loads((OUT / "drc.json").read_text())["unconnected_items"])
    assert sum(counts[n] for n in CONTROL_NETS) == 14
    paths = [Path(__file__), ROOT / "audio_main_watchdog_repack.py", ROOT / "audio_main_watchdog_native.py", CAPTURE,
             SOURCE / "routing-handoff.json"]+[OUT / name for name in names]
    result = dict(geometry, **proof, source_sha256=relative_hashes(paths),
                  native_geometry_findings=0, native_ERC_findings=0, native_missing_codec_footprint_findings=1,
                  all_native_categories_enabled=True, uncapped_open_connections=216,
                  local_connected_pairs=151, connected_signal_supply_endpoints=131, retained_native_local_pairs=138,
                  connected_ground_pads=200, connected_declared_local_ground_returns=20, placed_supply_pads=161, connected_supply_pads=161,
                  added_control_pairs=17, added_global_control_pairs=50,
                  added_global_control_tracks=parent["added_global_control_tracks"]+sum(r["kind"] == "segment" and r["net"] in CONTROL_NETS for r in record["additions"]),
                  added_global_control_vias=parent["added_global_control_vias"]+sum(r["kind"] == "via" and r["net"] in CONTROL_NETS for r in record["additions"]),
                  added_supply_tracks=parent["added_supply_tracks"]-13+sum(r["kind"] == "segment" and r["net"] == "V3V3_IO" for r in record["additions"]),
                  added_supply_vias=parent["added_supply_vias"]+1,
                  ground_plane_area_mm2=round(unary_union(polygons).area, 6), minimum_screened_drill_edge_to_SMD_copper_mm=round(minimum, 9),
                  remaining_control_connections=14, remaining_control_connections_by_net={n: counts[n] for n in sorted(CONTROL_NETS) if counts[n]},
                  critical_analog_copper_and_poses_preserved=True, three_part_watchdog_receiving_renewed=True,
                  high_frequency_compensation_capacitor_tracks_preserved=True, physical_codec_ADC_star_geometry_verified=False,
                  complete_mating_harness_support_and_case_receiving_qualified=False,
                  analog_PDN_thermal_stability_noise_and_manufacturing_qualified=False,
                  control_timing_signal_integrity_EMI_and_installed_fault_qualified=False,
                  PCB_routed=False, fabrication_released=False)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    result = check()
    path = OUT / "routing-handoff.json"
    if args.check:
        assert result == json.loads(path.read_text())
    else:
        with path.open("x") as f:
            json.dump(result, f, indent=2)
            f.write("\n")
    print("Watchdog cell renewed: 216 total opens / 14 controls; all prior terminal checks retained")
