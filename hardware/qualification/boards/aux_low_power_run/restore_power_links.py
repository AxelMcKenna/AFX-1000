"""Restore the two trial power disconnects with explicit wide copper candidates.

Connectivity is necessary, not sufficient. Finite spreading/barrel resistance,
current density, temperature and fault energy must be re-extracted before use.
"""

import argparse
import json
import uuid
from pathlib import Path

from hardware.electronics.common.sexpr import a, children, first, read_sexpr, sexpr
from hardware.electronics.rail_disconnect.revision28.band_router import BandRouter
from hardware.electronics.rail_disconnect.revision28.component_routes import connect_components

from .route_e28 import WORK, sha


def run():
    parser = argparse.ArgumentParser()
    parser.add_argument("--half-mm-followup", action="store_true")
    args = parser.parse_args()
    parent = WORK / "generated/logic-pour-trial/rail_disconnect.kicad_pcb"
    source = WORK / ("generated/power-link-repair-trial/rail_disconnect.kicad_pcb" if args.half_mm_followup else "generated/logic-pour-trial/rail_disconnect.kicad_pcb")
    graph = WORK / "generated/logic-pour-followup/components.json"
    filled = WORK / "generated/native-logic-pour-trial/rail_disconnect.kicad_pcb"
    out = WORK / ("generated/power-link-half-mm-trial" if args.half_mm_followup else "generated/power-link-repair-trial")
    out.mkdir(exist_ok=False)
    inventory = json.loads(graph.read_text())
    assert inventory["source_sha256"][str(parent)]==sha(parent)
    tree = read_sexpr(source.read_text())
    count,frozen = len(tree),sexpr(tree)
    pads = json.loads((WORK / "generated/routing-inputs/pads.json").read_text())
    rt = BandRouter(tree,read_sexpr(filled.read_text()),pads,step=.1)
    names = {str(n[1]):str(n[2]).lstrip("/") for n in children(tree,"net")}
    editable = {str(first(n,"uuid")[1]):names[str(first(n,"net")[1])]
                for kind in ("segment","via") for n in children(tree,kind)}
    results=[]
    width = .5 if args.half_mm_followup else 1.0
    for net in (("5V_DIG_SRC",) if args.half_mm_followup else ("5V_DIG_SRC","V5_REG_SRC")):
        groups=[]
        for group in inventory["inventory"][net]["components"]:
            points=[]
            for obj in group:
                if obj["kind"]!="PAD" and editable.get(obj["uuid"])!=net:
                    continue
                for xy in [obj["position_mm"]]+([obj["end_mm"]] if obj["kind"]=="PCB_TRACK" else []):
                    points.append(dict(xy=xy,layers=obj["layers"],kind=obj["kind"],uuid=obj["uuid"],ref=obj.get("ref")))
            groups.append(points)
        assert len(groups)==2
        rt.cached={}
        result=connect_components(rt,dict(net=net,components=groups),width=width,budget=900000)
        results.append(dict(net=net,trace_width_mm=width,**result))
        print(net,result.get("connected"),result.get("visited"),result.get("reason"),flush=True)
    assert sexpr(tree[:count])==frozen
    for index,node in enumerate(tree):
        if isinstance(node,list) and node and node[0] in ("segment","via") and not children(node,"uuid"):
            node.append([a("uuid"),a(str(uuid.uuid5(uuid.NAMESPACE_URL,f"rmx:AX03:powerrepair:{sha(source)}:{index}:{sexpr(node)}")))])
    pcb=out/source.name
    pcb.write_text(sexpr(tree)+"\n")
    (out/"routes.json").write_text(json.dumps(dict(source_sha256=sha(source),candidate_sha256=sha(pcb),
        recipe_sha256=sha(Path(__file__)),inventory_sha256=sha(graph),attempts=results,routes=rt.routes,
        all_existing_objects_preserved=True,other_filled_force_copper_reserved=True,
        connectivity_only_not_current_qualification=True,power_return_reextraction_required=True,
        physical_qualified=False,fabrication_released=False),indent=2)+"\n")


if __name__=="__main__":
    run()
