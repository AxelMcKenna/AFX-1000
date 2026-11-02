"""Verify placed-rail completion, exact retained analog copper and native fill."""

import argparse
import json
import math
from pathlib import Path

from shapely.geometry import LineString, Point, Polygon
from shapely.ops import unary_union
from shapely.strtree import STRtree

from hardware.electronics.common.sexpr import children, first, read_sexpr
from hardware.fabrication.audio_main_local_routes import relative_hashes, verify_hashes
from hardware.fabrication.audio_main_power_routes import RAILS
from hardware.fabrication.audio_main_supply_completion import RoutingSpace
from hardware.fabrication.audit_audio_main_supplies import check as parent_check
from hardware.fabrication.audit_audio_main_supplies import without_fill
from hardware.fabrication.audit_candidate import sha
from hardware.fabrication.route_nf_surface import shape

ROOT = Path(__file__).resolve().parent
BASE = ROOT / "staging/audio-main-supplies-02"
SURFACE = ROOT / "staging/audio-main-supplies-03"
OUT = ROOT / "staging/audio-main-supplies-06"


def verify_native(path):
    native = json.loads((path / "placement-native-review.json").read_text())
    verify_hashes(native["source_sha256"])
    assert all(sha(path / name) == h for name, h in native["raw_report_sha256"].items())
    drc, erc = [json.loads((path / name).read_text()) for name in ("drc.json", "erc.json")]
    assert drc["violations"] == [], "Native geometry findings remain"
    assert drc["ignored_checks"] == erc["ignored_checks"] == [], "Native checks disabled"
    assert drc["schematic_parity"] == json.loads((BASE / "drc.json").read_text())["schematic_parity"]
    assert not any(s["violations"] for s in erc["sheets"]) and len(erc["sheets"]) == 7
    assert native["DRC_geometry_findings"] == native["ERC_findings"] == 0 and native["schematic_parity_findings"] == 1
    assert all(c["returncode"] == 0 for c in native["complete_native_commands"])
    assert native["uncapped_open_connections"] == len(drc["unconnected_items"])
    return native


def verify_surface(board, record, captured):
    parent = read_sexpr((BASE / "audio_core.kicad_pcb").read_text())
    assert board[:len(parent)] == parent, "Parent analog copper or receiving changed"
    added = board[len(parent):]
    assert added and all(n[0] == "segment" for n in added)
    tracks = {str(first(n, "uuid")[1]): n for n in added}
    names = {str(n[1]): str(n[2]) for n in children(board, "net")}
    pads = {(o["ref"], o["pin"]): o for o in captured["objects"] if o["kind"] == "PAD" and o["pin"]}
    context = RoutingSpace(captured)
    used = set()
    for row in record["routes"]:
        net, layer, width = row["net"], row["layer"], row["width_mm"]
        assert net in RAILS and layer in ("F.Cu", "B.Cu") and width in (.2, .6)
        points = row["path_mm"]
        pad = pads[tuple(row["endpoint"])]
        assert pad["net"] == net and math.dist(points[0], pad["position_mm"]) < 1e-7
        assert context.free_layer(net, layer, width).covers(LineString(points))
        length = sum(math.dist(p, q) for p, q in zip(points, points[1:]))
        assert abs(length-row["length_mm"]) < 1e-7 and length <= (3.5 if width == .2 else 200)
        assert len(row["segment_uuids"]) == len(points)-1
        for ident, start, end in zip(row["segment_uuids"], points, points[1:]):
            n = tracks[ident]
            assert ident not in used and names[str(first(n, "net")[1])] == net
            assert first(n, "layer")[1] == layer and float(first(n, "width")[1]) == width
            assert math.dist(list(map(float, first(n, "start")[1:3])), start) < 1e-6
            assert math.dist(list(map(float, first(n, "end")[1:3])), end) < 1e-6
            used.add(ident)
        context.added_shapes.append((net, layer, LineString(points).buffer(width/2)))
    assert used == tracks.keys(), "Unreviewed surface copper"


