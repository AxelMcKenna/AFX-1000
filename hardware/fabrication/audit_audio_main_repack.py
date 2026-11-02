"""Independently replay the three-pose change and two closed audio endpoints."""

import argparse
import copy
import json
import math
import xml.etree.ElementTree as ET
from pathlib import Path

from shapely.geometry import Point

from hardware.electronics.common.netlists import netlist
from hardware.electronics.common.sexpr import children, first, read_sexpr, sexpr
from hardware.fabrication.audio_main_local_routes import relative_hashes, verify_hashes
from hardware.fabrication.audit_audio_main_placement import verify_geometry
from hardware.fabrication.audit_audio_main_routes import check as check_parent
from hardware.fabrication.audit_candidate import sha
from hardware.fabrication.route_nf_surface import shape

REPO = Path(__file__).resolve().parents[2]
ROOT = REPO / "hardware/fabrication"
OUT = ROOT / "staging/audio-main-local-routing-03"
PARENT = ROOT / "staging/audio-main-local-routing-02"


def fps(board):
    return {next(p[2] for p in children(fp, "property") if p[1] == "Reference"): fp
            for fp in children(board, "footprint")}


def verify_delta(board, construction, native_pads):
    parent = read_sexpr((PARENT / "audio_core.kicad_pcb").read_text())
    expected = copy.deepcopy(parent)
    changes = construction["declared_pose_changes"]
    assert set(changes) == {"D102", "C118", "R324"}, "Unexpected component relocation"
    old, updated = fps(parent), fps(expected)
    for ref, change in changes.items():
        assert list(map(float, first(old[ref], "at")[1:4])) == change["before"]
        first(updated[ref], "at")[1:4] = change["after"]
    assert board[:len(expected)] == read_sexpr(sexpr(expected)), "Changed parent copper, critical pose, land or pin net"
    added = board[len(expected):]
    assert len(added) > 0 and all(n[0] in ("segment", "via") for n in added)
    segments = {str(first(s, "uuid")[1]): s for s in added if s[0] == "segment"}
    vias = {str(first(s, "uuid")[1]): s for s in added if s[0] == "via"}
    assert len(segments) + len(vias) == len(added)
    pads = {(p["ref"], p["pin"]): p for p in native_pads["objects"] if p["pin"]}
    nets = {str(n[1]): str(n[2]) for n in children(board, "net")}
    rows = construction["added_routes"]
    assert {(r["ref"], r["pin"], r["owner"], r["owner_pin"]) for r in rows} == {
        ("R319", "1", "U303", "6"), ("C127", "1", "U102", "3")}
    used_segments, used_vias = set(), set()
    for row in rows:
        p, q = pads[(row["ref"], row["pin"])], pads[(row["owner"], row["owner_pin"])]
        assert p["net"] == q["net"] == row["net"]
        paths = row["paths"]
        assert math.dist(paths[0][1][0], p["position_mm"]) < 1e-7
        assert math.dist(paths[-1][1][-1], q["position_mm"]) < 1e-7
        segment_ids = iter(row["segment_uuids"])
        transitions = []
        length = 0.0
        for index, (layer, points) in enumerate(paths):
            assert layer in ("F.Cu", "B.Cu")
            if index:
                previous_layer, previous = paths[index-1]
                assert previous_layer != layer and math.dist(previous[-1], points[0]) < 1e-7
                transitions.append(points[0])
            for start, end in zip(points, points[1:]):
                ident = next(segment_ids)
                segment = segments[ident]
                assert first(segment, "layer")[1] == layer
                assert nets[str(first(segment, "net")[1])] == row["net"]
                assert float(first(segment, "width")[1]) == .2
                assert math.dist(list(map(float, first(segment, "start")[1:3])), start) < 1e-7
                assert math.dist(list(map(float, first(segment, "end")[1:3])), end) < 1e-7
                used_segments.add(ident)
                length += math.dist(start, end)
        assert next(segment_ids, None) is None
        limit = 6.4 if row["ref"] == "R319" else 5.6
        assert length <= limit and abs(length-row["actual_length_mm"]) < 1e-7
        assert row["route_length_limit_mm"] <= limit + 1e-8
        assert len(row["via_uuids"]) == len(transitions) == 2
        for ident, xy in zip(row["via_uuids"], transitions):
            via = vias[ident]
            assert math.dist(list(map(float, first(via, "at")[1:3])), xy) < 1e-7
            assert nets[str(first(via, "net")[1])] == row["net"]
            assert float(first(via, "size")[1]) == .6 and float(first(via, "drill")[1]) == .3
            assert first(via, "layers")[1:] == ["F.Cu", "B.Cu"]
            used_vias.add(ident)
    assert used_segments == segments.keys() and used_vias == vias.keys()
    previous = json.loads((PARENT / "construction.json").read_text())
    assert construction["routes"] == previous["routes"] + rows
    assert construction["requests"] == previous["requests"]
    assert construction["deferred"] == [r for r in previous["deferred"] if r["kind"] == "local_ground_return"]
    types = {(n.attrib["ref"], n.attrib["pin"]): n.attrib["pintype"]
             for n in ET.parse(OUT / "native-netlist.xml").findall("nets/net/node")}
    for row in construction["requests"]:
        if row["kind"] == "local_ground_return":
            assert types[(row["owner"], row["owner_pin"])] == "power_in"
    smd = [shape(polys) for p in native_pads["objects"] if not any(p["drill_mm"])
           for layer, polys in p["layers"].items() if layer in ("F.Cu", "B.Cu") and polys]
    gaps = [Point(list(map(float, first(v, "at")[1:3]))).distance(p) - float(first(v, "drill")[1])/2
            for v in children(board, "via") for p in smd]
    minimum = min(gaps)
    assert minimum >= .15-1e-7, "Drill-to-SMD receiving violated"
    return dict(local_connected_pairs=138, connected_signal_supply_endpoints=131,
                connected_actual_power_ground_pairs=7, deferred_signal_supply_pairs=[],
                deferred_local_ground_pairs=13, tracks=len(children(board, "segment")),
                vias=len(children(board, "via")), minimum_screened_drill_edge_to_SMD_copper_mm=minimum,
                three_unrouted_parts_relocated=True, all_parent_copper_and_critical_poses_preserved=True)


