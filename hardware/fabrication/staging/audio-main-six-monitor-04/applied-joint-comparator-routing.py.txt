"""Close the final comparator input with one resistor move and joint bias repairs."""

import argparse
import copy
import json
import math
import shutil
import sys
from pathlib import Path

from hardware.electronics.common.sexpr import children, first, read_sexpr, sexpr
from hardware.fabrication.audio_main_bypass_repack import add_geometry, add_via
from hardware.fabrication.audio_main_local_routes import relative_hashes, verify_hashes
from hardware.fabrication.audit_candidate import sha

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "staging/audio-main-six-monitor-03"
OUT = ROOT / "staging/audio-main-six-monitor-04"
PLAN = ROOT / "audio_main_comparator_closure_plan.json"
LEGACY = ROOT / "staging/audio-main-six-monitor-01/distribution-construction.json"


def snapshot(label):
    p = OUT / ("applied-"+label+".py.txt")
    assert not p.exists()
    shutil.copyfile(Path(__file__), p)
    return p


def prepare():
    from hardware.electronics.output_stage.check_placement import courtyard
    from hardware.fabrication.audio_main_local_repack import ReceivingSpace, footprints, poses, set_poses

    assert not OUT.exists()
    recipe = json.loads(PLAN.read_text())
    verify_hashes(recipe["source_sha256"])
    board = read_sexpr((SOURCE / "audio_core.kicad_pcb").read_text())
    before = poses(board)["R138"]
    after = tuple(recipe["after_pose"])
    assert list(before) == recipe["before_pose"] == [28, 48, 0] and after == (28, 47.7, 0)
    assert ReceivingSpace(board, {"R138"}).accepts({"R138": after})
    retired = set(recipe["retired_uuids"])
    removed = [n for tag in ("segment", "via") for n in children(board, tag) if str(first(n, "uuid")[1]) in retired]
    names = {str(n[1]): str(n[2]) for n in children(board, "net")}
    assert len(removed) == len(retired) == 9
    assert sorted(names[str(first(n, "net")[1])] for n in removed) == sorted(["V5_REG", "/ADC/THRESH_UPPER"]+["/ADC/BIAS_SHIFT_L"]*6+["/ADC/BIAS_SHIFT_R"])
    assert all(float(first(n, "width")[1]) == .2 for n in removed if n[0] == "segment")
    assert [str(first(n, "uuid")[1]) for n in removed if n[0] == "via"] == [recipe["pruned_left_entry_via_uuid"]]
    board = [n for n in board if n not in removed]
    set_poses(board, {"R138": after})
    relocation = recipe["via_relocation"]
    edits = []
    for ident, field, value in [(relocation["uuid"], "at", relocation["after_mm"]),
                               (relocation["F_spur_uuid"], "start", relocation["after_mm"]),
                               (relocation["B_spur_uuid"], "start", relocation["B_elbow_mm"])]:
        node = next(n for n in board if isinstance(n, list) and n and n[0] in ("segment", "via") and str(first(n, "uuid")[1]) == ident)
        assert names[str(first(node, "net")[1])] == "/ADC/BIAS_SHIFT_R"
        old = copy.deepcopy(node)
        first(node, field)[1:3] = value
        edits.append(dict(uuid=ident, before=old, after=copy.deepcopy(node)))
    additions = []
    add_geometry(board, additions, "/ADC/BIAS_SHIFT_R", "B.Cu", [relocation["after_mm"], relocation["B_elbow_mm"]], .2, "renew_relocated_via_spur")
    OUT.mkdir()
    applied = snapshot("comparator-preparation")
    for p in SOURCE.iterdir():
        if p.suffix in (".kicad_sch", ".kicad_pro", ".kicad_sym", ".kicad_dru") or p.name in ("fp-lib-table", "sym-lib-table"):
            shutil.copyfile(p, OUT / p.name)
    shutil.copytree(SOURCE / "libraries", OUT / "libraries")
    plan = json.loads((SOURCE / "plan.json").read_text())
    plan["poses"]["R138"] = [*after, "B"]
    plan["expanded_receiving_bounds_mm"]["R138"] = courtyard(footprints(board)["R138"], "B.CrtYd")
    assert not any(c["ref"] == "R138" or c["owner"] == "R138" for c in plan["local_cells"])
    plan["source_sha256"].update(relative_hashes([applied, SOURCE / "plan.json", PLAN]))
    (OUT / "plan.json").write_text(json.dumps(plan, indent=2)+"\n")
    dest = OUT / "prepared-input.kicad_pcb"
    dest.write_text(sexpr(board)+"\n")
    report = dict(source_sha256=relative_hashes([applied, PLAN, SOURCE / "audio_core.kicad_pcb", SOURCE / "plan.json",
        ROOT / "audio_main_local_repack.py", OUT / "plan.json"]), authored_PCB_sha256=sha(dest),
        declared_pose_changes={"R138": dict(before=list(before), after=list(after))},
        retired_copper_uuids=sorted(retired), retired_nodes=removed, declared_copper_edits=edits,
        preparation_added_segments=additions, receiving_screen_passed=True,
        expected_native_opens=176, all_undeclared_geometry_exact=True, fabrication_released=False)
    (OUT / "preparation-record.json").write_text(json.dumps(report, indent=2)+"\n")
    print("Moved R138 by 0.30 mm and renewed one bias via; eight segments and one redundant via retired; native checks pending")


