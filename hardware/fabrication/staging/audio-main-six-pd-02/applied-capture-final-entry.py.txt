"""Repair the amplifier PD exits with native passive-side templates."""

import argparse
import copy
import json
import math
import shutil
import sys
from pathlib import Path

from hardware.electronics.common.sexpr import children, first, read_sexpr, sexpr
from hardware.fabrication.audio_main_local_routes import relative_hashes, verify_hashes
from hardware.fabrication.audit_candidate import sha

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "staging/audio-main-six-pd-01"
OUT = ROOT / "staging/audio-main-six-pd-02"
PLAN = ROOT / "audio_main_pd_pin_plan.json"
ROUTES = ROOT / "audio_main_pd_pin_routes.json"


def snapshot(label):
    path = OUT / ("applied-"+label+".py.txt")
    assert not path.exists()
    shutil.copyfile(Path(__file__), path)
    return path


def templates():
    assert sys.platform == "linux", "Mac CAD remains disabled"
    import pcbnew

    from hardware.fabrication.capture_board import polygons

    assert not OUT.exists()
    parent = json.loads((SOURCE / "PD-routing-review.json").read_text())
    verify_hashes(parent["source_sha256"])
    assert parent["uncapped_open_connections"] == 165
    OUT.mkdir()
    applied = snapshot("native-F-side-templates")
    dest = OUT / "templates"
    dest.mkdir()
    source = SOURCE / "audio_core.kicad_pcb"
    source_tree = read_sexpr(source.read_text())
    source_codes = {str(n[2]): n[1] for n in children(source_tree, "net")}
    rows = []
    for ref in ("R115", "R131"):
        board = pcbnew.LoadBoard(str(source))
        fp = next(f for f in board.GetFootprints() if f.GetReference() == ref)
        assert fp.IsFlipped()
        fp.Flip(fp.GetPosition(), False)
        for angle in (0, 90, 180, 270):
            fp.SetOrientationDegrees(angle)
            fp.SetPosition(pcbnew.VECTOR2I(0, 0))
            temporary = dest / "native-work.kicad_pcb"
            assert pcbnew.SaveBoard(str(temporary), board)
            tree = read_sexpr(temporary.read_text())
            node = next(f for f in children(tree, "footprint") if any(p[1:3] == ["Reference", ref] for p in children(f, "property")))
            native_nets = {p.GetNumber(): p.GetNetname() for p in fp.Pads()}
            for pad in children(node, "pad"):
                net = first(pad, "net")
                net[1] = source_codes[native_nets[str(pad[1])]]
                del net[2:]
            target = dest / f"{ref}-F-{angle}.kicad_mod"
            target.write_text(sexpr(node)+"\n")
            pads = []
            for pad in fp.Pads():
                poly = pcbnew.SHAPE_POLY_SET()
                pad.TransformShapeToPolygon(poly, pad.GetLayer(), 0, 1000, pcbnew.ERROR_OUTSIDE)
                pads.append(dict(kind="PAD", ref=ref, pin=pad.GetNumber(), net=pad.GetNetname(),
                    position_mm=[pad.GetPosition().x/1e6, pad.GetPosition().y/1e6],
                    drill_mm=[0, 0], npth=False, layers={"F.Cu": polygons(poly)}))
            rows.append(dict(ref=ref, side="F", angle=angle, file=target.name, sha256=sha(target), pads=pads))
        temporary.unlink()
    (dest / "templates.json").write_text(json.dumps(dict(source_sha256=relative_hashes([
        applied, source, SOURCE / "PD-routing-review.json", ROOT / "capture_board.py"]), native_version=pcbnew.GetBuildVersion(),
        templates=rows, fabrication_released=False), indent=2)+"\n")
    print("Captured eight native front-side resistor templates; no source board edits")


