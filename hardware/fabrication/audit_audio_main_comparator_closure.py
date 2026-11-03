"""Check the comparator closure against native geometry and retained circuitry."""

import argparse
import copy
import json
import math
import re
from collections import Counter
from pathlib import Path

from shapely.geometry import LineString, Point
from shapely.ops import unary_union

from hardware.electronics.common.sexpr import children, first, read_sexpr, sexpr
from hardware.fabrication.audio_main_bypass_repack import add_geometry, add_via
from hardware.fabrication.audio_main_comparator_closure import LEGACY, OUT, PLAN, ROOT, SOURCE
from hardware.fabrication.audio_main_layer_screen import LayeredSignalScreen
from hardware.fabrication.audio_main_local_repack import ReceivingSpace, set_poses
from hardware.fabrication.audio_main_local_routes import relative_hashes, verify_hashes
from hardware.fabrication.audio_main_noise_audit import measure
from hardware.fabrication.audio_main_quiet_screen import QuietTraceScreen
from hardware.fabrication.audit_audio_main_named_routes import NETS, NOISY, point
from hardware.fabrication.audit_audio_main_six_preparation import verify_fill
from hardware.fabrication.audit_audio_main_supplies import without_fill
from hardware.fabrication.audit_audio_main_supply_completion import verify_native
from hardware.fabrication.audit_candidate import sha
from hardware.fabrication.route_nf_surface import shape


def read(name):
    return json.loads((OUT / name).read_text())


def verify_preparation(source, prepared, record, recipe):
    retired = set(recipe["retired_uuids"])
    assert retired == set(record["retired_copper_uuids"]) and len(retired) == 9
    removed = [n for tag in ("segment", "via") for n in children(source, tag) if str(first(n, "uuid")[1]) in retired]
    assert removed == record["retired_nodes"] and len(removed) == 9
    assert Counter(n[0] for n in removed) == {"segment": 8, "via": 1}
    expected = copy.deepcopy([n for n in source if n not in removed])
    assert record["declared_pose_changes"] == {"R138": {"before": [28, 48, 0], "after": [28, 47.7, 0]}}
    assert recipe["before_pose"] == [28, 48, 0] and recipe["after_pose"] == [28, 47.7, 0]
    assert ReceivingSpace(source, {"R138"}).accepts({"R138": (28, 47.7, 0)})
    set_poses(expected, {"R138": (28, 47.7, 0)})
    relocation = recipe["via_relocation"]
    assert relocation["before_mm"] == [28.5, 46.8] and relocation["after_mm"] == [28.15, 46.6]
    edits = [(relocation["uuid"], "at", [28.15, 46.6]),
             (relocation["F_spur_uuid"], "start", [28.15, 46.6]),
             (relocation["B_spur_uuid"], "start", [28, 46.85])]
    actual_edits = []
    for uid, field, xy in edits:
        node = next(n for n in expected if isinstance(n, list) and n and n[0] in ("segment", "via") and str(first(n, "uuid")[1]) == uid)
        before = copy.deepcopy(node)
        first(node, field)[1:3] = xy
        actual_edits.append(dict(uuid=uid, before=before, after=copy.deepcopy(node)))
    assert actual_edits == record["declared_copper_edits"]
    additions = []
    add_geometry(expected, additions, "/ADC/BIAS_SHIFT_R", "B.Cu", [[28.15, 46.6], [28, 46.85]], .2, "renew_relocated_via_spur")
    assert additions == record["preparation_added_segments"]
    assert without_fill(prepared) == without_fill(read_sexpr(sexpr(expected))), "Undeclared source geometry changed"


