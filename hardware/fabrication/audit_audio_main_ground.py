"""Replay actual ground copper, protected voids and native 200-pad continuity."""

import argparse
import copy
import json
import math
from pathlib import Path

from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import unary_union

from hardware.electronics.common.netlists import netlist
from hardware.electronics.common.sexpr import children, first, read_sexpr, sexpr
from hardware.fabrication.audio_main_local_routes import relative_hashes, verify_hashes
from hardware.fabrication.audit_audio_main_placement import verify_geometry
from hardware.fabrication.audit_audio_main_repack import check as check_parent
from hardware.fabrication.audit_candidate import sha
from hardware.fabrication.route_nf_surface import shape

REPO = Path(__file__).resolve().parents[2]
ROOT = REPO / "hardware/fabrication"
OUT = ROOT / "staging/audio-main-ground-02"
TRIAL = ROOT / "staging/audio-main-ground-01"
PARENT = ROOT / "staging/audio-main-local-routing-03"


def fps(board):
    return {next(p[2] for p in children(fp, "property") if p[1] == "Reference"): fp
            for fp in children(board, "footprint")}


def region(zone):
    return Polygon([tuple(map(float, p[1:3])) for p in children(first(first(zone, "polygon"), "pts"), "xy")])


def verify_ground_witness(report, pads):
    expected = {(p["ref"], p["pin"]) for p in pads["objects"] if p["net"] == "AGND"}
    actual = {(p["ref"], p["pin"]) for p in report["ground_pads"]}
    assert report["reference_terminal"] == ["J701", "2"]
    assert actual == expected and len(actual) == len(report["ground_pads"]) == 200
    assert report["connected_ground_pads"] == report["ground_pad_count"] == 200
    assert all(p["native_connected_to_input_ground"] for p in report["ground_pads"]), "Unconnected ground terminal"


