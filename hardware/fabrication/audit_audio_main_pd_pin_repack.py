"""Review the two passive moves, shared PD branch and complete legacy control cap."""

import argparse
import copy
import json
import math
from collections import Counter
from pathlib import Path

from shapely.affinity import translate
from shapely.geometry import LineString, Point
from shapely.ops import unary_union

from hardware.electronics.common.sexpr import children, first, read_sexpr, sexpr
from hardware.fabrication.audio_main_bypass_repack import add_geometry, add_via
from hardware.fabrication.audio_main_local_repack import ReceivingSpace, footprints
from hardware.fabrication.audio_main_local_routes import relative_hashes, verify_hashes
from hardware.fabrication.audio_main_noise_audit import measure
from hardware.fabrication.audio_main_pd_entry_screen import PDEntryScreen
from hardware.fabrication.audio_main_pd_pin_repack import OUT, PLAN, ROOT, ROUTES, SOURCE
from hardware.fabrication.audio_main_quiet_screen import QuietTraceScreen
from hardware.fabrication.audit_audio_main_named_routes import NETS, NOISY, point
from hardware.fabrication.audit_audio_main_six_preparation import verify_fill
from hardware.fabrication.audit_audio_main_supplies import without_fill
from hardware.fabrication.audit_audio_main_supply_completion import verify_native
from hardware.fabrication.audit_candidate import sha
from hardware.fabrication.route_nf_surface import shape

PD_NETS = {"/ADC/PD_L", "/ADC/PD_R", "/ADC/PD_GATED"}
LEGACY = ROOT / "staging/audio-main-controls-02/distribution-construction.json"


def read(name):
    return json.loads((OUT / name).read_text())


def verify_preparation(source, prepared, record, recipe):
    retired = set(recipe["retired_copper_uuids"])
    assert set(record["retired_copper_uuids"]) == retired and len(retired) == 15
    removed = [n for tag in ("segment", "via") for n in children(source, tag) if str(first(n, "uuid")[1]) in retired]
    assert removed == record["retired_nodes"] and Counter(n[0] for n in removed) == {"segment": 14, "via": 1}
    names = {str(n[1]): str(n[2]) for n in children(source, "net")}
    assert Counter(names[str(first(n, "net")[1])] for n in removed) == {"ADC_BIAS_WINDOW_OK": 12, "/ADC/PD_R": 3}
    assert all(float(first(n, "width")[1]) == .2 for n in removed if n[0] == "segment")
    expected = copy.deepcopy([n for n in source if n not in removed])
    assert set(record["declared_footprint_replacements"]) == {"R115", "R131"}
    assert recipe["placements"]["R115"]["pose"] == [38.5, 24, 180] and recipe["placements"]["R131"]["pose"] == [45.2, 39.8, 270]
    for ref, placement in recipe["placements"].items():
        old = footprints(expected)[ref]
        node = read_sexpr((OUT / "templates" / placement["template"]).read_text())
        assert first(old, "uuid") == first(node, "uuid") and old[1] == node[1]
        assert first(old, "layer")[1] == "B.Cu" and first(node, "layer")[1] == "F.Cu"
        props = {str(p[1]): str(p[2]) for p in children(node, "property")}
        assert all(props[str(p[1])] == str(p[2]) for p in children(old, "property"))
        for pad in children(node, "pad"):
            net = first(pad, "net")
            net[2:] = [names[str(net[1])]]
        first(node, "at")[1:] = placement["pose"]
        assert record["declared_footprint_replacements"][ref] == dict(before=old, after=node)
        expected[expected.index(old)] = node
    assert ReceivingSpace(expected, {"R115", "R131"}).accepts({r: v["pose"] for r, v in recipe["placements"].items()})
    assert without_fill(prepared) == without_fill(read_sexpr(sexpr(expected))), "Undeclared source geometry changed"


