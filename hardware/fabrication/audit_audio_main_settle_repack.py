"""Replay the settling supervisor, local pull-up and isolated SENSE branch."""

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
from hardware.fabrication.audit_audio_main_global_controls import verify_terminals
from hardware.fabrication.audit_audio_main_placement import verify_geometry
from hardware.fabrication.audit_audio_main_supplies import without_fill
from hardware.fabrication.audit_audio_main_supply_completion import verify_native
from hardware.fabrication.audit_audio_main_watchdog_repack import check as parent_check
from hardware.fabrication.audit_candidate import sha
from hardware.fabrication.route_nf_surface import shape

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "staging/audio-main-watchdog-repack-01"
OUT = ROOT / "staging/audio-main-settle-repack-01"
CAPTURE = OUT / "native-inputs.json"
REFS = {"U208", "C224", "C227", "R204"}
MOVED = {"ce0587ce-d5ab-5cf0-b16e-89920e6d4bea"}
REMOVED = {
    "3273276f-16c2-5e82-89db-726e2cc1eb2c", "7360dc53-5f8d-5204-aeed-fe12c0e9bb4d",
    "8db5f03d-1534-5c3d-93d2-2879c9a7c060", "42cf1cda-779e-5ad7-8773-350912c6d124",
    "1e3d4f4d-28e3-531d-a7fe-4c5e3ebb637c", "3c34343e-aab2-5694-bdb5-49a4ad3c72a4",
    "17098211-341e-56db-9fdd-2baf9bbdbd28", "b989fdc5-4438-592f-aa56-b27706b01c10",
    "cbdd49d8-3d6a-5592-b787-e4b50227512b", "abb55a63-512c-5f3e-9e87-e65bd178799c",
}


def fps(board):
    return {next(p[2] for p in children(fp, "property") if p[1] == "Reference"): fp for fp in children(board, "footprint")}


def shift(point):
    return [round(float(point[0])-44.57, 8), round(float(point[1])-6, 8)]


def relocate(ref, point):
    if ref == "R204":
        return [round(48.4-(float(point[1])-19), 8), round(14+(float(point[0])-86), 8)]
    return shift(point)


