"""Independently replay control copper, protected regions and native terminals."""

import argparse
import json
import math
import re
from collections import Counter
from pathlib import Path

from shapely.geometry import LineString, Point, Polygon
from shapely.ops import unary_union

from hardware.electronics.common.sexpr import children, first, read_sexpr
from hardware.fabrication.audio_main_control_routes import CONTROL_NETS
from hardware.fabrication.audio_main_global_controls import LAYERS, SignalScreen
from hardware.fabrication.audio_main_local_routes import relative_hashes, verify_hashes
from hardware.fabrication.audit_audio_main_supplies import without_fill
from hardware.fabrication.audit_audio_main_supply_completion import check as parent_check
from hardware.fabrication.audit_audio_main_supply_completion import verify_native
from hardware.fabrication.audit_candidate import sha
from hardware.fabrication.route_nf_surface import shape

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "staging/audio-main-supplies-06"
OUT = ROOT / "staging/audio-main-controls-02"


def point_key(point):
    return tuple(round(float(v), 6) for v in point)


def verify_copper(board, record, captured):
    parent = read_sexpr((SOURCE / "audio_core.kicad_pcb").read_text())
    assert without_fill(board[:len(parent)]) == without_fill(parent), "Parent analog/power copper, receiving or authored zones changed"
    added = board[len(parent):]
    assert added and all(n[0] in ("segment", "via") for n in added)
    segments = {str(first(n, "uuid")[1]): n for n in added if n[0] == "segment"}
    vias = {str(first(n, "uuid")[1]): n for n in added if n[0] == "via"}
    assert len(segments)+len(vias) == len(added)
    assert segments.keys() == {r["uuid"] for r in record["added_segments"]}
    assert vias.keys() == {r["uuid"] for r in record["added_vias"]}
    names = {str(n[1]): str(n[2]) for n in children(board, "net")}
    actual = {}
    for row in record["added_segments"]:
        node = segments[row["uuid"]]
        net, layer = names[str(first(node, "net")[1])], first(node, "layer")[1]
        points = [list(map(float, first(node, name)[1:3])) for name in ("start", "end")]
        assert net in CONTROL_NETS and net == row["net"], "Non-control net added"
        assert layer in LAYERS and layer == row["layer"]
        assert float(first(node, "width")[1]) == row["width_mm"] == .2, "Control width changed"
        assert math.dist(points[0], row["start_mm"]) < 1e-6 and math.dist(points[1], row["end_mm"]) < 1e-6
        key = (net, layer, point_key(points[0]), point_key(points[1]))
        assert key not in actual
        actual[key] = row["uuid"]
    actual_vias = {}
    for row in record["added_vias"]:
        node = vias[row["uuid"]]
        xy = list(map(float, first(node, "at")[1:3]))
        net = names[str(first(node, "net")[1])]
        assert net in CONTROL_NETS and net == row["net"] and math.dist(xy, row["xy_mm"]) < 1e-6
        assert float(first(node, "size")[1]) == row["diameter_mm"] == .6
        assert float(first(node, "drill")[1]) == row["drill_mm"] == .3, "Control drill changed"
        assert first(node, "layers")[1:] == ["F.Cu", "B.Cu"]
        key = (net, point_key(xy))
        assert key not in actual_vias
        actual_vias[key] = row["uuid"]
    objects = {o["uuid"]: o for o in captured["objects"]}
    groups = {}
    for key, ids in captured["groups"].items():
        contacts = set()
        for ident in ids:
            obj = objects[ident]
            for layer in LAYERS:
                if obj["layers"].get(layer):
                    for point in [obj["position_mm"]]+([obj["end_mm"]] if "end_mm" in obj else []):
                        contacts.add((layer, point_key(point)))
        groups[frozenset((key,))] = contacts
    screen = SignalScreen(captured)
    used_tracks, used_vias = set(), set()
    for row in record["routes"]:
        assert row["net"] in CONTROL_NETS
        left, right = [frozenset(side) for side in row["source_groups"]]
        assert left and right and left != right and not left & right and left in groups and right in groups, "False control island merge"
        assert all(objects[captured["groups"][key][0]]["net"] == row["net"] for key in left | right)
        runs = row["runs"]
        assert runs and (runs[0][0], point_key(runs[0][1][0])) in groups[left]
        assert (runs[-1][0], point_key(runs[-1][1][-1])) in groups[right]
        terminals = row.get("terminal_points_mm", row["portals"])
        assert math.dist(runs[0][1][0], terminals[0]) < 1e-7 and math.dist(runs[-1][1][-1], terminals[1]) < 1e-7
        # Search portals can be offset from a real pad by an explicit short
        # escape. Check the physical escape rather than treating that portal
        # as an already connected native terminal.
        for side, (terminal, portal) in enumerate(zip(terminals, row["portals"])):
            if math.dist(terminal, portal) > 1e-7:
                points = runs[0 if side == 0 else -1][1]
                assert math.dist(points[-1 if side == 0 else 0], portal) < 1e-7
                assert LineString(points).length <= 3.5+1e-8, "Control pad escape exceeds 3.5 mm"
                assert any(math.dist(portal, xy) < 1e-7 for xy in row["new_vias_mm"]), "Control escape has no plated portal"
        length = sum(LineString(points).length for _, points in runs)
        limit = min(180, 2.5*math.dist(*terminals)+10)
        assert abs(length-row["planar_length_mm"]) < 1e-7 and abs(limit-row["maximum_planar_length_mm"]) < 1e-7
        assert length <= limit+1e-8, "Control route length budget changed"
        assert len(row["new_vias_mm"]) <= 4, "Control via-count limit changed"
        for i, xy in enumerate(row["new_vias_mm"]):
            key = (row["net"], point_key(xy))
            assert actual_vias[key] not in used_vias
            assert all(math.dist(xy, p) > .86 for _, p in screen.vias+screen.new_vias)
            assert all(math.dist(xy, p) > .86 for p in row["new_vias_mm"][:i])
            assert screen.via_legal(row["net"], xy), "Control drill violates actual copper, reference or solder lands"
            used_vias.add(actual_vias[key])
        available_vias = [(n, p) for n, p in screen.vias+screen.new_vias]+[(row["net"], p) for p in row["new_vias_mm"]]
        for i, (layer, points) in enumerate(runs):
            assert layer in LAYERS and len(points) > 1 and screen.legal(row["net"], layer, points), "Control trace violates native obstacle or analog-region screen"
            if i:
                assert math.dist(runs[i-1][1][-1], points[0]) < 1e-7
                assert any(net == row["net"] and math.dist(xy, points[0]) < 1e-7 for net, xy in available_vias), "Layer transition has no plated connection"
            for start, end in zip(points, points[1:]):
                ident = actual[(row["net"], layer, point_key(start), point_key(end))]
                assert ident not in used_tracks
                used_tracks.add(ident)
        joined = groups.pop(left) | groups.pop(right)
        for layer, points in runs:
            screen.added.append((row["net"], layer, LineString(points)))
            joined.update((layer, point_key(p)) for p in points)
        for xy in row["new_vias_mm"]:
            screen.new_vias.append((row["net"], xy))
            joined.update((layer, point_key(xy)) for layer in LAYERS)
        groups[left | right] = joined
    assert used_tracks == segments.keys() and used_vias == vias.keys(), "Unaccounted control copper"
    assert record["trace_width_mm"] == record["clearance_mm"] == .2 and record["planning_margin_mm"] == .01
    assert record["allowed_control_nets"] == sorted(CONTROL_NETS) and record["signal_layers"] == list(LAYERS)
    smd = [shape(ps) for o in captured["objects"] if o["kind"] == "PAD" and not any(o["drill_mm"])
           for layer, ps in o["layers"].items() if layer in ("F.Cu", "B.Cu") and ps]
    minimum = min(Point(row["xy_mm"]).distance(g)-.15 for row in record["added_vias"] for g in smd)
    assert minimum >= .16-1e-7, "Control via drill approaches an SMD solder land"
    return dict(tracks=len(children(board, "segment")), vias=len(children(board, "via")),
                added_global_control_pairs=len(record["routes"]), added_global_control_tracks=len(segments),
                added_global_control_vias=len(vias), minimum_new_control_drill_edge_to_SMD_mm=round(minimum, 9),
                all_parent_analog_power_lands_copper_drills_and_authored_zones_exact=True)


