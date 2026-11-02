"""Check actual inner supply copper, native refill and retained audio witnesses."""

import argparse
import copy
import json
import math
from pathlib import Path

from shapely.geometry import LineString, Point, Polygon
from shapely.ops import unary_union

from hardware.electronics.common.sexpr import children, first, read_sexpr
from hardware.fabrication.audio_main_local_routes import relative_hashes, verify_hashes
from hardware.fabrication.audio_main_power_routes import RAILS, PowerSpace
from hardware.fabrication.audit_audio_main_controls import check as parent_check
from hardware.fabrication.audit_candidate import sha
from hardware.fabrication.route_nf_surface import shape

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "staging/audio-main-controls-01"
OUT = ROOT / "staging/audio-main-supplies-02"


def without_fill(board):
    result = copy.deepcopy(board)
    for zone in children(result, "zone"):
        zone[:] = [n for n in zone if not isinstance(n, list) or not n or n[0] != "filled_polygon"]
    return result


def verify_board(board, construction, captured):
    parent = read_sexpr((SOURCE / "audio_core.kicad_pcb").read_text())
    assert without_fill(board[:len(parent)]) == without_fill(parent), "Parent analog copper, footprint or authored zone changed"
    added = board[len(parent):]
    assert all(n[0] in ("segment", "via") for n in added)
    tracks = {first(n, "uuid")[1]: n for n in added if n[0] == "segment"}
    vias = {first(n, "uuid")[1]: n for n in added if n[0] == "via"}
    assert len(tracks)+len(vias) == len(added)
    assert tracks.keys() == {r["uuid"] for r in construction["added_segments"]}
    assert vias.keys() == {r["uuid"] for r in construction["added_vias"]}
    net_names = {str(n[1]): str(n[2]) for n in children(board, "net")}
    context = PowerSpace(captured)
    free_by_net = {rail["net"]: context.free(rail["net"]) for rail in construction["selected_rails"]}
    # All newly emitted copper is checked at its actual width. Native DRC is
    # still mandatory, including new-vs-new clearances and via centring.
    for row in construction["added_segments"]:
        node = tracks[row["uuid"]]
        net, layer = net_names[str(first(node, "net")[1])], first(node, "layer")[1]
        width = float(first(node, "width")[1])
        points = [list(map(float, first(node, k)[1:3])) for k in ("start", "end")]
        assert net == row["net"] and net in RAILS, "Undeclared supply net"
        assert layer == row["layer"] and width == row["width_mm"]
        assert math.dist(points[0], row["start_mm"]) < 1e-6 and math.dist(points[1], row["end_mm"]) < 1e-6
        assert math.dist(*points) > 0
        if layer == "In2.Cu":
            assert width == .6, "Distribution width changed"
            assert free_by_net[net].covers(LineString(points)), "Inner supply crosses original copper or protected opening"
        else:
            assert layer in ("F.Cu", "B.Cu") and width == .2
            assert context.surface.legal(net, layer, points), "Surface supply violates the native obstacle screen"
    smd = [shape(ps) for o in captured["objects"] if o["kind"] == "PAD" and not any(o["drill_mm"])
           for layer, ps in o["layers"].items() if layer in ("F.Cu", "B.Cu") and ps]
    minimum = math.inf
    for row in construction["added_vias"]:
        node = vias[row["uuid"]]
        xy = list(map(float, first(node, "at")[1:3]))
        net = net_names[str(first(node, "net")[1])]
        assert net == row["net"] and net in RAILS and math.dist(xy, row["xy_mm"]) < 1e-6
        assert float(first(node, "size")[1]) == .6 and float(first(node, "drill")[1]) == .3, "Supply drill geometry changed"
        assert first(node, "layers")[1:] == ["F.Cu", "B.Cu"]
        assert context.via_ok(net, xy), "Supply via violates reference, drill or land constraints"
        gap = min(Point(xy).distance(g)-.15 for g in smd)
        minimum = min(minimum, gap)
        assert gap >= .15-1e-7, "Supply drill approaches a solder land"
        context.new_vias.append(xy)
    objects = {o["uuid"]: o for o in captured["objects"]}
    for rail in construction["selected_rails"]:
        assert rail["net"] in RAILS and rail["root_endpoint"] == list(RAILS[rail["net"]])
        for escape in [rail["root_escape"]]+[b["escape"] for b in rail["branches"]]:
            obj = objects[escape["endpoint_uuid"]]
            assert obj["net"] == rail["net"]
            for layer, points in escape["paths"]:
                length = sum(math.dist(p, q) for p, q in zip(points, points[1:]))
                assert length <= 3.5 and abs(length-escape["fanout_length_mm"]) < 1e-7
                assert math.dist(points[0], obj["position_mm"]) < 1e-7 and math.dist(points[-1], escape["xy_mm"]) < 1e-7
    plane = next(z for z in children(board, "zone") if not children(z, "keepout"))
    polygons = [Polygon([tuple(map(float, p[1:3])) for p in children(first(n, "pts"), "xy")]).buffer(0)
                for n in children(plane, "filled_polygon")]
    area = unary_union(polygons).area
    assert area > 7800 and first(plane, "net_name")[1] == "AGND"
    return dict(tracks=len(children(board, "segment")), vias=len(children(board, "via")),
                added_supply_tracks=len(tracks), added_supply_vias=len(vias),
                ground_plane_area_mm2=round(area, 6), minimum_new_supply_drill_edge_to_SMD_mm=round(minimum, 9),
                all_parent_analog_copper_lands_and_authored_zones_preserved=True)