def verify_added(board, record, captured):
    parent = read_sexpr((SURFACE / "audio_core.kicad_pcb").read_text())
    assert without_fill(board[:len(parent)]) == without_fill(parent), "Parent copper, lands, drills or authored keepouts changed"
    added = board[len(parent):]
    assert all(n[0] in ("segment", "via") for n in added)
    segments = {str(first(n, "uuid")[1]): n for n in added if n[0] == "segment"}
    vias = {str(first(n, "uuid")[1]): n for n in added if n[0] == "via"}
    assert len(segments)+len(vias) == len(added)
    assert segments.keys() == {r["uuid"] for r in record["added_segments"]}
    assert vias.keys() == {r["uuid"] for r in record["added_vias"]}
    names = {str(n[1]): str(n[2]) for n in children(board, "net")}
    copper = [(o["net"], layer, shape(ps)) for o in captured["objects"] for layer, ps in o["layers"].items()
              if layer in ("F.Cu", "B.Cu") and ps]
    index = STRtree([g for _, _, g in copper])
    actual = {}
    for row in record["added_segments"]:
        n = segments[row["uuid"]]
        net, layer, width = names[str(first(n, "net")[1])], first(n, "layer")[1], float(first(n, "width")[1])
        points = [list(map(float, first(n, key)[1:3])) for key in ("start", "end")]
        assert net == row["net"] and net in RAILS and layer == row["layer"] and layer in ("F.Cu", "B.Cu")
        assert width == row["width_mm"] and width in (.2, .6), "Bridge trace width changed"
        assert math.dist(points[0], row["start_mm"]) < 1e-6 and math.dist(points[1], row["end_mm"]) < 1e-6
        line = LineString(points)
        for i in index.query(line.buffer(width/2+.22)):
            other, face, g = copper[int(i)]
            if face == layer and other != net:
                assert line.distance(g) >= width/2+.2-1e-6, "Bridge approaches native foreign copper"
        key = (net, layer, width, tuple(round(v, 6) for v in points[0]), tuple(round(v, 6) for v in points[1]))
        assert key not in actual
        actual[key] = row["uuid"]
    objects = {o["uuid"]: o for o in captured["objects"]}
    used = set()

    def path(net, layer, width, points):
        for start, end in zip(points, points[1:]):
            if math.dist(start, end) < 1e-8:
                continue
            key = (net, layer, width, tuple(round(v, 6) for v in start), tuple(round(v, 6) for v in end))
            assert actual[key] not in used
            used.add(actual[key])

    for row in record["roots_added"]+record["routes"]:
        source = objects[row["endpoint_uuid"]]
        assert source["net"] == row["net"]
        for layer, points in row["paths"]:
            length = sum(math.dist(p, q) for p, q in zip(points, points[1:]))
            assert length <= 3.5+1e-8 and abs(length-row["fanout_length_mm"]) < 1e-7
            assert math.dist(points[0], source["position_mm"]) < 1e-7 and math.dist(points[-1], row["xy_mm"]) < 1e-7
            path(row["net"], layer, .2, points)
    for row in record["routes"]:
        points = row["path_mm"]
        length = sum(math.dist(p, q) for p, q in zip(points, points[1:]))
        assert abs(length-row["length_mm"]) < 1e-7
        if row["width_mm"] == .2:
            if row["divider_feed"]:
                source = objects[row["endpoint_uuid"]]
                assert (source["ref"], source["pin"]) == ("R211", "1") and row["net"] == "/CODEC/A4V5", "Divider exception used on another load"
                assert length <= 12
            else:
                assert length <= 3.5+1e-8
        else:
            assert row["width_mm"] == .6 and length <= 200
        path(row["net"], row["layer"], row["width_mm"], points)
        for neck in row["necks"]:
            p = neck["path_mm"]
            neck_length = sum(math.dist(a, b) for a, b in zip(p, p[1:]))
            assert neck["width_mm"] == .2 and neck_length <= 3.5+1e-8, "Narrow neck length budget changed"
            assert abs(neck_length-neck["length_mm"]) < 1e-7
            assert min(math.dist(p[-1], points[0]), math.dist(p[-1], points[-1])) < 1e-7
            path(row["net"], neck["layer"], .2, p)
    assert used == segments.keys(), "Unaccounted bridge copper"
    context = RoutingSpace(captured)
    smd = [shape(ps) for o in captured["objects"] if o["kind"] == "PAD" and not any(o["drill_mm"])
           for layer, ps in o["layers"].items() if layer in ("F.Cu", "B.Cu") and ps]
    minimum = math.inf
    for row in record["added_vias"]:
        n = vias[row["uuid"]]
        xy = list(map(float, first(n, "at")[1:3]))
        assert names[str(first(n, "net")[1])] == row["net"] and row["net"] in RAILS
        assert math.dist(xy, row["xy_mm"]) < 1e-6
        assert float(first(n, "size")[1]) == .6 and float(first(n, "drill")[1]) == .3, "Bridge drill changed"
        assert first(n, "layers")[1:] == ["F.Cu", "B.Cu"]
        assert context.via_ok(row["net"], xy), "Bridge via violates pad, drill or reference constraints"
        minimum = min(minimum, min(Point(xy).distance(g)-.15 for g in smd))
        context.new_vias.append(xy)
    assert minimum >= .15-1e-7
    return dict(tracks=len(children(board, "segment")), vias=len(children(board, "via")),
                added_final_bridge_tracks=len(segments), added_final_bridge_vias=len(vias),
                minimum_new_bridge_drill_edge_to_SMD_mm=round(minimum, 9))