def prepare():
    from hardware.electronics.output_stage.check_placement import courtyard
    from hardware.fabrication.audio_main_local_repack import ReceivingSpace, footprints

    assert not (OUT / "prepared-input.kicad_pcb").exists()
    recipe = json.loads(PLAN.read_text())
    verify_hashes(recipe["source_sha256"])
    board = read_sexpr((SOURCE / "audio_core.kicad_pcb").read_text())
    net_names = {str(n[1]): str(n[2]) for n in children(board, "net")}
    originals, replacements = {}, {}
    for ref, placement in recipe["placements"].items():
        old = footprints(board)[ref]
        node = read_sexpr((OUT / "templates" / placement["template"]).read_text())
        assert first(old, "uuid") == first(node, "uuid") and old[1] == node[1]
        props = {str(p[1]): str(p[2]) for p in children(node, "property")}
        assert all(props[str(p[1])] == str(p[2]) for p in children(old, "property"))
        assert first(old, "layer")[1] == "B.Cu" and first(node, "layer")[1] == "F.Cu"
        # KiCad 10 exports numeric pad nets. This authored board uses the
        # earlier schema, which also requires the explicit name on each pad.
        for pad in children(node, "pad"):
            net = first(pad, "net")
            net[2:] = [net_names[str(net[1])]]
        first(node, "at")[1:] = placement["pose"]
        originals[ref], replacements[ref] = copy.deepcopy(old), copy.deepcopy(node)
        board[board.index(old)] = node
    assert ReceivingSpace(board, set(replacements)).accepts({r: v["pose"] for r, v in recipe["placements"].items()})
    retired = set(recipe["retired_copper_uuids"])
    removed = [n for tag in ("segment", "via") for n in children(board, tag) if str(first(n, "uuid")[1]) in retired]
    assert len(removed) == len(retired) == 15 and sum(n[0] == "via" for n in removed) == 1
    names = {str(n[1]): str(n[2]) for n in children(board, "net")}
    assert sorted(names[str(first(n, "net")[1])] for n in removed) == sorted(["ADC_BIAS_WINDOW_OK"]*12+["/ADC/PD_R"]*3)
    board = [n for n in board if n not in removed]
    applied = snapshot("PD-pin-preparation")
    for path in SOURCE.iterdir():
        if path.suffix in (".kicad_sch", ".kicad_pro", ".kicad_sym", ".kicad_dru") or path.name in ("fp-lib-table", "sym-lib-table"):
            shutil.copyfile(path, OUT / path.name)
    shutil.copytree(SOURCE / "libraries", OUT / "libraries")
    plan = json.loads((SOURCE / "plan.json").read_text())
    for ref, placement in recipe["placements"].items():
        assert not any(c["ref"] == ref or c["owner"] == ref for c in plan["local_cells"])
        plan["poses"][ref] = [*placement["pose"], "F"]
        plan["expanded_receiving_bounds_mm"][ref] = courtyard(replacements[ref], "F.CrtYd")
    plan["source_sha256"].update(relative_hashes([applied, PLAN, SOURCE / "plan.json"]))
    (OUT / "plan.json").write_text(json.dumps(plan, indent=2)+"\n")
    dest = OUT / "prepared-input.kicad_pcb"
    dest.write_text(sexpr(board)+"\n")
    (OUT / "preparation-record.json").write_text(json.dumps(dict(source_sha256=relative_hashes([
        applied, PLAN, SOURCE / "audio_core.kicad_pcb", SOURCE / "plan.json", OUT / "plan.json", ROOT / "audio_main_local_repack.py"]),
        authored_PCB_sha256=sha(dest), declared_footprint_replacements={r: dict(before=originals[r], after=replacements[r]) for r in replacements},
        retired_copper_uuids=sorted(retired), retired_nodes=removed, receiving_screen_passed=True,
        expected_native_opens=167, native_checks_pending=True, fabrication_released=False), indent=2)+"\n")
    print("Prepared two front-side pull resistors; retired fourteen segments and one via; native checks pending")


