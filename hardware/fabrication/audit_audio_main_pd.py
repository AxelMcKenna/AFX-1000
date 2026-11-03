"""Validate additive PD copper without weakening analog masks or prior wiring."""

import argparse
import copy
import json
import math
import xml.etree.ElementTree as ET
from pathlib import Path

from shapely.geometry import LineString, Point
from shapely.ops import unary_union

from hardware.electronics.common.sexpr import read_sexpr, sexpr
from hardware.fabrication.audio_main_bypass_repack import add_geometry, add_via
from hardware.fabrication.audio_main_local_routes import relative_hashes, verify_hashes
from hardware.fabrication.audio_main_noise_audit import measure
from hardware.fabrication.audio_main_pd_routes import OUT, PLAN, ROOT, SOURCE
from hardware.fabrication.audio_main_quiet_screen import QuietTraceScreen
from hardware.fabrication.audit_audio_main_named_routes import NETS, NOISY, point
from hardware.fabrication.audit_audio_main_six_preparation import verify_fill
from hardware.fabrication.audit_audio_main_supplies import without_fill
from hardware.fabrication.audit_audio_main_supply_completion import verify_native
from hardware.fabrication.audit_candidate import sha
from hardware.fabrication.route_nf_surface import shape

ELIGIBLE = {"/ADC/PD_GATED", "/ADC/PD_L", "/ADC/PD_R"}


def read(name):
    return json.loads((OUT / name).read_text())