def verify_board(board, escapes, pads):
    parent = read_sexpr((PARENT / "audio_core.kicad_pcb").read_text())
    expected = copy.deepcopy(parent)
    first(fps(expected)["C310"], "at")[1:4] = [94.5, 32, 270]
    assert board[:len(expected)] == read_sexpr(sexpr(expected)), "Changed parent critical copper or undeclared receiving"
    plan = json.loads((OUT / "plan.json").read_text())
    parts, pins = netlist(OUT / "native-netlist.xml")
    geometry = verify_geometry([n for n in expected if not isinstance(n, list) or not n or n[0] not in ("segment", "via")], plan, parts, pins)
    assert geometry == escapes["receiving_geometry"]
    added = board[len(parent):]
    assert all(n[0] in ("segment", "via", "zone") for n in added)
    segments = {str(first(n, "uuid")[1]): n for n in added if n[0] == "segment"}
    vias = {str(first(n, "uuid")[1]): n for n in added if n[0] == "via"}
    assert len(segments)+len(vias) == sum(n[0] in ("segment", "via") for n in added)
    all_vias = {str(first(n, "uuid")[1]): n for n in children(board, "via")}
    net_names = {str(n[1]): str(n[2]) for n in children(board, "net")}
    terminals = {(p["ref"],p["pin"]): p for p in pads["objects"] if p["pin"]}
    used_tracks, used_vias = set(), set()
    assert len(escapes["ground_escapes"]) == 182 and escapes["deferred_ground_groups"] == []
    for row in escapes["ground_escapes"]:
        pad = terminals[(row["ref"],row["pin"])]
        assert row["net"] == pad["net"] == "AGND" and row["layer"] in pad["layers"]
        assert math.dist(row["path_mm"][0], pad["position_mm"]) < 1e-7
        ids = row["segment_uuids"]
        assert len(ids) == len(row["path_mm"])-1
        length = 0.0
        for ident, start, end in zip(ids,row["path_mm"],row["path_mm"][1:]):
            node = segments[ident]
            assert first(node,"layer")[1] == row["layer"] and net_names[str(first(node,"net")[1])] == "AGND"
            assert float(first(node,"width")[1]) == .2
            assert math.dist(list(map(float,first(node,"start")[1:3])),start) < 1e-7
            assert math.dist(list(map(float,first(node,"end")[1:3])),end) < 1e-7
            used_tracks.add(ident)
            length += math.dist(start,end)
        limit = 5.6 if (row["ref"],row["pin"]) == ("U205","2") else 3.5
        assert length <= limit+1e-8 and abs(length-row["actual_length_mm"]) < 1e-7
        assert row["maximum_length_mm"] <= limit+1e-8
        ident = row["via_uuid"]
        via = all_vias[ident]
        assert math.dist(list(map(float,first(via,"at")[1:3])),row["path_mm"][-1]) < 1e-7
        assert net_names[str(first(via,"net")[1])] == "AGND"
        used_vias.add(ident)
    assert used_tracks == segments.keys() and used_vias == vias.keys()
    for via in vias.values():
        assert first(via,"layers")[1:] == ["F.Cu","B.Cu"]
        assert float(first(via,"size")[1]) == .6 and float(first(via,"drill")[1]) == .3
    # Every actual drill, including the retained signal escapes, is screened
    # against fresh native solder-land polygons on both faces and on the same net.
    smd = [shape(ps) for p in pads["objects"] if not any(p["drill_mm"])
           for layer,ps in p["layers"].items() if layer in ("F.Cu","B.Cu") and ps]
    minimum = min(Point(list(map(float,first(v,"at")[1:3]))).distance(p)-float(first(v,"drill")[1])/2
                  for v in children(board,"via") for p in smd)
    assert minimum >= .15-1e-7, "Via drill approaches a solder land"
    zones = [n for n in added if n[0] == "zone"]
    planes = [z for z in zones if not children(z,"keepout")]
    assert len(planes) == 1 and first(planes[0],"net_name")[1] == "AGND", "Unassigned ground plane"
    assert net_names[str(first(planes[0],"net")[1])] == "AGND" and first(planes[0],"layer")[1] == "In1.Cu"
    assert region(planes[0]).equals(box(.5,.5,149.5,62.5))
    full, sensitive = [], []
    for z in zones:
        if not children(z,"keepout"):
            continue
        layers = set(first(z,"layers")[1:])
        policies = {n[0]:n[1] for n in first(z,"keepout")[1:]}
        assert policies["copperpour"] == "not_allowed"
        if layers == {"F.Cu","B.Cu","In1.Cu","In2.Cu"}:
            assert policies["tracks"] == policies["vias"] == "not_allowed"
            full.append(region(z))
        else:
            assert layers == {"In1.Cu","In2.Cu"} and policies["tracks"] == policies["vias"] == "allowed"
            sensitive.append(region(z))
    assert len(full) == 6 and len(sensitive) == 12, "Missing support or sensitive-node exclusions"
    for x,y in ((4,4),(146,4),(4,59),(146,59),(10,56),(82,56)):
        assert any(p.hausdorff_distance(box(x-3.6,y-3.6,x+3.6,y+3.6)) < 1e-8 for p in full)
    sensitive_nets = {terminals[(r,p)]["net"] for r in ("U101","U102") for p in ("1","4","5","8")}
    sensitive_nets |= {terminals[(r,p)]["net"] for r in ("U301","U302","U303","U304") for p in ("2","6")}
    shapes = [shape(ps).buffer(.5) for p in pads["objects"] if p["net"] in sensitive_nets
              for layer,ps in p["layers"].items() if layer in ("F.Cu","B.Cu") and ps]
    for track in children(parent,"segment"):
        if net_names[str(first(track,"net")[1])] in sensitive_nets:
            shapes.append(LineString([list(map(float,first(track,k)[1:3])) for k in ("start","end")]).buffer(.6))
    # Authored coordinates are serialized to six decimal places in millimetres
    # (one nanometre); permit only the corresponding boundary quantization.
    assert unary_union(sensitive).buffer(1e-6).covers(unary_union(shapes)), "Sensitive plane opening omitted"
    fills = [Polygon([tuple(map(float,p[1:3])) for p in children(first(f,"pts"),"xy")]).buffer(0)
             for f in children(planes[0],"filled_polygon")]
    copper = unary_union(fills)
    assert not copper.is_empty and copper.area > 7500
    exclusions = unary_union(full+sensitive)
    assert copper.intersection(exclusions.buffer(-1e-6)).area < 1e-8, "Ground fill entered an exclusion"
    return dict(geometry, tracks=len(children(board,"segment")), vias=len(children(board,"via")),
                added_ground_escape_branches=182, added_ground_vias=len(vias), ground_pad_count=200,
                connected_ground_pads=200, connected_signal_supply_endpoints=131,
                connected_declared_local_ground_returns=20, local_connected_pairs=151,
                ground_plane_layer="In1.Cu", ground_plane_area_mm2=round(copper.area,6),
                plane_void_boundary_comparison_tolerance_mm=1e-6,
                minimum_screened_drill_edge_to_SMD_copper_mm=round(minimum,9),
                critical_analog_copper_and_poses_preserved=True, current_receiving_geometry_renewed=True)