def verify_pruning(record, captured):
    objects = copy.deepcopy(captured["objects"])
    objects = [o for o in objects if o["uuid"] not in REMOVED]
    for obj in objects:
        if obj.get("ref") in REFS or obj["uuid"] in MOVED:
            for polygons in obj["layers"].values():
                for polygon in polygons:
                    polygon["outer"] = [relocate(obj.get("ref"), p) for p in polygon["outer"]]
                    polygon["holes"] = [[relocate(obj.get("ref"), p) for p in ring] for ring in polygon["holes"]]
            obj["position_mm"] = relocate(obj.get("ref"), obj["position_mm"])
            if "end_mm" in obj:
                obj["end_mm"] = relocate(obj.get("ref"), obj["end_mm"])
    assert len(record["pruned_abandoned_power_copper_uuids"]) == 6
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
        after = [48.4, 14, 0] if ref == "R204" else [*shift(before[:2]), before[2]]
        assert row == dict(before=before, after=after), "Declared cell pose changed"
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
    allowed = {"AGND", "V3V3_IO", "/CODEC/CT_SETTLE", "/CODEC/DRIVER_SETTLE_READY", "/CODEC/TIMER_OK"}
    wide = []
    for node, row in zip(added, record["additions"]):
        assert row["net"] in allowed, "Unrelated net added"
        if row["kind"] == "via":
            assert row["diameter_mm"] == .6 and row["drill_mm"] == .3, "Repack drill changed"
            wanted = [a("via"), [a("at"), *row["xy_mm"]], [a("size"), .6], [a("drill"), .3],
                      [a("layers"), "F.Cu", "B.Cu"], [a("net"), nets[row["net"]]], [a("uuid"), row["uuid"]]]
        else:
            assert row["kind"] == "segment"
            width = .6 if row["purpose"] == "retained_supply_bridge" else .2
            assert row["width_mm"] == width, "Repack trace width changed"
            assert row["layer"] in ("F.Cu", "B.Cu", "In2.Cu")
            if width == .6:
                assert row["net"] == "V3V3_IO"
                wide.append((row["layer"], row["start_mm"], row["end_mm"]))
            wanted = [a("segment"), [a("start"), *row["start_mm"]], [a("end"), *row["end_mm"]], [a("width"), width],
                      [a("layer"), row["layer"]], [a("net"), nets[row["net"]]], [a("uuid"), row["uuid"]]]
        assert node == read_sexpr(sexpr(wanted)), "Actual new copper differs from construction"
    assert wide == [("F.Cu", [91.4, 23], [92.55, 23])], "Original supply bridge not retained"
    for row in record["routes"]:
        matching = [r for r in record["additions"] if r["kind"] == "segment" and r["purpose"] == "completed_control_connection" and r["net"] == row["net"]]
        expected = [(layer, start, end) for layer, points in row["runs"] for start, end in zip(points, points[1:])]
        assert [(r["layer"], r["start_mm"], r["end_mm"]) for r in matching] == expected
        assert len(row["new_vias_mm"]) <= 4, "Control via-count budget changed"
        escape = next(e for e in record["reserved_control_escapes"] if e["net"] == row["net"])
        total = sum(LineString(points).length for _, points in row["runs"])+LineString(escape["points"]).length
        assert total <= min(180, 2.5*math.dist(escape["points"][0], row["runs"][-1][1][-1])+10), "Control path length budget"
    timing = [r for r in record["additions"] if r["purpose"] == "private_settle_timing" and r["kind"] == "segment"]
    assert len(timing) == 2 and sum(math.dist(r["start_mm"], r["end_mm"]) for r in timing) <= 3.5, "Settling timing path length"
    assert {r["net"] for r in record["routes"]} == {"/CODEC/DRIVER_SETTLE_READY", "/CODEC/TIMER_OK"}
    return dict(tracks=len(children(board, "segment")), vias=len(children(board, "via")),
                settle_added_control_pairs=2, settle_private_timing_pair_connected=True)


def verify_witnesses(report, extra, record, captured):
    verify_terminals(report, record, captured)
    previous = json.loads((SOURCE / "terminal-connectivity-review.json").read_text())
    inherited = json.loads((SOURCE / "additional-terminal-review.json").read_text())
    assert extra["retained_global_control_witnesses"] == inherited["retained_global_control_witnesses"]+previous["new_route_witnesses"], "Prior global control closure lost"
    assert extra["retained_private_timing_connections"] == inherited.get("retained_private_timing_connections", [])+[inherited["private_timing_connection"]], "Prior private timing connection lost"
    assert extra["private_timing_connection"] == dict(net="/CODEC/CT_SETTLE", endpoints=[["U208", "5"], ["C227", "1"]], native_connected=True)
    assert extra["reserved_control_escapes"] == [dict(ref=r["ref"], pin=r["pin"], net=r["net"], via_mm=r["via"], native_connected=True)
                                                 for r in record["reserved_control_escapes"]]