def verify_routes(parent, board, record, captured):
    assert set(record["allowed_nets"]) <= ELIGIBLE
    assert set(record["allowed_nets"]) == {r["net"] for r in record["routes"]}
    assert record["complete_target_nets"] == ["/ADC/PD_GATED"]
    assert record["trace_width_mm"] == record["clearance_mm"] == .2 and record["planning_margin_mm"] == .01
    assert record["comparator_centreline_clearance_mm"] == .71
    assert len(record["routes"]) == 6 and captured["native_uncapped_opens"] == 171 and captured["layer_count"] == 6
    native = {o["uuid"]: o for o in captured["objects"]}
    pads = {(o["ref"], o["pin"]): o for o in native.values() if o["kind"] == "PAD" and o["pin"]}
    membership = {uid: k for k, ids in captured["groups"].items() for uid in ids}
    groups = {frozenset([k]) for k in captured["groups"]}
    screen = QuietTraceScreen(captured, NETS)
    expected, additions = copy.deepcopy(parent), []
    all_vias = []
    for row in record["routes"]:
        net, runs, vias = row["net"], row["runs"], row["new_vias_mm"]
        assert net in ELIGIBLE and row["purpose"] == "ADC_power_down_control"
        p, q = [pads[tuple(k)] for k in row["endpoints"]]
        assert p["net"] == q["net"] == net
        left, right = [frozenset(k) for k in row["source_groups"]]
        assert left != right and not left & right and left in groups and right in groups, "False native island merge"
        assert membership[p["uuid"]] in left and membership[q["uuid"]] in right
        assert row["terminal_points_mm"] == [p["position_mm"], q["position_mm"]]
        assert point(runs[0][1][0]) == point(p["position_mm"]) and point(runs[-1][1][-1]) == point(q["position_mm"])
        assert p["layers"].get(runs[0][0]) and q["layers"].get(runs[-1][0])
        length = sum(LineString(ps).length for _, ps in runs)
        limit = min(40, 2*math.dist(p["position_mm"], q["position_mm"])+6)
        assert row["maximum_planar_length_mm"] == limit and abs(length-row["planar_length_mm"]) < 1e-7 and length <= limit
        assert row["maximum_new_vias"] == 2 and len(vias) in (0, 2)
        if vias:
            assert len(runs) == 3 and runs[1][0] in ("In2.Cu", "In3.Cu")
            for i in (0, 2):
                assert runs[i][0] in ("F.Cu", "B.Cu") and LineString(runs[i][1]).length <= 3.5
            assert [point(runs[0][1][-1]), point(runs[1][1][-1])] == list(map(point, vias))
            assert point(runs[1][1][0]) == point(vias[0]) and point(runs[2][1][0]) == point(vias[1])
        else:
            assert len(runs) == 1 and runs[0][0] in ("F.Cu", "B.Cu")
        for i, xy in enumerate(vias):
            assert screen.via_legal(net, xy) and all(math.dist(xy, other) > .86 for _, other in screen.vias+screen.new_vias)
            assert all(math.dist(xy, other) > .86 for other in vias[:i])
            all_vias.append(xy)
        # One contact with the existing tree at each endpoint; no redundant
        # same-net return or accidental third source-island connection.
        for face, points in runs:
            assert screen.legal(net, face, points), "Trace violates copper, protected regions or comparator spacing"
            allowed = unary_union([shape(o["layers"].get(face, [])).buffer(.101) for o in (p, q)])
            line = LineString(points)
            geometries = [shape(o["layers"][face]) for o in native.values() if o["net"] == net and o["layers"].get(face)]
            geometries += [g for n, f, g in screen.added if n == net and f == face]
            assert all(line.intersection(g.buffer(.1)).difference(allowed).is_empty for g in geometries), "Nonterminal same-net contact"
            add_geometry(expected, additions, net, face, points, .2, row["purpose"])
        for xy in vias:
            add_via(expected, additions, net, xy, row["purpose"])
        screen.added.extend((net, face, LineString(points)) for face, points in runs)
        screen.new_vias.extend((net, xy) for xy in vias)
        groups.difference_update([left, right])
        groups.add(left | right)
    expected = read_sexpr(sexpr(expected))
    assert without_fill(board) == without_fill(expected), "Retained or added copper, pads, poses, keepouts or stack changed"
    assert record["added_segments"] == [r for r in additions if r["kind"] == "segment"]
    assert record["added_vias"] == [r for r in additions if r["kind"] == "via"]
    smd = [shape(polygons) for o in captured["objects"] if o["kind"] == "PAD" and not any(o["drill_mm"])
           for face, polygons in o["layers"].items() if face in ("F.Cu", "B.Cu") and polygons]
    minimum = min(Point(xy).distance(g)-.15 for xy in all_vias for g in smd)
    assert minimum >= .16-1e-7
    # Native source pin roles establish this is the existing supervisor/PD
    # circuit, rather than a relay-current, supply or differential-audio net.
    document = ET.parse(SOURCE / "native-netlist.xml")
    circuit = {n.attrib["name"]: {(p.attrib["ref"], p.attrib["pin"]): p.attrib for p in n.findall("node")} for n in document.findall(".//nets/net")}
    assert circuit["/ADC/PD_GATED"]["U108", "1"]["pintype"] == "open_collector"
    for ref, net in (("U101", "/ADC/PD_L"), ("U102", "/ADC/PD_R")):
        assert circuit[net][ref, "7"]["pinfunction"] == "PD_7" and circuit[net][ref, "7"]["pintype"] == "input"
    return round(minimum, 9)