def verify_witness(report, captured):
    parent = json.loads((BASE / "supply-connectivity-review.json").read_text())
    assert report["retained_local_pairs"] == parent["retained_local_pairs"], "Local analog pair lost"
    assert report["retained_control_pairs"] == parent["retained_control_pairs"], "Control pair lost"
    assert report["ground_pads"] == parent["ground_pads"], "Ground terminal lost"
    expected = {(o["ref"], o["pin"]): o for o in captured["objects"] if o["kind"] == "PAD" and o["pin"] and o["net"] in RAILS}
    rows = report["supply_pads"]
    assert {(r["ref"], r["pin"]) for r in rows} == expected.keys() and len(rows) == len(expected) == 161
    for row in rows:
        assert row["net"] == expected[(row["ref"], row["pin"])]["net"] and row["root"] == list(RAILS[row["net"]])
        assert row["native_connected_to_source"], "Placed supply/sense pad not connected to source"
    assert report["connected_supply_pads"] == 161


def check():
    parent = parent_check()
    assert parent == json.loads((BASE / "routing-handoff.json").read_text())
    surface_record = json.loads((SURFACE / "construction.json").read_text())
    surface_capture = json.loads((SURFACE / "native-inputs.json").read_text())
    names = ("native-inputs.json", "distribution-construction.json", "native-refill.json", "supply-connectivity-review.json", "fill-entry.json", "review-entry.json")
    reports = {name: json.loads((OUT / name).read_text()) for name in names}
    for r in [surface_record, surface_capture, *reports.values()]:
        verify_hashes(r["source_sha256"])
    surface_board = read_sexpr((SURFACE / "audio_core.kicad_pcb").read_text())
    assert sha(SURFACE / "audio_core.kicad_pcb") == surface_record["candidate_PCB_sha256"]
    verify_surface(surface_board, surface_record, surface_capture)
    surface_native = verify_native(SURFACE)
    capture, record = reports["native-inputs.json"], reports["distribution-construction.json"]
    refill, witness = reports["native-refill.json"], reports["supply-connectivity-review.json"]
    assert sha(OUT / "distribution-input.kicad_pcb") == record["authored_PCB_sha256"]
    assert sha(OUT / "audio_core.kicad_pcb") == refill["filled_PCB_sha256"]
    assert sha(OUT / "native-refill-export.kicad_pcb") == refill["native_export_sha256"]
    board = read_sexpr((OUT / "audio_core.kicad_pcb").read_text())
    assert without_fill(board) == without_fill(read_sexpr((OUT / "distribution-input.kicad_pcb").read_text()))
    native_board = read_sexpr((OUT / "native-refill-export.kicad_pcb").read_text())
    fill = {str(first(z, "uuid")[1]): children(z, "filled_polygon") for z in children(native_board, "zone") if not children(z, "keepout")}
    polygons = []
    for z in children(board, "zone"):
        if not children(z, "keepout"):
            assert children(z, "filled_polygon") == fill[str(first(z, "uuid")[1])]
            polygons += [Polygon([tuple(map(float, p[1:3])) for p in children(first(f, "pts"), "xy")]).buffer(0) for f in children(z, "filled_polygon")]
    proof = verify_added(board, record, capture)
    verify_witness(witness, capture)
    native = verify_native(OUT)
    assert witness["uncapped_open_connections"] == native["uncapped_open_connections"] < surface_native["uncapped_open_connections"] < parent["uncapped_open_connections"]
    assert witness["tracks"] == proof["tracks"] and witness["vias"] == proof["vias"]
    for p in BASE.iterdir():
        if p.suffix in (".kicad_sch", ".kicad_pro", ".kicad_sym", ".kicad_dru") or p.name in ("plan.json", "fp-lib-table", "sym-lib-table"):
            assert (OUT / p.name).read_bytes() == p.read_bytes()
    assessment = record["divider_feed_construction_assessment"]
    assert assessment["endpoint"] == ["R211", "1"] and assessment["maximum_trace_mm"] == 12
    assert assessment["assumed_rail_upper_V"] == 4.65 and assessment["sense_current_allowance_A"] == 1e-6
    assert assessment["current_bound_A"] < .000125 and assessment["trace_only_drop_bound_V"] < .000010
    paths = [Path(__file__), ROOT / "audio_main_supply_bridges.py", ROOT / "audio_main_supply_completion.py",
             ROOT / "audio_main_native_capture.py", BASE / "routing-handoff.json"]
    paths += [SURFACE / n for n in ("construction.json", "native-inputs.json", "placement-native-review.json", "routing-handoff.json")]
    paths += [OUT / n for n in names]+[OUT / "placement-native-review.json"]
    result = dict(parent)
    result.update(proof)
    result.update(source_sha256=relative_hashes(paths), uncapped_open_connections=native["uncapped_open_connections"],
                  added_supply_tracks=parent["added_supply_tracks"]+sum(len(r["segment_uuids"]) for r in surface_record["routes"])+proof["added_final_bridge_tracks"],
                  added_supply_vias=parent["added_supply_vias"]+proof["added_final_bridge_vias"],
                  added_surface_supply_pairs=len(surface_record["routes"]),
                  placed_supply_pads=161, connected_supply_pads=161, all_placed_supply_and_sense_pads_source_connected=True,
                  ground_plane_area_mm2=round(unary_union(polygons).area, 6),
                  minimum_screened_drill_edge_to_SMD_copper_mm=min(parent["minimum_screened_drill_edge_to_SMD_copper_mm"], proof["minimum_new_bridge_drill_edge_to_SMD_mm"]),
                  retained_native_ground_pads=200, retained_native_local_pairs=138, retained_control_pairs=17,
                  all_parent_analog_lands_copper_drills_and_authored_zones_exact=True,
                  complete_supply_routing=False, missing_codec_supply_routing_and_installed_PDN_qualification_pending=True,
                  PCB_routed=False, fabrication_released=False)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    result = check()
    p = OUT / "routing-handoff.json"
    if args.check:
        assert result == json.loads(p.read_text())
    else:
        with p.open("x") as f:
            json.dump(result, f, indent=2)
            f.write("\n")
    print("Audio placed supplies: 161/161; opens", result["uncapped_open_connections"])
