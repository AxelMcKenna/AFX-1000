"""Renew two congested audio cells without relaxing receiving or routing limits."""

import argparse
import copy
import json
import math
import shutil
import sys
import uuid
from pathlib import Path

from hardware.electronics.common.sexpr import a, children, first, read_sexpr, sexpr
from hardware.electronics.output_stage.check_placement import courtyard
from hardware.fabrication.audio_main_local_routes import relative_hashes, verify_hashes
from hardware.fabrication.audio_main_placement import FILMS, MOUNTS
from hardware.fabrication.audit_candidate import sha

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "staging/audio-main-local-routing-02"
RAW = ROOT / "staging/audio-main-local-routing-01/native-inputs.json"
OUT = ROOT / "staging/audio-main-local-routing-03"
MOVES = {"D102": (45, 36.5, 0), "C118": (49.5, 31, 180), "R324": (107, 30, 90)}


def footprints(board):
    return {next(p[2] for p in children(fp, "property") if p[1] == "Reference"): fp
            for fp in children(board, "footprint")}


def mapper(before, after):
    x, y, angle = before
    xx, yy, target = after
    theta = math.radians(target - angle)
    def move(point):
        dx, dy = point[0] - x, point[1] - y
        return (xx + math.cos(theta) * dx + math.sin(theta) * dy,
                yy - math.sin(theta) * dx + math.cos(theta) * dy)
    return move


def moved_inputs(original, oldposes, newposes):
    captured = copy.deepcopy(original)
    for pad in captured["objects"]:
        ref = pad["ref"]
        if ref not in newposes:
            continue
        move = mapper(oldposes[ref], newposes[ref])
        pad["position_mm"] = move(pad["position_mm"])
        for polygons in pad["layers"].values():
            for polygon in polygons:
                polygon["outer"] = [move(p) for p in polygon["outer"]]
                polygon["holes"] = [[move(p) for p in ring] for ring in polygon["holes"]]
    return captured


def poses(board):
    return {ref: tuple(map(float, first(fp, "at")[1:4])) for ref, fp in footprints(board).items()}


def set_poses(board, updated):
    for ref, fp in footprints(board).items():
        if ref in updated:
            first(fp, "at")[1:4] = list(updated[ref])


class ReceivingSpace:
    def __init__(self, board, moving):
        from shapely.geometry import box
        from shapely.strtree import STRtree

        from hardware.fabrication.audit_audio_main_placement import pad_extent

        self.base = footprints(board)
        self.moving = moving
        self.shapes, self.trees = {}, {}
        for face in ("F", "B"):
            entries = []
            for ref, fp in self.base.items():
                if ref in moving or ref.startswith("H"):
                    continue
                same = first(fp, "layer")[1] == face + ".Cu"
                if same:
                    b = courtyard(fp, face + ".CrtYd")
                    extra = .5 if ref in FILMS or ref.startswith("J") else 0
                    entries.append((box(b[0]-extra, b[1]-extra, b[2]+extra, b[3]+extra), .3))
                else:
                    entries.extend((pad_extent(fp, p), 0) for p in children(fp, "pad")
                                   if p[2] in ("thru_hole", "np_thru_hole"))
            self.shapes[face] = entries
            self.trees[face] = STRtree([s for s, _ in entries])

    def accepts(self, updated):
        from shapely.geometry import box

        changed = {}
        for ref, pose in updated.items():
            fp = copy.deepcopy(self.base[ref])
            first(fp, "at")[1:4] = list(pose)
            face = first(fp, "layer")[1][0]
            poly = box(*courtyard(fp, face + ".CrtYd"))
            if not box(.5, .5, 149.5, 62.5).covers(poly) or poly.distance(box(54, 22, 70, 38)) < .5-1e-8:
                return False
            if any(poly.distance(box(x-3.6, y-3.6, x+3.6, y+3.6)) < .15-1e-8 for x, y in MOUNTS):
                return False
            for index in self.trees[face].query(poly.buffer(.31)):
                other, gap = self.shapes[face][int(index)]
                if (gap and poly.distance(other) < gap-1e-8) or (not gap and poly.intersection(other).area > 1e-10):
                    return False
            changed[ref] = (face, poly)
        return all(face != otherface or p.distance(q) >= .3-1e-8
                   for i, (face, p) in enumerate(changed.values()) for otherface, q in list(changed.values())[i+1:])