def replace_span(runs, old_start, old_end, points):
    result = copy.deepcopy(runs)
    count = 0
    for _, path in result:
        starts = [i for i, p in enumerate(path) if math.dist(p, old_start) < 1e-6]
        ends = [i for i, p in enumerate(path) if math.dist(p, old_end) < 1e-6]
        if starts and ends:
            assert len(starts) == len(ends) == 1 and starts[0] < ends[0]
            path[starts[0]:ends[0]+1] = copy.deepcopy(points)
            count += 1
    assert count == 1
    return result


def build():
    from shapely.geometry import LineString, Point
    from shapely.strtree import STRtree

    from hardware.fabrication.audio_main_continuous_path import route
    from hardware.fabrication.audio_main_layer_screen import LayeredSignalScreen
    from hardware.fabrication.audio_main_quiet_screen import QuietTraceScreen
    from hardware.fabrication.audit_audio_main_named_routes import NOISY
    from hardware.fabrication.route_nf_surface import shape

    assert not (OUT / "distribution-input.kicad_pcb").exists()
    applied = snapshot("joint-comparator-routing")
    recipe = json.loads(PLAN.read_text())
    verify_hashes(recipe["source_sha256"])
    captured = json.loads((OUT / "prepared-native-inputs.json").read_text())
    verify_hashes(captured["source_sha256"])
    assert captured["native_uncapped_opens"] == 176 and captured["layer_count"] == 6
    objects = {o["uuid"]: o for o in captured["objects"]}
    pads = {(o["ref"], o["pin"]): o for o in objects.values() if o["kind"] == "PAD" and o["pin"]}
    member = {uid: k for k, ids in captured["groups"].items() for uid in ids}
    def contact(net, face, point, kind=None, refpin=None):
        if refpin:
            o = pads[refpin]
            assert o["net"] == net and o["layers"].get(face) and math.dist(o["position_mm"], point) < 1e-6
        else:
            choices = [o for o in objects.values() if o["net"] == net and o["layers"].get(face) and (not kind or o["kind"] == kind)
                       and any(math.dist(p, point) < 1e-6 for p in [o["position_mm"]]+([o["end_mm"]] if "end_mm" in o else []))]
            assert choices
            o = min(choices, key=lambda o: o["uuid"])
        return dict(uuid=o["uuid"], face=face, point_mm=point)
    routes = []
    def add(net, runs, endpoints, purpose, limit, vias=(), repair=True):
        length = sum(LineString(ps).length for _, ps in runs)
        assert length <= limit+1e-7
        groups = [[member[c["uuid"]]] for c in endpoints]
        assert groups[0] != groups[1], (purpose, "No native source island separation")
        routes.append(dict(net=net, runs=runs, native_contacts=endpoints, source_groups=groups,
            terminal_points_mm=[c["point_mm"] for c in endpoints], new_vias_mm=list(vias),
            planar_length_mm=length, maximum_planar_length_mm=limit, purpose=purpose, repaired_existing_join=repair))
    v5, upper = recipe["resistor_reentries"]
    add("V5_REG", [("B.Cu", v5[2])], [contact("V5_REG", "B.Cu", v5[2][0], refpin=("R138", "1")),
        contact("V5_REG", "B.Cu", v5[2][-1], kind="PCB_VIA")], "restore_R138_supply_leaf", 3.5)
    upoints = upper[2]
    add("/ADC/THRESH_UPPER", [("B.Cu", upoints)], [contact("/ADC/THRESH_UPPER", "B.Cu", upoints[0], refpin=("R138", "2")),
        contact("/ADC/THRESH_UPPER", "B.Cu", upoints[-1], refpin=("R139", "1"))], "restore_R138_threshold_link", min(8, 1.6*math.dist(*upoints)+.5))
    quiet, power = QuietTraceScreen(captured, NOISY), LayeredSignalScreen(captured)
    for row in routes:
        screen = power if row["net"] == "V5_REG" else quiet
        assert all(screen.legal(row["net"], face, ps) for face, ps in row["runs"])
        for s in (quiet, power):
            s.added.extend((row["net"], face, LineString(ps)) for face, ps in row["runs"])
    via = recipe["new_via_mm"]
    assert quiet.via_legal("/ADC/THRESH_LOWER", via)
    low = recipe["threshold_runs"]
    p, q = low[0][1][0], low[-1][1][-1]
    add("/ADC/THRESH_LOWER", low, [contact("/ADC/THRESH_LOWER", "F.Cu", p, refpin=("U107", "10")),
        contact("/ADC/THRESH_LOWER", "In3.Cu", q, kind="PCB_VIA")], "complete_lower_threshold_input", min(40, 2*math.dist(p, q)+6), [recipe["new_via_mm"]], False)
    assert all(quiet.legal("/ADC/THRESH_LOWER", face, ps) for face, ps in low)
    for s in (quiet, power):
        s.added.extend(("/ADC/THRESH_LOWER", face, LineString(ps)) for face, ps in low)
        s.new_vias.append(("/ADC/THRESH_LOWER", via))
    legacy = json.loads(LEGACY.read_text())
    for net, key, anchor in [("/ADC/BIAS_SHIFT_R", "right_span_endpoints_mm", ("U107", "8")),
                              ("/ADC/BIAS_SHIFT_L", "left_span_endpoints_mm", ("R135", "1"))]:
        original = next(r for r in legacy["routes"] if r["net"] == net and tuple(r["endpoints"][0]) == anchor)
        ends = recipe[key]
        routing_screen = quiet
        if net.endswith("_R"):
            # Do not cross the retained R137 branch of this same net and
            # accidentally create a large high-impedance copper loop.
            routing_screen = QuietTraceScreen(captured, NOISY)
            routing_screen.added = list(quiet.added)
            routing_screen.new_vias = list(quiet.new_vias)
            for uid in recipe["right_nonintersection_branch_uuids"]:
                o = objects[uid]
                assert o["net"] == net and o["kind"] == "PCB_TRACK"
                routing_screen.geometry["In3.Cu"].append((None, shape(o["layers"]["In3.Cu"]), .31))
            routing_screen.trees["In3.Cu"] = STRtree([g for _, g, _ in routing_screen.geometry["In3.Cu"]])
        path = route(routing_screen, net, "In3.Cu", ends[0], ends[1], [22, 39, 37, 57], seconds=10)
        assert path, (net, "No joint repair path")
        points = path["points_mm"]
        if net.endswith("_L"):
            # Join the existing input tree once, rather than running parallel
            # copper back to the abandoned private input via.
            inner = original["runs"][1][1]
            cut = next(i for i, xy in enumerate(inner) if math.dist(xy, points[0]) < 1e-6)
            retained = objects[recipe["left_native_track_uuid"]]
            assert retained["net"] == net and retained["position_mm"] == [26.9, 51.7]
            assert retained["end_mm"] == points[-1]
            entry = next(r for r in legacy["routes"] if r["net"] == net and r["endpoints"][0] == ["U107", "7"])
            full = [copy.deepcopy(original["runs"][0]), ["In3.Cu", copy.deepcopy(inner[:cut])+points+[retained["position_mm"]]],
                    ["F.Cu", list(reversed(entry["runs"][0][1]))]]
        else:
            shifted = copy.deepcopy(original["runs"])
            relocation = recipe["via_relocation"]
            for _, ps in shifted:
                for i, xy in enumerate(ps):
                    if math.dist(xy, relocation["before_mm"]) < 1e-6:
                        ps[i] = relocation["after_mm"]
            full = replace_span(shifted, points[-1], points[0], list(reversed(points)))
        terminal_disks = Point(points[0]).buffer(.65).union(Point(points[-1]).buffer(.65))
        for o in objects.values():
            if o["net"] == net and o["layers"].get("In3.Cu"):
                contact_geometry = LineString(points).intersection(shape(o["layers"]["In3.Cu"]).buffer(.1))
                assert contact_geometry.difference(terminal_disks).is_empty, (net, "Nonterminal same-net contact", o["uuid"])
        complete_length = sum(LineString(ps).length for _, ps in full)
        assert complete_length <= original["maximum_planar_length_mm"]
        retained_length = complete_length-path["length_mm"]
        limit = original["maximum_planar_length_mm"]-retained_length
        add(net, [("In3.Cu", points)], [contact(net, "In3.Cu", points[0]), contact(net, "In3.Cu", points[-1])],
            "restore_bias_span", limit)
        routes[-1].update(complete_legacy_runs=full, complete_legacy_length_mm=complete_length,
                          complete_legacy_maximum_mm=original["maximum_planar_length_mm"], legacy_endpoints=original["endpoints"])
        assert quiet.legal(net, "In3.Cu", points)
        for s in (quiet, power):
            s.added.append((net, "In3.Cu", LineString(points)))
    quiet, power = QuietTraceScreen(captured, NOISY), LayeredSignalScreen(captured)
    for row in routes:
        screen = power if row["net"] == "V5_REG" else quiet
        assert all(screen.legal(row["net"], face, ps) for face, ps in row["runs"]), row["purpose"]
        for s in (quiet, power):
            s.added.extend((row["net"], face, LineString(ps)) for face, ps in row["runs"])
            s.new_vias.extend((row["net"], xy) for xy in row["new_vias_mm"])
    board = read_sexpr((OUT / "prepared-refilled.kicad_pcb").read_text())
    original, count, additions = sexpr(board), len(board), []
    for row in routes:
        for face, ps in row["runs"]:
            add_geometry(board, additions, row["net"], face, ps, .2, row["purpose"])
        for xy in row["new_vias_mm"]:
            add_via(board, additions, row["net"], xy, row["purpose"])
    assert sexpr(board[:count]) == original
    dest = OUT / "distribution-input.kicad_pcb"
    dest.write_text(sexpr(board)+"\n")
    report = dict(source_sha256=relative_hashes([applied, PLAN, LEGACY, OUT / "prepared-native-inputs.json", OUT / "prepared-refilled.kicad_pcb",
        ROOT / "audio_main_quiet_screen.py", ROOT / "audio_main_layer_screen.py", ROOT / "audio_main_bypass_repack.py"]),
        authored_PCB_sha256=sha(dest), routes=routes, added_segments=[r for r in additions if r["kind"] == "segment"],
        added_vias=[r for r in additions if r["kind"] == "via"], trace_width_mm=.2, clearance_mm=.2,
        planning_margin_mm=.01, noisy_net_centreline_to_copper_mm=.71, restored_existing_connections=4,
        new_comparator_connections=1, expected_native_opens=171, native_checks_pending=True,
        electrical_noise_and_installed_fault_performance_qualified=False, fabrication_released=False)
    (OUT / "distribution-construction.json").write_text(json.dumps(report, indent=2)+"\n")
    print("Joint comparator construction: four restored connections and one new input; native checks pending")
    for row in routes:
        print(row["purpose"], round(row["planar_length_mm"], 3), "mm", flush=True)