def build():
    from shapely.geometry import LineString

    from hardware.fabrication.audio_main_bypass_repack import add_geometry, add_via
    from hardware.fabrication.audio_main_pd_entry_screen import PDEntryScreen
    from hardware.fabrication.audio_main_quiet_screen import QuietTraceScreen
    from hardware.fabrication.audit_audio_main_named_routes import NETS

    assert not (OUT / "distribution-input.kicad_pcb").exists()
    proposal = json.loads(ROUTES.read_text())
    verify_hashes(proposal["source_sha256"])
    captured = json.loads((OUT / "prepared-native-inputs.json").read_text())
    verify_hashes(captured["source_sha256"])
    assert captured["native_uncapped_opens"] == 167
    objects = {o["uuid"]: o for o in captured["objects"]}
    pads = {(o["ref"], o["pin"]): o for o in objects.values() if o["kind"] == "PAD" and o["pin"]}
    member = {uid: key for key, ids in captured["groups"].items() for uid in ids}
    groups = {frozenset([key]) for key in captured["groups"]}
    routes = copy.deepcopy(proposal["routes"])
    common = QuietTraceScreen(captured, NETS)
    board = read_sexpr((OUT / "prepared-refilled.kicad_pcb").read_text())
    additions = []
    for row in routes:
        contacts = row["native_contacts"]
        for contact in contacts:
            obj = pads[contact["ref"], contact["pin"]] if "ref" in contact else objects[contact["uuid"]]
            assert obj["net"] == row["net"] and obj["layers"].get(contact["face"])
            assert any(math.dist(p, contact["point_mm"]) < 1e-6 for p in [obj["position_mm"]]+([obj["end_mm"]] if "end_mm" in obj else []))
            contact["uuid"] = obj["uuid"]
        sides = [next(g for g in groups if member[c["uuid"]] in g) for c in contacts]
        assert sides[0] != sides[1]
        row["source_groups"] = [sorted(g) for g in sides]
        screen = PDEntryScreen(captured, row["net"], row["runs"][0][1]) if row["purpose"] == "amplifier_PD_entry" else QuietTraceScreen(captured, NETS)
        screen.added, screen.new_vias = list(common.added), list(common.new_vias)
        assert all(screen.legal(row["net"], face, ps) for face, ps in row["runs"])
        assert sum(LineString(ps).length for face, ps in row["runs"]) <= row["maximum_planar_length_mm"]
        for xy in row["new_vias_mm"]:
            assert screen.via_legal(row["net"], xy)
        before = len(additions)
        for face, ps in row["runs"]:
            add_geometry(board, additions, row["net"], face, ps, .2, row["purpose"])
        for xy in row["new_vias_mm"]:
            add_via(board, additions, row["net"], xy, row["purpose"])
        row["new_copper_uuids"] = [a["uuid"] for a in additions[before:]]
        common.added.extend((row["net"], face, LineString(ps)) for face, ps in row["runs"])
        common.new_vias.extend((row["net"], xy) for xy in row["new_vias_mm"])
        groups.difference_update(sides)
        groups.add(sides[0] | sides[1])
    applied = snapshot("PD-pin-routing")
    target = OUT / "distribution-input.kicad_pcb"
    target.write_text(sexpr(board)+"\n")
    (OUT / "distribution-construction.json").write_text(json.dumps(dict(source_sha256=relative_hashes([
        applied, ROUTES, PLAN, OUT / "prepared-refilled.kicad_pcb", OUT / "prepared-native-inputs.json", OUT / "prepared-geometry-review.json",
        ROOT / "audio_main_pd_entry_screen.py", ROOT / "audio_main_quiet_screen.py", ROOT / "audio_main_bypass_repack.py"]),
        authored_PCB_sha256=sha(target), routes=routes, added_segments=[r for r in additions if r["kind"] == "segment"],
        added_vias=[r for r in additions if r["kind"] == "via"], trace_width_mm=.2, clearance_mm=.2, planning_margin_mm=.01,
        maximum_new_vias_per_PD_connection=2, maximum_PD_surface_neck_mm=3.5, maximum_legacy_control_path_vias=4,
        shared_previous_F_segments=1, expected_native_opens=162, new_PD_joins=3, restored_existing_joins=2,
        native_checks_pending=True, fabrication_released=False), indent=2)+"\n")
    print("Built five joins: three additional PD connections and two restored joins; native checks pending")