def check():
    parent = check_parent()
    names = ("construction.json","escape-construction.json","final-fill.json","placement-native-review.json",
             "local-connectivity-review.json","ground-connectivity-review.json","native-pad-capture.json")
    reports = {name:json.loads((OUT/name).read_text()) for name in names}
    for report in reports.values():
        verify_hashes(report["source_sha256"])
    pcb = OUT/"audio_core.kicad_pcb"
    assert sha(pcb) == reports["construction.json"]["candidate_PCB_sha256"] == reports["final-fill.json"]["filled_PCB_sha256"]
    for p in PARENT.iterdir():
        if p.suffix in (".kicad_sch",".kicad_pro",".kicad_sym",".kicad_dru"):
            assert (OUT/p.name).read_bytes() == p.read_bytes()
    board = read_sexpr(pcb.read_text())
    proof = verify_board(board,reports["escape-construction.json"],reports["native-pad-capture.json"])
    verify_ground_witness(reports["ground-connectivity-review.json"],reports["native-pad-capture.json"])
    native = reports["placement-native-review.json"]
    assert all(sha(OUT/p) == h for p,h in native["raw_report_sha256"].items())
    drc,erc = [json.loads((OUT/p).read_text()) for p in ("drc.json","erc.json")]
    assert drc["violations"] == [] and drc["ignored_checks"] == erc["ignored_checks"] == []
    assert drc["schematic_parity"] == json.loads((PARENT/"drc.json").read_text())["schematic_parity"]
    assert not any(s["violations"] for s in erc["sheets"]) and len(erc["sheets"]) == 7
    assert all(c["returncode"] == 0 for c in native["complete_native_commands"])
    assert native["DRC_geometry_findings"] == native["ERC_findings"] == 0 and native["schematic_parity_findings"] == 1
    assert native["uncapped_open_connections"] == len(drc["unconnected_items"]) == reports["ground-connectivity-review.json"]["uncapped_open_connections"] == 393
    old_routes = json.loads((PARENT/"construction.json").read_text())["routes"]
    witnesses = [dict(ref=r["ref"],pin=r["pin"],owner=r["owner"],owner_pin=r["owner_pin"],native_connected=True) for r in old_routes]
    assert reports["local-connectivity-review.json"]["connections"] == witnesses
    assert reports["local-connectivity-review.json"]["native_via_count"] == proof["vias"]
    paths = [Path(__file__),PARENT/"routing-handoff.json"]+[OUT/name for name in names]
    result = dict(parent)
    result.pop("three_unrouted_parts_relocated",None)
    result.pop("native_pad_geometry_independently_matches_planning_transform",None)
    result.update(proof)
    result.update(source_sha256=relative_hashes(paths),uncapped_open_connections=393,
                  deferred_local_ground_pairs=0,connected_actual_power_ground_pairs=20,
                  explicit_prior_local_ground_pair_tracks=7,unrouted_part_pose_changes_total=4,
                  native_pad_geometry_independently_captured_current=True,
                  complete_ground_return_and_power_distribution=False,PCB_routed=False,
                  ground_connectivity_is_not_PDN_noise_thermal_or_stability_qualification=True,
                  fabrication_released=False)
    return result


if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check",action="store_true")
    args=parser.parse_args()
    result=check()
    handoff=OUT/"routing-handoff.json"
    if args.check:
        assert result == json.loads(handoff.read_text())
    else:
        with handoff.open("x") as f:
            json.dump(result,f,indent=2)
            f.write("\n")
    print("Audio ground: 200/200 input-ground pads; 131/131 signal/supply endpoints; 393 opens")