def verify_terminals(report, record, captured):
    parent = json.loads((SOURCE / "supply-connectivity-review.json").read_text())
    assert report["retained_local_pairs"] == [dict(r, additive_successor_native_connected=True) for r in parent["retained_local_pairs"]], "Local analog pair lost"
    assert report["retained_control_pairs"] == [dict(r, additive_successor_native_connected=True) for r in parent["retained_control_pairs"]], "Prior control pair lost"
    assert report["ground_pads"] == parent["ground_pads"], "Ground terminal lost"
    assert report["supply_pads"] == parent["supply_pads"], "Supply or sense terminal lost"
    objects = {o["uuid"]: o for o in captured["objects"]}
    expected = []
    for row in record["routes"]:
        contacts = [objects[i] for side in row["source_groups"] for key in side for i in captured["groups"][key]
                    if objects[i]["kind"] == "PAD" and objects[i]["pin"]]
        assert contacts
        expected.append(dict(net=row["net"], source_groups=row["source_groups"], reference_terminal=[contacts[0]["ref"], contacts[0]["pin"]],
                             contacts=[dict(ref=p["ref"], pin=p["pin"], native_connected=True) for p in contacts]))
    assert report["new_route_witnesses"] == expected, "New control closure lacks complete native pad witnesses"


def check():
    parent = parent_check()
    assert parent == json.loads((SOURCE / "routing-handoff.json").read_text())
    names = ("native-inputs.json", "distribution-construction.json", "native-refill.json", "terminal-connectivity-review.json", "fill-entry.json", "review-entry.json")
    reports = {name: json.loads((OUT / name).read_text()) for name in names}
    for report in reports.values():
        verify_hashes(report["source_sha256"])
    capture, record = reports["native-inputs.json"], reports["distribution-construction.json"]
    refill, witness = reports["native-refill.json"], reports["terminal-connectivity-review.json"]
    assert sha(OUT / "distribution-input.kicad_pcb") == record["authored_PCB_sha256"]
    assert sha(OUT / "audio_core.kicad_pcb") == refill["filled_PCB_sha256"] and sha(OUT / "native-refill-export.kicad_pcb") == refill["native_export_sha256"]
    board = read_sexpr((OUT / "audio_core.kicad_pcb").read_text())
    assert without_fill(board) == without_fill(read_sexpr((OUT / "distribution-input.kicad_pcb").read_text()))
    native_export = read_sexpr((OUT / "native-refill-export.kicad_pcb").read_text())
    fills = {str(first(z, "uuid")[1]): children(z, "filled_polygon") for z in children(native_export, "zone") if not children(z, "keepout")}
    polygons = []
    for zone in children(board, "zone"):
        if not children(zone, "keepout"):
            assert children(zone, "filled_polygon") == fills[str(first(zone, "uuid")[1])]
            polygons += [Polygon([tuple(map(float, p[1:3])) for p in children(first(f, "pts"), "xy")]).buffer(0) for f in children(zone, "filled_polygon")]
    proof = verify_copper(board, record, capture)
    verify_terminals(witness, record, capture)
    native = verify_native(OUT)
    opens = native["uncapped_open_connections"]
    assert opens == witness["uncapped_open_connections"] <= parent["uncapped_open_connections"]-proof["added_global_control_pairs"]
    assert proof["tracks"] == witness["tracks"] and proof["vias"] == witness["vias"]
    for p in SOURCE.iterdir():
        if p.suffix in (".kicad_sch", ".kicad_pro", ".kicad_sym", ".kicad_dru") or p.name in ("plan.json", "fp-lib-table", "sym-lib-table"):
            assert (OUT / p.name).read_bytes() == p.read_bytes()
    counts = Counter()
    for row in json.loads((OUT / "drc.json").read_text())["unconnected_items"]:
        nets = [re.search(r"\[([^]]+)\]", item["description"]).group(1) for item in row["items"]]
        assert len(set(nets)) == 1
        counts[nets[0]] += 1
    paths = [Path(__file__), ROOT / "audio_main_global_controls.py", ROOT / "audio_main_native_review.py", SOURCE / "routing-handoff.json"]
    paths += [OUT / n for n in names]+[OUT / "placement-native-review.json"]
    result = dict(parent)
    result.update(proof)
    result.update(source_sha256=relative_hashes(paths), uncapped_open_connections=opens,
                  remaining_control_connections=sum(counts[n] for n in CONTROL_NETS),
                  remaining_control_connections_by_net={n: counts[n] for n in sorted(CONTROL_NETS) if counts[n]},
                  ground_plane_area_mm2=round(unary_union(polygons).area, 6),
                  minimum_screened_drill_edge_to_SMD_copper_mm=min(parent["minimum_screened_drill_edge_to_SMD_copper_mm"], proof["minimum_new_control_drill_edge_to_SMD_mm"]),
                  control_timing_signal_integrity_EMI_and_installed_fault_qualified=False,
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
    print("Global audio controls:", result["added_global_control_pairs"], "joins;", result["remaining_control_connections"], "control gaps; total opens", result["uncapped_open_connections"])