def verify_witnesses(report, captured, construction):
    parent = json.loads((SOURCE / "control-connectivity-review.json").read_text())
    assert report["retained_local_pairs"] == [dict(r, supply_successor_native_connected=True) for r in parent["retained_local_pairs"]]
    assert report["retained_control_pairs"] == [dict(r, supply_successor_native_connected=True) for r in parent["new_control_pairs"]]
    assert report["ground_pads"] == parent["ground_pads"], "Lost or missing ground terminal"
    expected = {(o["ref"], o["pin"]): o for o in captured["objects"] if o["kind"] == "PAD" and o["pin"] and o["net"] in RAILS}
    rows = report["supply_pads"]
    assert {(r["ref"], r["pin"]) for r in rows} == expected.keys() and len(rows) == len(expected) == 161
    for row in rows:
        assert row["net"] == expected[(row["ref"], row["pin"])]["net"]
        assert row["root"] == list(RAILS[row["net"]])
    assert sum(r["native_connected_to_source"] for r in rows) == report["connected_supply_pads"]
    by_pad = {(r["ref"], r["pin"]): r for r in rows}
    objects = {o["uuid"]: o for o in captured["objects"]}
    for rail in construction["selected_rails"]:
        for key in [rail["root_group"]]+[b["group"] for b in rail["branches"]]:
            pads = [objects[uid] for uid in captured["groups"][key] if objects[uid]["kind"] == "PAD" and objects[uid]["pin"]]
            assert pads and all(by_pad[(p["ref"], p["pin"])]["native_connected_to_source"] for p in pads), "Planned supply island not native connected"


def check():
    parent = parent_check()
    assert parent == json.loads((SOURCE / "routing-handoff.json").read_text())
    names = ("native-inputs.json", "distribution-construction.json", "native-refill.json", "placement-native-review.json", "supply-connectivity-review.json")
    reports = {name: json.loads((OUT / name).read_text()) for name in names}
    for report in reports.values():
        verify_hashes(report["source_sha256"])
    capture, construction = reports["native-inputs.json"], reports["distribution-construction.json"]
    native, witness, refill = reports["placement-native-review.json"], reports["supply-connectivity-review.json"], reports["native-refill.json"]
    pcb = OUT / "audio_core.kicad_pcb"
    assert sha(pcb) == refill["filled_PCB_sha256"] and sha(OUT / "native-refill-export.kicad_pcb") == refill["native_export_sha256"]
    assert sha(OUT / "distribution-input.kicad_pcb") == construction["authored_PCB_sha256"]
    board = read_sexpr(pcb.read_text())
    assert without_fill(board) == without_fill(read_sexpr((OUT / "distribution-input.kicad_pcb").read_text()))
    exported = read_sexpr((OUT / "native-refill-export.kicad_pcb").read_text())
    native_fill = {str(first(z, "uuid")[1]): children(z, "filled_polygon") for z in children(exported, "zone") if not children(z, "keepout")}
    for zone in children(board, "zone"):
        if not children(zone, "keepout"):
            assert children(zone, "filled_polygon") == native_fill[str(first(zone, "uuid")[1])], "Stored fill differs from actual native refill"
    for p in SOURCE.iterdir():
        if p.suffix in (".kicad_sch", ".kicad_pro", ".kicad_sym", ".kicad_dru") or p.name in ("plan.json", "fp-lib-table", "sym-lib-table"):
            assert (OUT / p.name).read_bytes() == p.read_bytes()
    proof = verify_board(board, construction, capture)
    verify_witnesses(witness, capture, construction)
    assert witness["tracks"] == proof["tracks"] and witness["vias"] == proof["vias"]
    drc, erc = [json.loads((OUT / name).read_text()) for name in ("drc.json", "erc.json")]
    assert drc["violations"] == [] and drc["ignored_checks"] == erc["ignored_checks"] == []
    assert drc["schematic_parity"] == json.loads((SOURCE / "drc.json").read_text())["schematic_parity"]
    assert not any(s["violations"] for s in erc["sheets"]) and len(erc["sheets"]) == 7
    assert all(sha(OUT / name) == h for name, h in native["raw_report_sha256"].items())
    assert native["DRC_geometry_findings"] == native["ERC_findings"] == 0 and native["schematic_parity_findings"] == 1
    assert all(c["returncode"] == 0 for c in native["complete_native_commands"])
    opens = native["uncapped_open_connections"]
    assert opens == len(drc["unconnected_items"]) == witness["uncapped_open_connections"] < parent["uncapped_open_connections"]
    paths = [Path(__file__), ROOT / "audio_main_power_routes.py", SOURCE / "routing-handoff.json"]+[OUT / name for name in names]
    result = dict(parent)
    result.update(proof)
    result.update(source_sha256=relative_hashes(paths), uncapped_open_connections=opens,
                  placed_supply_pads=len(witness["supply_pads"]), connected_supply_pads=witness["connected_supply_pads"],
                  complete_supply_routing=False, reference_refilled_for_new_supply_vias=True,
                  supply_current_drop_return_noise_fault_and_process_qualified=False, fabrication_released=False)
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
    print("Audio supplies:", result["connected_supply_pads"], "/", result["placed_supply_pads"], "; opens", result["uncapped_open_connections"])
