"""Local timing-cap rotation removes the fence around U1's final supply pad."""

import json
import uuid
from pathlib import Path

from hardware.electronics.common.sexpr import a, children, first, read_sexpr, sexpr
from hardware.fabrication.audit_candidate import sha

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT/"staging/bypass-final-native-01/sequenced_bypass.kicad_pcb"
OUTPUT = ROOT/"staging/bypass-watchdog-escape-01"
GROUND_BRANCH = {"8c467129-dff8-4c4c-8158-259fa636e821","9fe3ddb0-12a9-440d-bc64-756f07a2fc99","e9117ae9-31fb-4151-b0cb-5d47854136bd"}
UNUSED_VIA = "a1714b9c-2dbf-46c9-a836-6659911cca30"


def run():
    assert not OUTPUT.exists()
    original = sha(SOURCE)
    board = read_sexpr(SOURCE.read_text())
    removed = []
    for node in list(board):
        if not (isinstance(node,list) and node and node[0] in ("segment","via")):
            continue
        uid,net = str(first(node,"uuid")[1]),str(first(node,"net")[-1])
        delete = net == "/CWD" or uid in GROUND_BRANCH or uid == UNUSED_VIA
        if not delete:
            continue
        if uid in GROUND_BRANCH:
            assert net == "/AGND" and node[0] == "segment"
        if uid == UNUSED_VIA:
            assert net == "/INPUT_READY" and node[0] == "via"
        removed.append(dict(kind=str(node[0]),uuid=uid,net=net))
        board.remove(node)
    assert len(removed) == 8 and sum(r["net"] == "/CWD" for r in removed) == 4
    cap = next(fp for fp in children(board,"footprint") if any(p[1:3] == ["Reference","C1"] for p in children(fp,"property")))
    at = first(cap,"at")
    assert list(map(float,at[1:3])) == [54,16] and (len(at) == 3 or float(at[3]) == 0)
    at[:] = [a("at"),54,16,180]
    paths = [
        ("/CWD",[(56.6,15.675),(54.9125,16)]),
        ("/AGND",[(53.0875,16),(51.5,16)]),
        ("/AGND",[(56.6,16.975),(57.1,16.975),(58,16.8)]),
        ("/3V3",[(56.6,16.325),(55.9,16.325),(55.9,17.5),(55,18)]),
    ]
    for net,points in paths:
        for start,end in zip(points,points[1:]):
            uid = str(uuid.uuid5(uuid.NAMESPACE_URL,f"AFX:E11:WD-escape:{original}:{net}:{start}:{end}"))
            board.append([a("segment"),[a("start"),*start],[a("end"),*end],[a("width"),.2],
                          [a("layer"),"F.Cu"],[a("net"),net],[a("uuid"),uid]])
    vias = [("/AGND",(51.5,16)),("/3V3",(55,18))]
    for net,point in vias:
        uid = str(uuid.uuid5(uuid.NAMESPACE_URL,f"AFX:E11:WD-escape-via:{original}:{net}:{point}"))
        board.append([a("via"),[a("at"),*point],[a("size"),.65],[a("drill"),.3],
            [a("layers"),"F.Cu","B.Cu"],[a("tenting"),[a("front"),a("yes")],[a("back"),a("yes")]],
            [a("net"),net],[a("uuid"),uid]])
    assert sha(SOURCE) == original
    OUTPUT.mkdir()
    pcb = OUTPUT/SOURCE.name
    pcb.write_text(sexpr(board)+"\n")
    (OUTPUT/"construction.json").write_text(json.dumps(dict(source_PCB_sha256=original,
        candidate_PCB_sha256=sha(pcb),recipe_sha256=sha(Path(__file__)),removed=removed,
        changed_component_pose=dict(ref="C1",xy_mm=[54,16],old_angle=0,new_angle=180),
        unchanged_component_values_and_pin_nets=True,paths=paths,vias=vias,
        native_checks_pending=True,physical_qualified=False,fabrication_released=False),indent=2)+"\n")
    print("Rotated C1 and rebuilt local CWD/ground/supply routes; one unused signal via removed")


if __name__ == "__main__":
    run()