def check():
    parent = check_parent()
    reports = {name: json.loads((OUT / name).read_text()) for name in (
        "construction.json", "placement-native-review.json", "local-connectivity-review.json", "native-pad-capture.json")}
    for report in reports.values():
        verify_hashes(report["source_sha256"])
    construction = reports["construction.json"]
    assert construction["candidate_PCB_sha256"] == sha(OUT / "audio_core.kicad_pcb")
    for name in ("audio_core.kicad_pro", "audio_core.kicad_dru"):
        assert (OUT / name).read_bytes() == (PARENT / name).read_bytes()
    board = read_sexpr((OUT / "audio_core.kicad_pcb").read_text())
    proof = verify_delta(board, construction, reports["native-pad-capture.json"])
    plan = json.loads((OUT / "plan.json").read_text())
    parts, pins = netlist(OUT / "native-netlist.xml")
    geometry = verify_geometry([n for n in board if not isinstance(n, list) or not n or n[0] not in ("segment", "via")], plan, parts, pins)
    assert geometry == construction["receiving_geometry"]
    planning = json.loads((OUT / "planning-pad-inputs.json").read_text())
    verify_hashes(planning["source_sha256"])
    def pad_key(pad):
        # These authored boards omit pad UUIDs; KiCad allocates fresh UUIDs on
        # each load. Match the physical terminal, including distinct unnumbered
        # connector locating holes, rather than treating a generated UUID as ID.
        return pad["ref"], pad["pin"], tuple(round(v, 6) for v in pad["position_mm"])

    expected = {pad_key(p): p for p in planning["objects"]}
    observed = reports["native-pad-capture.json"]["objects"]
    assert len(expected) == len(observed) == 930
    for pad in observed:
        old = expected[pad_key(pad)]
        assert all(pad[k] == old[k] for k in ("ref", "pin", "net", "drill_mm", "npth"))
        assert math.dist(pad["position_mm"], old["position_mm"]) < 1e-6
        assert pad["layers"].keys() == old["layers"].keys()
        for layer, polygons in pad["layers"].items():
            if polygons:
                assert shape(polygons).hausdorff_distance(shape(old["layers"][layer])) <= .0021
    native = reports["placement-native-review.json"]
    assert all(sha(OUT / p) == h for p, h in native["raw_report_sha256"].items())
    drc, erc = [json.loads((OUT / p).read_text()) for p in ("drc.json", "erc.json")]
    assert drc["violations"] == [] and drc["ignored_checks"] == erc["ignored_checks"] == []
    assert drc["schematic_parity"] == json.loads((PARENT / "drc.json").read_text())["schematic_parity"]
    assert not any(s["violations"] for s in erc["sheets"]) and len(erc["sheets"]) == 7
    assert all(c["returncode"] == 0 for c in native["complete_native_commands"])
    assert native["DRC_geometry_findings"] == native["ERC_findings"] == 0 and native["schematic_parity_findings"] == 1
    connectivity = reports["local-connectivity-review.json"]
    assert connectivity["connections"] == [dict(ref=r["ref"], pin=r["pin"], owner=r["owner"], owner_pin=r["owner_pin"], native_connected=True)
                                             for r in construction["routes"]]
    assert connectivity["native_via_count"] == proof["vias"] == 20
    assert native["uncapped_open_connections"] == connectivity["uncapped_open_connections"] == 585
    clamp_path = OUT / "additional-clamp-connectivity.json"
    clamp = json.loads(clamp_path.read_text())
    verify_hashes(clamp["source_sha256"])
    assert (clamp["ref"], clamp["pin"], clamp["owner"], clamp["owner_pin"], clamp["net"]) == ("D102", "2", "U102", "3", "V5_REG")
    assert clamp["native_connected"] and clamp["uncapped_open_connections"] == 585
    paths = [Path(__file__), PARENT / "routing-handoff.json", clamp_path] + [OUT / name for name in reports]
    return dict(parent, source_sha256=relative_hashes(paths)) | geometry | proof | dict(
        uncapped_open_connections=585, additional_native_clamp_supply_connections=1, current_receiving_geometry_renewed=True,
        native_pad_geometry_independently_matches_planning_transform=True,
        PCB_routed=False, fabrication_released=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    result = check()
    handoff = OUT / "routing-handoff.json"
    if args.check:
        assert result == json.loads(handoff.read_text())
    else:
        with handoff.open("x") as f:
            json.dump(result, f, indent=2)
            f.write("\n")
    print("Audio local rework:", result["local_connected_pairs"], "pairs plus clamp supply; 131/131 signal-supply endpoints; 585 opens")