def native(action):
    assert sys.platform == "linux", "Mac CAD remains disabled"
    applied = snapshot(action+"-entry")
    if action == "fill-prepared":
        from hardware.fabrication import audio_main_six_layer_trial as helper
        helper.OUT = OUT
        helper.fill_prepared()
        result = OUT / "prepared-refill.json"
    elif action in ("capture", "capture-final"):
        from hardware.fabrication.capture_audio_layer_trial import capture
        final = action == "capture-final"
        result = OUT / ("final-native-inputs.json" if final else "prepared-native-inputs.json")
        capture(OUT, OUT / ("audio_core.kicad_pcb" if final else "prepared-refilled.kicad_pcb"),
                OUT / ("terminal-connectivity-review.json" if final else "prepared-refill.json"), result.name, applied)
    elif action == "review-prepared":
        import subprocess
        project = OUT / "prepared-refilled.kicad_pro"
        shutil.copyfile(OUT / "audio_core.kicad_pro", project)
        rules = OUT / "prepared-refilled.kicad_dru"
        shutil.copyfile(OUT / "audio_core.kicad_dru", rules)
        command = ["kicad-cli", "pcb", "drc", "--all-track-errors", "--severity-all", "--format", "json",
                   "-o", str(OUT / "prepared-drc.json"), str(OUT / "prepared-refilled.kicad_pcb")]
        completed = subprocess.run(command, capture_output=True, text=True, check=True)
        (OUT / "prepared-drc.log").write_text(completed.stdout+completed.stderr)
        drc = json.loads((OUT / "prepared-drc.json").read_text())
        # Removing the declared links leaves two one-face vias and one track
        # end until build(). No other finding is permissible.
        allowed = {("via_dangling", "9d8927bc-761b-56d9-b1d9-8800f778b537"),
                   ("via_dangling", "8377fae8-caa6-5ed1-98d8-922580f8a68c"),
                   ("track_dangling", "2b413427-ea2b-5708-a1f4-91625134e0d4")}
        assert drc["ignored_checks"] == []
        assert {(r["type"], r["items"][0]["uuid"]) for r in drc["violations"]} == allowed, drc["violations"]
        result = OUT / "prepared-geometry-review.json"
        result.write_text(json.dumps(dict(source_sha256=relative_hashes([applied, OUT / "prepared-refilled.kicad_pcb", project, rules,
            OUT / "prepared-drc.json"]), command=command, native_non_dangling_findings=0,
            expected_preparation_dangling_findings=drc["violations"],
            prepared_geometry_only=True, schematic_parity_performed=False, final_zero_findings_required=True, fabrication_released=False), indent=2)+"\n")
        print("Prepared DRC has only the three expected incomplete-link warnings; final DRC must have zero findings")
    elif action == "fill":
        from hardware.fabrication import audio_main_power_routes as helper
        helper.OUT = OUT
        helper.fill()
        result = OUT / "native-refill.json"
    elif action == "review":
        from hardware.fabrication.audio_main_native_review import review
        review(OUT, SOURCE / "terminal-connectivity-review.json", OUT / "prepared-native-inputs.json", OUT / "distribution-construction.json", applied)
        result = OUT / "terminal-connectivity-review.json"
    else:
        from hardware.fabrication.review_audio_layer_retention import review
        review(SOURCE, OUT, 97, applied)
        result = OUT / "additional-terminal-review.json"
    (OUT / (action+"-entry.json")).write_text(json.dumps(dict(source_sha256=relative_hashes([applied, result]), fabrication_released=False), indent=2)+"\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "fill-prepared", "capture", "review-prepared", "build", "fill", "review", "retain", "capture-final"))
    action = parser.parse_args().action
    {"prepare": prepare, "build": build}.get(action, lambda: native(action))()