def verify_routes(parent, board, record, captured, final):
    expected, additions = copy.deepcopy(parent), []
    objects = {o["uuid"]: o for o in captured["objects"]}
    member = {uid: k for k, ids in captured["groups"].items() for uid in ids}
    final_pads = {(o["ref"], o["pin"]): o for o in final["objects"] if o["kind"] == "PAD" and o["pin"]}
    legacy = json.loads(LEGACY.read_text())["routes"]
    quiet, power = QuietTraceScreen(captured, NOISY), LayeredSignalScreen(captured)
    assert len(record["routes"]) == 5 and record["restored_existing_connections"] == 4 and record["new_comparator_connections"] == 1
    assert record["trace_width_mm"] == record["clearance_mm"] == .2
    assert record["planning_margin_mm"] == .01 and record["noisy_net_centreline_to_copper_mm"] == .71
    for index, row in enumerate(record["routes"]):
        net, runs = row["net"], row["runs"]
        assert row["repaired_existing_join"] == (index != 2)
        contacts = row["native_contacts"]
        assert len(contacts) == 2 and row["source_groups"] == [[member[c["uuid"]]] for c in contacts]
        assert row["source_groups"][0] != row["source_groups"][1], "False source island separation"
        for c in contacts:
            o = objects[c["uuid"]]
            assert o["net"] == net and o["layers"].get(c["face"])
            assert any(point(c["point_mm"]) == point(p) for p in [o["position_mm"]]+([o["end_mm"]] if "end_mm" in o else []))
        assert row["terminal_points_mm"] == [c["point_mm"] for c in contacts]
        assert point(runs[0][1][0]) == point(contacts[0]["point_mm"]) and point(runs[-1][1][-1]) == point(contacts[1]["point_mm"])
        if index == 0:
            assert net == "V5_REG" and runs == [["B.Cu", [[27.0875, 47.7], [27.0875, 49.02]]]]
            limit = 3.5
        elif index == 1:
            assert net == "/ADC/THRESH_UPPER" and runs == [["B.Cu", [[28.9125, 47.7], [31, 48.825]]]]
            limit = min(8, 1.6*math.dist(*row["terminal_points_mm"])+.5)
        elif index == 2:
            assert net == "/ADC/THRESH_LOWER" and runs == [["F.Cu", [[30.475, 49.27], [29.1, 49]]], ["In3.Cu", [[29.1, 49], [28, 51.9]]]]
            assert row["new_vias_mm"] == [[29.1, 49]] and LineString(runs[0][1]).length <= 3.5
            limit = min(40, 2*math.dist(*row["terminal_points_mm"])+6)
        else:
            assert net == ("/ADC/BIAS_SHIFT_R" if index == 3 else "/ADC/BIAS_SHIFT_L") and len(runs) == 1 and runs[0][0] == "In3.Cu"
            original = next(r for r in legacy if r["net"] == net and r["endpoints"] == row["legacy_endpoints"])
            full = row["complete_legacy_runs"]
            length = sum(LineString(ps).length for _, ps in full)
            assert abs(length-row["complete_legacy_length_mm"]) < 1e-7
            assert row["complete_legacy_maximum_mm"] == original["maximum_planar_length_mm"] and length <= original["maximum_planar_length_mm"]
            assert point(full[0][1][0]) == point(final_pads[tuple(original["endpoints"][0])]["position_mm"])
            assert point(full[-1][1][-1]) == point(final_pads[tuple(original["endpoints"][1])]["position_mm"])
            for i, (face, ps) in enumerate(full):
                copper = unary_union([shape(o["layers"][face]) for o in final["objects"] if o["net"] == net and o["layers"].get(face)])
                assert LineString(ps).difference(copper.buffer(.000002)).is_empty, "Legacy path leaves actual native copper"
                if i:
                    xy = ps[0]
                    assert point(xy) == point(full[i-1][1][-1])
                    assert any(o["kind"] == "PCB_VIA" and o["net"] == net and point(o["position_mm"]) == point(xy) for o in final["objects"])
                if face in ("F.Cu", "B.Cu"):
                    assert LineString(ps).length <= 3.5
            limit = original["maximum_planar_length_mm"]-(length-sum(LineString(ps).length for _, ps in runs))
            disks = Point(runs[0][1][0]).buffer(.65).union(Point(runs[0][1][-1]).buffer(.65))
            for o in objects.values():
                if o["net"] == net and o["layers"].get("In3.Cu"):
                    overlap = LineString(runs[0][1]).intersection(shape(o["layers"]["In3.Cu"]).buffer(.1))
                    assert overlap.difference(disks).is_empty, "Nonterminal same-net contact creates redundant copper"
        length = sum(LineString(ps).length for _, ps in runs)
        assert abs(length-row["planar_length_mm"]) < 1e-7 and abs(limit-row["maximum_planar_length_mm"]) < 1e-7 and length <= limit
        assert row["new_vias_mm"] == ([[29.1, 49]] if index == 2 else [])
        screen = power if net == "V5_REG" else quiet
        for xy in row["new_vias_mm"]:
            assert screen.via_legal(net, xy)
            add_via(expected, additions, net, xy, row["purpose"])
        for face, ps in runs:
            assert screen.legal(net, face, ps), "Route violates clearance or reference policy"
            add_geometry(expected, additions, net, face, ps, .2, row["purpose"])
        for s in (quiet, power):
            s.added.extend((net, face, LineString(ps)) for face, ps in runs)
            s.new_vias.extend((net, xy) for xy in row["new_vias_mm"])
    # Native refill preserves authored object order. The audit constructs via
    # objects before their runs, whereas the author writes runs first.
    def body(nodes):
        return [n for n in without_fill(nodes) if not isinstance(n, list) or not n or n[0] not in ("segment", "via")]
    def copper(nodes):
        return {str(first(n, "uuid")[1]): n for tag in ("segment", "via") for n in children(nodes, tag)}
    expected = read_sexpr(sexpr(expected))
    assert body(board) == body(expected) and copper(board) == copper(expected), "Added or retained geometry changed"
    for kind, key in (("segment", "added_segments"), ("via", "added_vias")):
        assert sorted((r for r in additions if r["kind"] == kind), key=lambda r: r["uuid"]) == sorted(record[key], key=lambda r: r["uuid"])