def verify_routes(parent, board, record, captured, recipe):
    assert captured["native_uncapped_opens"] == 167 and captured["layer_count"] == 6
    assert record["trace_width_mm"] == record["clearance_mm"] == .2 and record["planning_margin_mm"] == .01
    assert record["maximum_new_vias_per_PD_connection"] == 2 and record["maximum_PD_surface_neck_mm"] == 3.5
    assert record["maximum_legacy_control_path_vias"] == 4 and record["shared_previous_F_segments"] == 1
    assert record["new_PD_joins"] == 3 and record["restored_existing_joins"] == 2
    assert len(record["routes"]) == 5
    objects = {o["uuid"]: o for o in captured["objects"]}
    pads = {(o["ref"], o["pin"]): o for o in objects.values() if o["kind"] == "PAD" and o["pin"]}
    membership = {uid: key for key, ids in captured["groups"].items() for uid in ids}
    groups = {frozenset([key]) for key in captured["groups"]}
    common = QuietTraceScreen(captured, NETS)
    expected, additions, reused, full_control = copy.deepcopy(parent), [], [], None
    purposes = ["amplifier_PD_entry", "amplifier_PD_entry", "restore_right_PD_divider", "complete_left_PD_divider", "restore_ADC_bias_control"]
    for index, row in enumerate(record["routes"]):
        assert row["purpose"] == purposes[index]
        net, runs, vias, contacts = row["net"], row["runs"], row["new_vias_mm"], row["native_contacts"]
        assert len(contacts) == 2
        sides = [next(g for g in groups if membership[c["uuid"]] in g) for c in contacts]
        assert sides[0] != sides[1] and row["source_groups"] == [sorted(g) for g in sides], "False source island merge"
        for contact in contacts:
            obj = objects[contact["uuid"]]
            assert obj["net"] == net and obj["layers"].get(contact["face"])
            assert any(point(p) == point(contact["point_mm"]) for p in [obj["position_mm"]]+([obj["end_mm"]] if "end_mm" in obj else []))
            if "ref" in contact:
                assert (obj["ref"], obj["pin"]) == (contact["ref"], contact["pin"])
        assert row["terminal_points_mm"] == [c["point_mm"] for c in contacts]
        assert point(runs[0][1][0]) == point(contacts[0]["point_mm"]) and point(runs[-1][1][-1]) == point(contacts[1]["point_mm"])
        screen = QuietTraceScreen(captured, NETS)
        allowed_reuse = []
        if index in (0, 1):
            chip, resistor, net_expected = (("U101", "R115", "/ADC/PD_L") if index == 0 else ("U102", "R131", "/ADC/PD_R"))
            assert net == net_expected and row["budget_endpoints"] == [[chip, "7"], [resistor, "1"]]
            assert contacts[0]["uuid"] == pads[chip, "7"]["uuid"] and contacts[1]["uuid"] == pads[resistor, "1"]["uuid"]
            assert runs == [["F.Cu", recipe["FDA_entry_paths"][net]]] and vias == [] and row["maximum_new_vias"] == 0
            limit = min(40, 2*math.dist(*row["terminal_points_mm"])+6)
            screen = PDEntryScreen(captured, net, runs[0][1])
        elif index == 2:
            assert net == "/ADC/PD_R" and row["budget_endpoints"] == [["R130", "2"], ["R131", "1"]]
            assert objects[contacts[0]["uuid"]]["kind"] == "PCB_VIA" and contacts[0]["point_mm"] == [50.48, 36.8375]
            assert contacts[1]["uuid"] == pads["R131", "1"]["uuid"]
            neck = [pads["R130", "2"]["position_mm"], [50.48, 36.8375]]
            assert row["retained_surface_neck"] == neck
            old_neck = objects["0243d3b1-6e73-58ae-ba1d-cd3abf4570d8"]
            assert [old_neck["position_mm"], old_neck["end_mm"]] == neck and old_neck["width_mm"] == .2
            full_limit = min(40, 2*math.dist(pads["R130", "2"]["position_mm"], pads["R131", "1"]["position_mm"])+6)
            assert row["complete_endpoint_maximum_mm"] == full_limit
            limit = full_limit-LineString(neck).length
            assert len(runs) == 2 and [r[0] for r in runs] == ["In3.Cu", "F.Cu"] and len(vias) == row["maximum_new_vias"] == 1
            assert point(runs[0][1][-1]) == point(runs[1][1][0]) == point(vias[0]) and LineString(runs[1][1]).length <= 3.5
        elif index == 3:
            assert net == "/ADC/PD_L" and row["budget_endpoints"] == [["R114", "2"], ["R115", "1"]]
            assert [c["uuid"] for c in contacts] == [pads["R114", "2"]["uuid"], pads["R115", "1"]["uuid"]]
            limit = min(40, 2*math.dist(*row["terminal_points_mm"])+6)
            assert len(runs) == 3 and [r[0] for r in runs] == ["F.Cu", "In3.Cu", "F.Cu"] and len(vias) == row["maximum_new_vias"] == 2
            assert LineString(runs[0][1]).length <= 3.5 and LineString(runs[-1][1]).length <= 3.5
            assert list(map(point, vias)) == [point(runs[0][1][-1]), point(runs[1][1][-1])]
            assert point(runs[1][1][0]) == point(vias[0]) and point(runs[2][1][0]) == point(vias[1])
            shared = recipe["FDA_entry_paths"][net][-2:]
            assert row["reused_previous_F_segment_mm"] == shared and runs[-1][1][-2:] == shared
            assert shared == record["routes"][0]["runs"][0][1][-2:]
            allowed_reuse = [LineString(shared).buffer(.101)]
            reused.append(shared)
        else:
            assert net == "ADC_BIAS_WINDOW_OK" and vias == [] and row["maximum_new_vias"] == 0
            assert [c["point_mm"] for c in contacts] == [[51.7, 35.4], [50.6, 45.4]] and all(objects[c["uuid"]]["kind"] == "PCB_VIA" for c in contacts)
            assert len(runs) == 1 and runs[0][0] == "In3.Cu"
            legacy = next(r for r in json.loads(LEGACY.read_text())["routes"] if r["net"] == net and r["runs"][0][1][0] == [61.95, 44.6375])
            index_of_branch = legacy["runs"][2][1].index([50.3, 43.9])
            kept = legacy["runs"][:2]+[["F.Cu", legacy["runs"][2][1][:index_of_branch+1]+[[50.6, 45.4]]], legacy["runs"][3]]
            assert row["retained_legacy_runs"] == kept and row["complete_legacy_maximum_mm"] == legacy["maximum_planar_length_mm"]
            assert row["complete_legacy_via_limit"] == 4 and row["retained_legacy_vias_mm"] == legacy["new_vias_mm"]+[[50.6, 45.4]]
            full = kept[:3]+[["In3.Cu", list(reversed(runs[0][1]))]]+[kept[-1]]
            transitions = []
            for left, right in zip(full, full[1:]):
                assert point(left[1][-1]) == point(right[1][0])
                transitions.append(point(left[1][-1]))
            assert len(transitions) == len(set(transitions)) == 4
            assert all(any(o["kind"] == "PCB_VIA" and o["net"] == net and point(o["position_mm"]) == p for o in objects.values()) for p in transitions)
            limit = legacy["maximum_planar_length_mm"]-sum(LineString(ps).length for _, ps in kept)
            full_length = sum(LineString(ps).length for _, ps in full)
            assert full_length <= legacy["maximum_planar_length_mm"]
            full_control = dict(runs=full, length_mm=full_length, maximum_mm=legacy["maximum_planar_length_mm"], physical_transition_vias=len(transitions))
        length = sum(LineString(ps).length for _, ps in runs)
        assert abs(length-row["planar_length_mm"]) < 1e-7 and abs(limit-row["maximum_planar_length_mm"]) < 1e-7 and length <= limit
        screen.added, screen.new_vias = list(common.added), list(common.new_vias)
        for i, xy in enumerate(vias):
            assert screen.via_legal(net, xy) and all(math.dist(xy, q) > .86 for _, q in screen.vias+screen.new_vias)
            assert all(math.dist(xy, q) > .86 for q in vias[:i])
        for face, points in runs:
            assert screen.legal(net, face, points), "New route violates physical or owner-entry policy"
            allowed = unary_union([shape(objects[c["uuid"]]["layers"].get(face, [])).buffer(.101) for c in contacts]+allowed_reuse)
            geometry = [shape(o["layers"][face]) for o in objects.values() if o["net"] == net and o["layers"].get(face)]
            geometry += [g for n, f, g in common.added if n == net and f == face]
            assert all(LineString(points).intersection(g.buffer(.1)).difference(allowed).is_empty for g in geometry), "Unexpected same-net contact or loop"
        before = len(additions)
        for face, points in runs:
            add_geometry(expected, additions, net, face, points, .2, row["purpose"])
        for xy in vias:
            add_via(expected, additions, net, xy, row["purpose"])
        assert row["new_copper_uuids"] == [r["uuid"] for r in additions[before:]]
        common.added.extend((net, face, LineString(points)) for face, points in runs)
        common.new_vias.extend((net, xy) for xy in vias)
        groups.difference_update(sides)
        groups.add(sides[0] | sides[1])
    assert len(reused) == 1 and full_control is not None
    assert without_fill(board) == without_fill(read_sexpr(sexpr(expected))), "Existing or new geometry differs from the declared construction"
    assert record["added_segments"] == [r for r in additions if r["kind"] == "segment"]
    assert record["added_vias"] == [r for r in additions if r["kind"] == "via"] and len(record["added_vias"]) == 3
    smd = [shape(ps) for o in captured["objects"] if o["kind"] == "PAD" and not any(o["drill_mm"])
           for face, ps in o["layers"].items() if face in ("F.Cu", "B.Cu") and ps]
    minimum = min(Point(row["xy_mm"]).distance(g)-.15 for row in record["added_vias"] for g in smd)
    assert minimum >= .16-1e-7
    return full_control, round(minimum, 9)