def build():
    from hardware.electronics.common.netlists import netlist
    from hardware.fabrication.audio_main_escape_router import EscapeScreen
    from hardware.fabrication.audit_audio_main_placement import verify_geometry
    from hardware.fabrication.audit_audio_main_routes import check

    assert check() == json.loads((SOURCE / "routing-handoff.json").read_text())
    assert not OUT.exists()
    board = read_sexpr((SOURCE / "audio_core.kicad_pcb").read_text())
    original = copy.deepcopy(board)
    oldposes = poses(board)
    assert ReceivingSpace(board, set(MOVES)).accepts(MOVES)
    construction = json.loads((SOURCE / "construction.json").read_text())
    assert not any(row["ref"] in MOVES for row in construction["routes"])
    raw = json.loads(RAW.read_text())
    verify_hashes(raw["source_sha256"])
    captured = moved_inputs(raw, oldposes, MOVES)
    set_poses(board, MOVES)
    plan = json.loads((SOURCE / "plan.json").read_text())
    for ref, pose in MOVES.items():
        fp = footprints(board)[ref]
        side = first(fp, "layer")[1][0]
        plan["poses"][ref] = [*pose, side]
        plan["expanded_receiving_bounds_mm"][ref] = courtyard(fp, side + ".CrtYd")
    parts, pins = netlist(SOURCE / "native-netlist.xml")
    geometry = verify_geometry([n for n in board if not isinstance(n, list) or not n or n[0] not in ("segment", "via")], plan, parts, pins)
    routes = copy.deepcopy(construction["routes"])
    requests = copy.deepcopy(construction["requests"])
    deferred = []
    new_routes, new_vias = [], []
    nets = {str(n[2]): int(n[1]) for n in children(board, "net")}
    for row in construction["deferred"]:
        if row["kind"] == "local_ground_return":
            deferred.append(copy.deepcopy(row))
            continue
        context = EscapeScreen(board, captured)
        result = context.route(row)
        assert result, ("Local route not closed", row["ref"])
        ids, via_ids = [], []
        for layer, path in result["paths"]:
            for start, end in zip(path, path[1:]):
                ident = str(uuid.uuid5(uuid.NAMESPACE_URL, f"AFX:AC04:finish:{row['net']}:{layer}:{start}:{end}"))
                ids.append(ident)
                board.append([a("segment"), [a("start"), *start], [a("end"), *end], [a("width"), .2],
                              [a("layer"), layer], [a("net"), nets[row["net"]]], [a("uuid"), ident]])
        for xy in result["vias"]:
            ident = str(uuid.uuid5(uuid.NAMESPACE_URL, f"AFX:AC04:finishvia:{row['net']}:{xy}"))
            via_ids.append(ident)
            board.append([a("via"), [a("at"), *xy], [a("size"), .6], [a("drill"), .3],
                          [a("layers"), "F.Cu", "B.Cu"], [a("net"), nets[row["net"]]], [a("uuid"), ident]])
            new_vias.append(dict(uuid=ident, net=row["net"], xy_mm=xy, diameter_mm=.6, drill_mm=.3))
        route = dict(row, actual_length_mm=result["length"], paths=result["paths"], path_mm=[],
                     segment_uuids=ids, via_uuids=via_ids, inherited_trunk_segment_uuids=[],
                     nominal_via_barrel_traversal_mm=1.6 * len(via_ids))
        routes.append(route)
        new_routes.append(route)
    assert len(new_routes) == 2 and len(routes) == 138 and len(deferred) == 13
    expected = copy.deepcopy(original)
    set_poses(expected, MOVES)
    assert board[:len(expected)] == expected, "Unexpected existing copper or land edit"
    OUT.mkdir()
    for p in SOURCE.iterdir():
        if p.suffix in (".kicad_sch", ".kicad_pro", ".kicad_sym", ".kicad_dru") or p.name in ("fp-lib-table", "sym-lib-table"):
            shutil.copyfile(p, OUT / p.name)
    shutil.copytree(SOURCE / "libraries", OUT / "libraries")
    (OUT / "plan.json").write_text(json.dumps(plan, indent=2) + "\n")
    (OUT / "audio_core.kicad_pcb").write_text(sexpr(board) + "\n")
    captured["source_sha256"] = relative_hashes([RAW, SOURCE / "audio_core.kicad_pcb", Path(__file__)])
    captured["planning_polygons_transformed_from_parent_native_capture"] = True
    captured["current_native_pad_capture_required"] = True
    (OUT / "planning-pad-inputs.json").write_text(json.dumps(captured, separators=(",", ":")) + "\n")
    inputs = [Path(__file__), ROOT / "audio_main_escape_router.py", SOURCE / "audio_core.kicad_pcb",
              SOURCE / "routing-handoff.json", SOURCE / "construction.json", SOURCE / "plan.json", RAW,
              OUT / "audio_core.kicad_dru", OUT / "plan.json", OUT / "planning-pad-inputs.json"]
    data = dict(source_sha256=relative_hashes(inputs), candidate_PCB_sha256=sha(OUT / "audio_core.kicad_pcb"),
                requests=requests, routes=routes, deferred=deferred, added_routes=new_routes, added_vias=new_vias,
                declared_pose_changes={ref: dict(before=oldposes[ref], after=pose) for ref, pose in MOVES.items()},
                receiving_geometry=geometry, all_parent_copper_and_critical_poses_preserved=True,
                filter_capacitor_C118_is_provisional_pending_actual_ESS_land=True,
                width_mm=.2, general_clearance_mm=.2, native_checks_pending=True,
                complete_ground_returns_power_routing_and_analog_qualification=False, fabrication_released=False)
    (OUT / "construction.json").write_text(json.dumps(data, indent=2) + "\n")
    print("Built local rework: all 131 declared signal/supply endpoints routed; native review pending")