def check():
    names = ["preparation-record.json", "prepared-refill.json", "prepared-geometry-review.json", "prepared-native-inputs.json",
             "distribution-construction.json", "native-refill.json", "terminal-connectivity-review.json", "additional-terminal-review.json",
             "current-native-pads.json", "final-native-inputs.json"]
    reports = {n: read(n) for n in names}
    for r in reports.values():
        verify_hashes(r["source_sha256"])
        assert not r["fabrication_released"]
    source = read_sexpr((SOURCE / "audio_core.kicad_pcb").read_text())
    prepared = read_sexpr((OUT / "prepared-input.kicad_pcb").read_text())
    assert sha(OUT / "prepared-input.kicad_pcb") == reports["preparation-record.json"]["authored_PCB_sha256"]
    verify_preparation(source, prepared, reports["preparation-record.json"], json.loads(PLAN.read_text()))
    verify_fill(OUT, prepared, "prepared-refilled.kicad_pcb", "prepared-native-export.kicad_pcb", reports["prepared-refill.json"])
    record, captured, final = reports["distribution-construction.json"], reports["prepared-native-inputs.json"], reports["final-native-inputs.json"]
    assert captured["native_uncapped_opens"] == 176 and captured["layer_count"] == final["layer_count"] == 6
    assert sha(OUT / "distribution-input.kicad_pcb") == record["authored_PCB_sha256"]
    ground = verify_fill(OUT, read_sexpr((OUT / "distribution-input.kicad_pcb").read_text()), "audio_core.kicad_pcb", "native-refill-export.kicad_pcb", reports["native-refill.json"])
    board = read_sexpr((OUT / "audio_core.kicad_pcb").read_text())
    verify_routes(read_sexpr((OUT / "prepared-refilled.kicad_pcb").read_text()), board, record, captured, final)
    native = verify_native(OUT)
    source_witness = json.loads((SOURCE / "terminal-connectivity-review.json").read_text())
    witness, extra = reports["terminal-connectivity-review.json"], reports["additional-terminal-review.json"]
    for key in ("retained_local_pairs", "retained_control_pairs", "ground_pads", "supply_pads"):
        assert witness[key] == source_witness[key]
    objects = {o["uuid"]: o for o in captured["objects"]}
    expected = []
    for row in record["routes"]:
        pads = [objects[uid] for side in row["source_groups"] for k in side for uid in captured["groups"][k] if objects[uid]["kind"] == "PAD" and objects[uid]["pin"]]
        expected.append(dict(net=row["net"], source_groups=row["source_groups"], reference_terminal=[pads[0]["ref"], pads[0]["pin"]],
                             contacts=[dict(ref=p["ref"], pin=p["pin"], native_connected=True) for p in pads]))
    assert witness["new_route_witnesses"] == expected
    inherited = json.loads((SOURCE / "additional-terminal-review.json").read_text())
    assert extra["retained_global_control_witnesses"] == inherited["retained_global_control_witnesses"]+source_witness["new_route_witnesses"]
    assert len(extra["retained_global_control_witnesses"]) == 97 and extra["retained_private_timing_connections"] == inherited["retained_private_timing_connections"]
    def pad_map(rows):
        return {(p["ref"], p["pin"], point(p["position_mm"])): {k: p[k] for k in ("net", "layers", "drill_mm", "npth")} for p in rows if p["kind"] == "PAD"}
    assert pad_map(captured["objects"]) == pad_map(final["objects"]) == pad_map(reports["current-native-pads.json"]["objects"])
    assert len(pad_map(final["objects"])) == 930
    counts = Counter(re.search(r"\[([^]]+)\]", row["items"][0]["description"]).group(1) for row in json.loads((OUT / "drc.json").read_text())["unconnected_items"])
    assert all(counts[n] == 0 for n in NETS), "Comparator inputs remain disconnected"
    # Every terminal of each comparator input net must share one native island.
    final_objects = {o["uuid"]: o for o in final["objects"]}
    comparator_islands = {}
    for net in NETS:
        groups = [k for k, ids in final["groups"].items() if any(final_objects[i]["kind"] == "PAD" and final_objects[i]["net"] == net for i in ids)]
        assert len(groups) == 1, (net, groups)
        comparator_islands[net] = groups[0]
    noise = measure(final, NETS, NOISY)
    assert noise["violations"] == []
    smd = [shape(polygons) for o in final["objects"] if o["kind"] == "PAD" and not any(o["drill_mm"])
           for face, polygons in o["layers"].items() if face in ("F.Cu", "B.Cu") and polygons]
    drill_gaps = {label: min(Point(xy).distance(g)-.15 for g in smd)
                  for label, xy in (("fresh_threshold", [29.1, 49]), ("relocated_right_bias", [28.15, 46.6]))}
    assert min(drill_gaps.values()) >= .16-1e-7
    assert native["uncapped_open_connections"] == witness["uncapped_open_connections"] == extra["uncapped_open_connections"] == final["native_uncapped_opens"] == 171
    # All schematic, rule, library, and project inputs remain identical.
    for p in SOURCE.rglob("*"):
        rel = p.relative_to(SOURCE)
        if p.is_file() and (rel.parts[0] == "libraries" or p.parent == SOURCE and (p.suffix in (".kicad_sch", ".kicad_sym", ".kicad_dru", ".kicad_pro") or p.name in ("fp-lib-table", "sym-lib-table"))):
            assert sha(p) == sha(OUT / rel)
    return dict(source_sha256=relative_hashes([Path(__file__), PLAN, LEGACY, ROOT / "audio_main_noise_audit.py", ROOT / "audio_main_quiet_screen.py",
                ROOT / "audit_audio_main_named_routes.py", ROOT / "audit_audio_main_six_preparation.py", ROOT / "audit_audio_main_supply_completion.py",
                SOURCE / "clearance-repair-review.json", SOURCE / "audio_core.kicad_pcb", SOURCE / "terminal-connectivity-review.json",
                SOURCE / "additional-terminal-review.json", OUT / "placement-native-review.json"]+[OUT / n for n in names]),
                uncapped_open_connections=171, native_geometry_findings=0, native_ERC_findings=0, missing_codec_parity_findings=1,
                comparator_input_native_islands=comparator_islands, remaining_comparator_input_gaps={},
                declared_R138_move_mm=.3, retired_segments=8, retired_vias=1, relocated_vias=1, fresh_vias=1,
                retained_local_pairs=138, retained_control_pairs=17, retained_ground_pads=200, retained_rail_pads=161,
                inherited_witness_rows=97, private_timing_pairs=2, native_pad_count=930, ground_plane_area_mm2=ground,
                minimum_drill_edge_to_SMD_mm=drill_gaps,
                exhaustive_noise_geometry=noise, electrical_noise_and_installed_fault_performance_qualified=False, fabrication_released=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    result = check()
    if args.write:
        (OUT / "comparator-closure-review.json").write_text(json.dumps(result, indent=2)+"\n")
    print(json.dumps(result, indent=2))