def check():
    names = ["preparation-record.json", "prepared-refill.json", "prepared-native-inputs.json", "prepared-geometry-review.json", "distribution-construction.json",
             "native-refill.json", "terminal-connectivity-review.json", "additional-terminal-review.json", "current-native-pads.json", "final-native-inputs.json"]
    reports = {name: read(name) for name in names}
    for report in reports.values():
        verify_hashes(report["source_sha256"])
        assert not report["fabrication_released"]
    recipe = json.loads(PLAN.read_text())
    verify_hashes(recipe["source_sha256"])
    template_report = json.loads((OUT / "templates/templates.json").read_text())
    verify_hashes(template_report["source_sha256"])
    assert all(sha(OUT / "templates" / t["file"]) == t["sha256"] for t in template_report["templates"])
    parent = read_sexpr((SOURCE / "audio_core.kicad_pcb").read_text())
    prepared = read_sexpr((OUT / "prepared-input.kicad_pcb").read_text())
    assert sha(OUT / "prepared-input.kicad_pcb") == reports["preparation-record.json"]["authored_PCB_sha256"]
    verify_preparation(parent, prepared, reports["preparation-record.json"], recipe)
    verify_fill(OUT, prepared, "prepared-refilled.kicad_pcb", "prepared-native-export.kicad_pcb", reports["prepared-refill.json"])
    record, captured = reports["distribution-construction.json"], reports["prepared-native-inputs.json"]
    assert sha(OUT / "distribution-input.kicad_pcb") == record["authored_PCB_sha256"]
    ground = verify_fill(OUT, read_sexpr((OUT / "distribution-input.kicad_pcb").read_text()), "audio_core.kicad_pcb", "native-refill-export.kicad_pcb", reports["native-refill.json"])
    control, minimum = verify_routes(read_sexpr((OUT / "prepared-refilled.kicad_pcb").read_text()), read_sexpr((OUT / "audio_core.kicad_pcb").read_text()), record, captured, recipe)
    native = verify_native(OUT)
    witness, extra, final = reports["terminal-connectivity-review.json"], reports["additional-terminal-review.json"], reports["final-native-inputs.json"]
    source_witness = json.loads((SOURCE / "terminal-connectivity-review.json").read_text())
    for key in ("retained_local_pairs", "retained_control_pairs", "ground_pads", "supply_pads"):
        assert witness[key] == source_witness[key]
    objects = {o["uuid"]: o for o in captured["objects"]}
    expected = []
    for row in record["routes"]:
        pads = [objects[uid] for side in row["source_groups"] for key in side for uid in captured["groups"][key] if objects[uid]["kind"] == "PAD" and objects[uid]["pin"]]
        expected.append(dict(net=row["net"], source_groups=row["source_groups"], reference_terminal=[pads[0]["ref"], pads[0]["pin"]],
                             contacts=[dict(ref=p["ref"], pin=p["pin"], native_connected=True) for p in pads]))
    assert witness["new_route_witnesses"] == expected
    inherited = json.loads((SOURCE / "additional-terminal-review.json").read_text())
    assert extra["retained_global_control_witnesses"] == inherited["retained_global_control_witnesses"]+source_witness["new_route_witnesses"]
    assert len(extra["retained_global_control_witnesses"]) == 108 and extra["retained_private_timing_connections"] == inherited["retained_private_timing_connections"]
    def pads(rows, exclude=()):
        return {(p["ref"], p["pin"], point(p["position_mm"])): {k: p[k] for k in ("net", "layers", "drill_mm", "npth")} for p in rows if p["kind"] == "PAD" and p["ref"] not in exclude}
    assert pads(captured["objects"]) == pads(final["objects"]) == pads(reports["current-native-pads.json"]["objects"])
    assert len(pads(final["objects"])) == 930
    source_capture = json.loads((SOURCE / "final-native-inputs.json").read_text())
    unchanged = pads(source_capture["objects"], {"R115", "R131"})
    assert unchanged == pads(final["objects"], {"R115", "R131"}) and len(unchanged) == 926
    moved = {(p["ref"], p["pin"]): p for p in final["objects"] if p["kind"] == "PAD" and p["ref"] in ("R115", "R131")}
    for ref, placement in recipe["placements"].items():
        template = next(t for t in template_report["templates"] if t["file"] == placement["template"])
        x, y, _ = placement["pose"]
        for p in template["pads"]:
            actual = moved[ref, p["pin"]]
            assert actual["net"] == p["net"] and actual["drill_mm"] == [0, 0] and set(actual["layers"]) == {"F.Cu"}
            wanted = translate(shape(p["layers"]["F.Cu"]), xoff=x, yoff=y)
            assert wanted.hausdorff_distance(shape(actual["layers"]["F.Cu"])) < .000002
    final_objects = {o["uuid"]: o for o in final["objects"]}
    island_counts = {}
    for net in PD_NETS | NETS | {"ADC_BIAS_WINDOW_OK"}:
        keys = [k for k, ids in final["groups"].items() if any(final_objects[i]["kind"] == "PAD" and final_objects[i]["net"] == net for i in ids)]
        assert len(keys) == 1, (net, keys)
        island_counts[net] = 1
    assert native["uncapped_open_connections"] == witness["uncapped_open_connections"] == extra["uncapped_open_connections"] == final["native_uncapped_opens"] == record["expected_native_opens"] == 162
    noise = measure(final, NETS, NOISY | PD_NETS)
    assert noise["violations"] == []
    for p in SOURCE.rglob("*"):
        rel = p.relative_to(SOURCE)
        if p.is_file() and (rel.parts[0] == "libraries" or p.parent == SOURCE and (p.suffix in (".kicad_sch", ".kicad_pro", ".kicad_sym", ".kicad_dru") or p.name in ("fp-lib-table", "sym-lib-table"))):
            assert sha(p) == sha(OUT / rel)
    return dict(source_sha256=relative_hashes([Path(__file__), PLAN, ROUTES, LEGACY, ROOT / "audio_main_pd_entry_screen.py", ROOT / "audio_main_noise_audit.py",
                OUT / "templates/templates.json", OUT / "plan.json", SOURCE / "audio_core.kicad_pcb", SOURCE / "final-native-inputs.json", SOURCE / "PD-routing-review.json",
                SOURCE / "terminal-connectivity-review.json", SOURCE / "additional-terminal-review.json", OUT / "placement-native-review.json"]+[OUT / n for n in names]),
                uncapped_open_connections=162, new_PD_connections=3, restored_existing_joins=2, retired_segments=14, retired_vias=1,
                added_tracks=len(record["added_segments"]), added_vias=3, shared_F_segment_count=1, unchanged_native_pads=926, moved_native_pads=4,
                moved_references=["R115", "R131"], moved_pad_shapes_match_native_templates=True, native_islands_by_net=island_counts,
                native_geometry_findings=0, native_ERC_findings=0, missing_codec_parity_findings=1, remaining_PD_control_gaps=0,
                control_legacy_path=control, inherited_witness_rows=108, ground_plane_area_mm2=ground, minimum_new_drill_edge_to_SMD_mm=minimum,
                exhaustive_noise_geometry=noise, electrical_PD_response_and_noise_qualified=False, fabrication_released=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    result = check()
    if args.write:
        (OUT / "PD-pin-repack-review.json").write_text(json.dumps(result, indent=2)+"\n")
    print(json.dumps(result, indent=2))