def review():
    assert sys.platform == "linux", "Mac CAD remains disabled"
    import pcbnew

    from hardware.fabrication import audio_main_local_branches
    from hardware.fabrication.capture_board import polygons

    audio_main_local_branches.OUT = OUT
    audio_main_local_branches.review()
    pcb = OUT / "audio_core.kicad_pcb"
    board = pcbnew.LoadBoard(str(pcb))
    objects = []
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            row = dict(uuid=pad.m_Uuid.AsString(), kind="PAD", ref=fp.GetReference(), pin=pad.GetNumber(),
                       net=pad.GetNetname(), position_mm=[pad.GetPosition().x / 1e6, pad.GetPosition().y / 1e6],
                       drill_mm=[pad.GetDrillSize().x / 1e6, pad.GetDrillSize().y / 1e6],
                       npth=int(pad.GetAttribute()) == int(pcbnew.PAD_ATTRIB_NPTH), layers={})
            for name in ("F.Cu", "B.Cu", "In1.Cu", "In2.Cu"):
                layer = board.GetLayerID(name)
                if pad.IsOnLayer(layer):
                    poly = pcbnew.SHAPE_POLY_SET()
                    pad.TransformShapeToPolygon(poly, layer, 0, pcbnew.FromMM(.001), pcbnew.ERROR_OUTSIDE)
                    poly.Simplify()
                    row["layers"][name] = polygons(poly)
            objects.append(row)
    data = dict(source_sha256=relative_hashes([pcb, Path(__file__), ROOT / "capture_board.py"]),
                native_version=pcbnew.GetBuildVersion(), objects=objects, fabrication_released=False)
    (OUT / "native-pad-capture.json").write_text(json.dumps(data, separators=(",", ":")) + "\n")
    print("Captured", len(objects), "current native pads independently of the planning transform")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("build", "review"))
    args = parser.parse_args()
    {"build": build, "review": review}[args.action]()