def verify_sense(record, pads, planning):
    by_key = {(p["ref"], p["pin"]): p for p in pads if p["pin"]}
    sense, supply = by_key["U208", "1"], by_key["U208", "4"]
    assert sense["net"] == supply["net"] == by_key["C224", "1"]["net"] == "V3V3_IO"
    assert math.dist(sense["position_mm"], [45.43, 18.1]) < 1e-6
    # The only long narrow rail branch terminates at the SENSE input.
    fixed = [([45.43, 18.1], [44.5, 19.52]), ([47.98, 17], [49, 18.2])]
    entries = []
    for start, end in fixed:
        matching = [r for r in record["additions"] if r["kind"] == "segment" and r["net"] == "V3V3_IO" and
                    r["layer"] == "F.Cu" and math.dist(r["start_mm"], start) < 1e-7 and math.dist(r["end_mm"], end) < 1e-7]
        assert len(matching) == 1, "Dedicated SENSE endpoint missing or redirected to VDD"
        entries.extend(matching)
    middle = [r for r in record["additions"] if r["kind"] == "segment" and r["purpose"] == "settle_sense_branch"]
    paths = record["replacement_power_paths_mm"]
    assert len(paths) == 1 and paths[0]["layer"] in ("B.Cu", "In2.Cu")
    path = paths[0]
    assert path["points_mm"][0] == [44.5, 19.52] and path["points_mm"][-1] == [49, 18.2]
    assert [(r["layer"], r["start_mm"], r["end_mm"]) for r in middle] == [
        (path["layer"], a, b) for a, b in zip(path["points_mm"], path["points_mm"][1:])]
    length = sum(math.dist(r["start_mm"], r["end_mm"]) for r in entries+middle)
    assert length <= 12, "Dedicated SENSE trace length exceeds 12 mm"
    vias = [r for r in record["additions"] if r["kind"] == "via" and r["net"] == "V3V3_IO" and
            any(math.dist(r["xy_mm"], xy) < 1e-7 for xy in ([44.5, 19.52], [49, 18.2]))]
    assert len(vias) == 2
    ids = {r["uuid"] for r in entries+middle+vias}
    geometry = {layer: [] for layer in ("F.Cu", "In1.Cu", "In2.Cu", "B.Cu")}
    for obj in planning["objects"]:
        if obj["uuid"] in ids:
            for layer, ps in obj["layers"].items():
                if ps:
                    geometry[layer].append(shape(ps))
    copper = {layer: unary_union(rows) for layer, rows in geometry.items()}
    cap = by_key["C224", "1"]
    for other in planning["objects"]:
        if other["net"] != "V3V3_IO" or other["uuid"] in ids or (other.get("ref"), other.get("pin")) in (("U208", "1"), ("C224", "1")):
            continue
        for layer, ps in other["layers"].items():
            if not ps:
                continue
            source_land = shape(cap["layers"].get(layer, [])).buffer(.002)
            assert copper[layer].difference(source_land).intersection(shape(ps)).area < 1e-10, "SENSE branch carries another supply load"
    # Ordinary VDD and resistor feeds retain the short 0.20 mm entry limit.
    bulk = [r for r in record["additions"] if r["kind"] == "segment" and r["net"] == "V3V3_IO" and r["purpose"] == "local_pullup_power"]
    assert len(bulk) == 2 and sum(math.dist(r["start_mm"], r["end_mm"]) for r in bulk) <= 3.5
    feed = [r for r in record["additions"] if r["kind"] == "segment" and r["net"] == "V3V3_IO" and r["layer"] == "F.Cu" and r["end_mm"] == [50, 14.7]]
    assert len(feed) == 1 and math.dist(feed[0]["start_mm"], feed[0]["end_mm"]) <= 3.5
    # These are unapproved construction assumptions, not installed accuracy,
    # via resistance, copper acceptance or a noise/transient qualification.
    resistance = 1.724e-8*(1+.00393*(125-20))*.012/(.00016*.000018)
    return dict(terminal=["U208", "1"], source_terminal=["C224", "1"], actual_trace_length_mm=round(length, 9),
                maximum_trace_length_mm=12, nominal_trace_width_mm=.2,
                fixed_variant_datasheet_ISENSE_max_A_at_5V=8e-6, engineering_current_allowance_A=20e-6,
                assumed_minimum_finished_width_mm=.16, assumed_minimum_copper_um=18, assumed_copper_temperature_C=125,
                maximum_trace_only_resistance_ohm=resistance, maximum_trace_only_drop_V=resistance*20e-6,
                primary_document_url="https://www.ti.com/lit/ds/symlink/tps3890.pdf",
                primary_document_revision="SLVSD65A, May 2016",
                primary_document_sha256="ee79599730e7606ba9718d9820b411020e3dcd9ff7d44572f8ee63fead15b9d0",
                fixed_variant_8uA_is_not_adjustable_variant_100nA=True,
                source_role_checked=True, other_supply_loads_on_branch=False,
                installed_rail_bounds_via_loss_coupling_fault_accuracy_and_process_qualified=False)


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
    assert native["uncapped_open_connections"] == report["uncapped_open_connections"] == extra["uncapped_open_connections"] == 213
    assert proof["tracks"] == report["tracks"] and proof["vias"] == report["vias"]
    plan = reports["plan.json"]
    expected_plan = json.loads((SOURCE / "plan.json").read_text())
    for ref in REFS:
        before = expected_plan["poses"][ref]
        expected_plan["poses"][ref] = [48.4, 14, 0, "B"] if ref == "R204" else [*shift(before[:2]), *before[2:]]
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
    planning = json.loads((OUT / "planning-inputs.json").read_text())
    verify_hashes(planning["source_sha256"])
    def pad_key(p):
        return p["ref"], p["pin"], tuple(round(v, 6) for v in p["position_mm"])
    proposed = {pad_key(p): p for p in planning["objects"] if p["kind"] == "PAD"}
    assert len(proposed) == 930
    for pad in pads:
        expected = proposed[pad_key(pad)]
        assert all(pad[k] == expected[k] for k in ("ref", "pin", "net", "drill_mm", "npth"))
        assert pad["layers"].keys() == expected["layers"].keys()
        for layer, ps in pad["layers"].items():
            if ps:
                assert shape(ps).hausdorff_distance(shape(expected["layers"][layer])) <= .0021
    import xml.etree.ElementTree as ET
    node = next(n for n in ET.parse(OUT / "native-netlist.xml").findall("nets/net/node") if n.get("ref") == "U208" and n.get("pin") == "1")
    assert node.get("pinfunction") == "SENSE_1" and node.get("pintype") == "input"
    sense_assessment = verify_sense(record, pads, planning)
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
    assert sum(counts[n] for n in CONTROL_NETS) == 12
    paths = [Path(__file__), ROOT / "audio_main_settle_repack.py", ROOT / "audio_main_settle_native.py", CAPTURE,
             SOURCE / "routing-handoff.json"]+[OUT / name for name in names]
    paths.append(OUT / "planning-inputs.json")
    result = dict(geometry, **proof, source_sha256=relative_hashes(paths), sense_branch_assessment=sense_assessment,
                  native_geometry_findings=0, native_ERC_findings=0, native_missing_codec_footprint_findings=1,
                  all_native_categories_enabled=True, uncapped_open_connections=213,
                  local_connected_pairs=151, connected_signal_supply_endpoints=131, retained_native_local_pairs=138,
                  connected_ground_pads=200, connected_declared_local_ground_returns=20, placed_supply_pads=161, connected_supply_pads=161,
                  added_control_pairs=17, added_global_control_pairs=52,
                  added_global_control_tracks=parent["added_global_control_tracks"]+sum(r["kind"] == "segment" and r["net"] in CONTROL_NETS for r in record["additions"]),
                  added_global_control_vias=parent["added_global_control_vias"]+sum(r["kind"] == "via" and r["net"] in CONTROL_NETS for r in record["additions"]),
                  added_supply_tracks=parent["added_supply_tracks"]-8+sum(r["kind"] == "segment" and r["net"] == "V3V3_IO" for r in record["additions"]),
                  added_supply_vias=parent["added_supply_vias"]+3,
                  ground_plane_area_mm2=round(unary_union(polygons).area, 6), minimum_screened_drill_edge_to_SMD_copper_mm=round(minimum, 9),
                  remaining_control_connections=12, remaining_control_connections_by_net={n: counts[n] for n in sorted(CONTROL_NETS) if counts[n]},
                  critical_analog_copper_and_poses_preserved=True, four_part_settling_receiving_renewed=True,
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
    print("Settling cell renewed: 213 total opens / 12 controls; all prior terminal checks retained")