def native(action):
    assert sys.platform == "linux", "Mac CAD remains disabled"
    applied = snapshot(action+"-entry")
    if action == "fill-prepared":
        from hardware.fabrication import audio_main_six_layer_trial as helper
        helper.OUT = OUT
        helper.fill_prepared()
        result = OUT / "prepared-refill.json"
    elif action == "capture":
        from hardware.fabrication.capture_audio_layer_trial import capture
        result = OUT / "prepared-native-inputs.json"
        capture(OUT, OUT / "prepared-refilled.kicad_pcb", OUT / "prepared-refill.json", result.name, applied)
    elif action == "fill":
        from hardware.fabrication import audio_main_power_routes as helper
        helper.OUT = OUT
        helper.fill()
        result = OUT / "native-refill.json"
    elif action == "review":
        from hardware.fabrication.audio_main_native_review import review
        review(OUT, SOURCE / "terminal-connectivity-review.json", OUT / "prepared-native-inputs.json", OUT / "distribution-construction.json", applied)
        result = OUT / "terminal-connectivity-review.json"
    elif action == "retain":
        from hardware.fabrication.review_audio_layer_retention import review
        review(SOURCE, OUT, 108, applied)
        result = OUT / "additional-terminal-review.json"
    elif action == "capture-final":
        from hardware.fabrication.capture_audio_layer_trial import capture
        result = OUT / "final-native-inputs.json"
        capture(OUT, OUT / "audio_core.kicad_pcb", OUT / "terminal-connectivity-review.json", result.name, applied)
    else:
        import subprocess
        project, rules = [OUT / ("prepared-refilled"+suffix) for suffix in (".kicad_pro", ".kicad_dru")]
        shutil.copyfile(OUT / "audio_core.kicad_pro", project)
        shutil.copyfile(OUT / "audio_core.kicad_dru", rules)
        command = ["kicad-cli", "pcb", "drc", "--all-track-errors", "--severity-all", "--format", "json",
                   "-o", str(OUT / "prepared-drc.json"), str(OUT / "prepared-refilled.kicad_pcb")]
        completed = subprocess.run(command, capture_output=True, text=True, check=True)
        (OUT / "prepared-drc.log").write_text(completed.stdout+completed.stderr)
        drc = json.loads((OUT / "prepared-drc.json").read_text())
        assert drc["ignored_checks"] == []
        allowed = {("via_dangling", "7a953de3-5809-520c-9206-4fb656481a9c"),
                   ("via_dangling", "d743267a-d20f-5bbe-934c-0450c4a5f02e")}
        assert {(r["type"], r["items"][0]["uuid"]) for r in drc["violations"]} == allowed, drc["violations"]
        result = OUT / "prepared-geometry-review.json"
        result.write_text(json.dumps(dict(source_sha256=relative_hashes([applied, OUT / "prepared-refilled.kicad_pcb", project, rules,
            OUT / "prepared-drc.json"]), native_non_dangling_findings=0, expected_preparation_dangling_findings=drc["violations"],
            prepared_geometry_only=True, final_zero_findings_required=True, fabrication_released=False), indent=2)+"\n")
        print("Prepared DRC has only the two expected incomplete-link warnings; final DRC must have zero findings")
    (OUT / (action+"-entry.json")).write_text(json.dumps(dict(source_sha256=relative_hashes([applied, result]), fabrication_released=False), indent=2)+"\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("templates", "prepare", "fill-prepared", "capture", "review-prepared", "build", "fill", "review", "retain", "capture-final"))
    action = parser.parse_args().action
    {"templates": templates, "prepare": prepare, "build": build}.get(action, lambda: native(action))()
