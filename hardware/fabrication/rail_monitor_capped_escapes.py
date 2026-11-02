"""Separate E13 via-in-pad trial; requires filled/capped process acceptance.

Connect only orphan supply/ground groups to their actual same-net inner plane.
Preserve every original authored object and retain fresh native checks as a gate.
"""

import json
import uuid
from pathlib import Path

from shapely.geometry import Point

from hardware.electronics.common.sexpr import a, read_sexpr, sexpr
from hardware.fabrication.audit_candidate import sha
from hardware.fabrication.route_nf_surface import shape

ROOT = Path(__file__).resolve().parent


def run():
    capture_path = ROOT/"staging/rail-monitor-routing-inputs-13/capture.json"
    capture = json.loads(capture_path.read_text())
    assert all(sha(Path(p)) == h for p, h in capture["source_sha256"].items())
    source = next(Path(p) for p in capture["source_sha256"] if p.endswith(".kicad_pcb"))
    board = read_sexpr(source.read_text())
    original = sexpr(board)
    size = len(board)
    objects = {p["uuid"]: p for p in capture["objects"]}
    planes = {z["net"]: (z["layer"], shape(z["polygons"]))
              for z in capture["zones"] if not z["keepout"]}
    added = []
    deferred = []
    for group, ids in sorted(capture["groups"].items()):
        net = objects[ids[0]]["net"]
        if net not in planes:
            continue
        layer, plane = planes[net]
        if any(layer in objects[i]["layers"] and
               shape(objects[i]["layers"][layer]).intersection(plane).area > 1e-8 for i in ids):
            continue
        pads = sorted((objects[i] for i in ids if objects[i]["kind"] == "PAD" and
                       "F.Cu" in objects[i]["layers"] and
                       plane.covers(Point(objects[i]["position_mm"]))), key=lambda p: (p["ref"], p["pin"]))
        if not pads:
            deferred.append(dict(net=net, group=group, reason="No pad over its filled supply plane"))
            continue
        pad = pads[0]
        xy = pad["position_mm"]
        ident = str(uuid.uuid5(uuid.NAMESPACE_URL, f"AFX:E13:capped:{sha(source)}:{pad['uuid']}"))
        board.append([a("via"), [a("at"), *xy], [a("size"), .65], [a("drill"), .3],
                      [a("layers"), "F.Cu", "B.Cu"], [a("capping"), a("yes")],
                      [a("filling"), a("yes")], [a("net"), net], [a("uuid"), ident]])
        added.append(dict(uuid=ident, net=net, ref=pad["ref"], pin=pad["pin"],
                          position_mm=xy, plane_layer=layer, native_group=group))
    assert added and sexpr(board[:size]) == original
    output = ROOT/"staging/rail-monitor-capped-escapes-01"
    output.mkdir(exist_ok=False)
    pcb = output/source.name
    pcb.write_text(sexpr(board)+"\n")
    (output/"construction.json").write_text(json.dumps(dict(
        source_sha256={str(p): sha(p) for p in (source, capture_path, Path(__file__))},
        candidate_PCB_sha256=sha(pcb), added_vias=added, deferred_groups=deferred,
        original_authored_objects_exact=True, native_checks_pending=True,
        filled_copper_capped_planar_via_process_required=True,
        process_accepted=False, fabrication_released=False), indent=2)+"\n")
    print("Added", len(added), "explicit filled/capped via-in-pad escapes; native review pending")


if __name__ == "__main__":
    run()