def check():
    names = ["distribution-construction.json", "native-refill.json", "terminal-connectivity-review.json", "additional-terminal-review.json",
             "current-native-pads.json", "final-native-inputs.json"]
    reports = {n: read(n) for n in names}
    for report in reports.values():
        verify_hashes(report["source_sha256"])
        assert not report["fabrication_released"]
    captured = json.loads((SOURCE / "final-native-inputs.json").read_text())
    verify_hashes(captured["source_sha256"])
    parent = read_sexpr((SOURCE / "audio_core.kicad_pcb").read_text())
    record = reports["distribution-construction.json"]
    assert sha(OUT / "distribution-input.kicad_pcb") == record["authored_PCB_sha256"]
    ground = verify_fill(OUT, read_sexpr((OUT / "distribution-input.kicad_pcb").read_text()), "audio_core.kicad_pcb", "native-refill-export.kicad_pcb", reports["native-refill.json"])
    minimum = verify_routes(parent, read_sexpr((OUT / "audio_core.kicad_pcb").read_text()), record, captured)
    native = verify_native(OUT)
    source_witness = json.loads((SOURCE / "terminal-connectivity-review.json").read_text())
    witness, extra, final = reports["terminal-connectivity-review.json"], reports["additional-terminal-review.json"], reports["final-native-inputs.json"]
    for key in ("retained_local_pairs", "retained_control_pairs", "ground_pads", "supply_pads"):
        assert witness[key] == source_witness[key]
    source_objects = {o["uuid"]: o for o in captured["objects"]}
    expected = []
    for row in record["routes"]:
        pads = [source_objects[uid] for side in row["source_groups"] for k in side for uid in captured["groups"][k]
                if source_objects[uid]["kind"] == "PAD" and source_objects[uid]["pin"]]
        expected.append(dict(net=row["net"], source_groups=row["source_groups"], reference_terminal=[pads[0]["ref"], pads[0]["pin"]],
                             contacts=[dict(ref=p["ref"], pin=p["pin"], native_connected=True) for p in pads]))
    assert witness["new_route_witnesses"] == expected
    inherited = json.loads((SOURCE / "additional-terminal-review.json").read_text())
    assert extra["retained_global_control_witnesses"] == inherited["retained_global_control_witnesses"]+source_witness["new_route_witnesses"]
    assert len(extra["retained_global_control_witnesses"]) == 102 and extra["retained_private_timing_connections"] == inherited["retained_private_timing_connections"]
    def pads(rows):
        return {(o["ref"], o["pin"], point(o["position_mm"])): {k: o[k] for k in ("net", "layers", "drill_mm", "npth")} for o in rows if o["kind"] == "PAD"}
    assert pads(captured["objects"]) == pads(final["objects"]) == pads(reports["current-native-pads.json"]["objects"]) and len(pads(final["objects"])) == 930
    final_objects = {o["uuid"]: o for o in final["objects"]}
    counts = {}
    for net in ELIGIBLE | NETS:
        islands = [k for k, ids in final["groups"].items() if any(final_objects[i]["kind"] == "PAD" and final_objects[i]["net"] == net for i in ids)]
        counts[net] = len(islands)
    assert counts["/ADC/PD_GATED"] == 1 and counts["/ADC/PD_L"] == 3 and counts["/ADC/PD_R"] == 2
    assert all(counts[n] == 1 for n in NETS)
    assert final["layer_count"] == 6 and native["uncapped_open_connections"] == witness["uncapped_open_connections"] == extra["uncapped_open_connections"] == final["native_uncapped_opens"] == record["expected_native_opens"] == 165
    noise = measure(final, NETS, NOISY | ELIGIBLE)
    assert noise["violations"] == []
    for p in SOURCE.rglob("*"):
        rel = p.relative_to(SOURCE)
        if p.is_file() and (rel.parts[0] == "libraries" or p.parent == SOURCE and (p.suffix in (".kicad_sch", ".kicad_pro", ".kicad_sym", ".kicad_dru") or p.name in ("plan.json", "fp-lib-table", "sym-lib-table"))):
            assert sha(p) == sha(OUT / rel)
    return dict(source_sha256=relative_hashes([Path(__file__), PLAN, ROOT / "audio_main_quiet_screen.py", ROOT / "audio_main_noise_audit.py",
                ROOT / "audit_audio_main_named_routes.py", SOURCE / "audio_core.kicad_pcb", SOURCE / "final-native-inputs.json", SOURCE / "native-netlist.xml",
                SOURCE / "comparator-closure-review.json", SOURCE / "terminal-connectivity-review.json", SOURCE / "additional-terminal-review.json",
                OUT / "placement-native-review.json"]+[OUT / n for n in names]),
                uncapped_open_connections=165, added_connections=6, added_tracks=len(record["added_segments"]), added_vias=len(record["added_vias"]),
                native_geometry_findings=0, native_ERC_findings=0, missing_codec_parity_findings=1,
                all_parent_copper_poses_pads_stack_and_masks_exact=True, native_pad_count=930, native_islands_by_net=counts,
                complete_PD_supervisor_bus=True, remaining_amplifier_PD_gaps=3, comparator_input_gaps=0,
                inherited_witness_rows=102, ground_plane_area_mm2=ground, minimum_new_drill_edge_to_SMD_mm=minimum,
                exhaustive_noise_geometry=noise, electrical_PD_response_and_noise_qualified=False, fabrication_released=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    result = check()
    if args.write:
        (OUT / "PD-routing-review.json").write_text(json.dumps(result, indent=2)+"\n")
    print(json.dumps(result, indent=2))
