"""Explicit pour-cut trial for remaining low-current logic connections.

No existing copper object, component or rule is removed. Refilling may withdraw
power/return pours. Previous current-path claims cannot be inherited: compare
actual filled copper and rerun finite power/return extraction before adoption.
"""

import json
import uuid
from pathlib import Path

from hardware.electronics.common.sexpr import a, children, first, read_sexpr, sexpr
from hardware.electronics.rail_disconnect.revision28.band_router import BandRouter
from hardware.electronics.rail_disconnect.revision28.component_routes import connect_components

from .route_e28 import WORK, sha


def run():
    source = WORK / "generated/receiver-direct-routes/rail_disconnect.kicad_pcb"
    out = WORK / "generated/logic-pour-trial"
    out.mkdir(exist_ok=False)
    digest = sha(source)
    tree = read_sexpr(source.read_text())
    count, frozen = len(tree), sexpr(tree)
    filled_path = WORK / "generated/native-direct-pose-checked/rail_disconnect.kicad_pcb"
    pads_path = WORK / "generated/routing-inputs/pads.json"
    pads = json.loads(pads_path.read_text())
    router = BandRouter(tree,read_sexpr(filled_path.read_text()),pads,step=.05)
    router.force_guard = None
    inventory = json.loads((WORK / "generated/routing-inputs/components.json").read_text())
    names = {str(n[1]):str(n[2]).lstrip("/") for n in children(tree,"net")}
    editable = {str(first(n,"uuid")[1]):names[str(first(n,"net")[1])]
                for kind in ("segment","via") for n in children(tree,kind)}
    runs = [n for n in children(tree,"via") if names[str(first(n,"net")[1])]=="RUN_BUFFERED"]
    assert len(runs)==2
    run_anchors = [dict(xy=[float(v)-100 for v in first(n,"at")[1:3]],layers=list(range(6)),
                        kind="PCB_VIA",uuid=str(first(n,"uuid")[1])) for n in runs]
    tasks = [("RUN_BUFFERED",[[run_anchors[0]],[run_anchors[1]]])]
    for net,row in inventory["inventory"].items():
        if net in ("AGND","V2V5_AUX","POWER_RUN","RUN_BUFFERED"):
            continue
        groups = []
        for group in row["components"]:
            points=[]
            for obj in group:
                if obj["kind"]!="PAD" and editable.get(obj["uuid"])!=net:
                    continue
                for xy in [obj["position_mm"]]+([obj["end_mm"]] if obj["kind"]=="PCB_TRACK" else []):
                    points.append(dict(xy=xy,layers=obj["layers"],kind=obj["kind"],uuid=obj["uuid"],ref=obj.get("ref")))
            assert points
            groups.append(points)
        tasks.append((net,groups))
    results=[]
    for net,groups in tasks:
        joined=groups[0]
        for group in groups[1:]:
            router.cached={}
            result=connect_components(router,dict(net=net,components=[joined,group]),width=.2,budget=800000)
            results.append(dict(net=net,**result))
            print(net,result.get("connected"),result.get("visited"),result.get("reason"),flush=True)
            if result.get("connected"):
                joined+=group
    assert sexpr(tree[:count])==frozen
    for index,node in enumerate(tree):
        if isinstance(node,list) and node and node[0] in ("segment","via") and not children(node,"uuid"):
            node.append([a("uuid"),a(str(uuid.uuid5(uuid.NAMESPACE_URL,f"rmx:AX03:pourtrial:{digest}:{index}:{sexpr(node)}")))])
    pcb=out/source.name
    pcb.write_text(sexpr(tree)+"\n")
    (out/"routes.json").write_text(json.dumps(dict(source_sha256=digest,candidate_sha256=sha(pcb),
        recipe_sha256=sha(Path(__file__)),native_inventory_sha256=sha(WORK/"generated/routing-inputs/components.json"),
        attempts=results,routes=router.routes,existing_objects_unchanged=True,
        existing_power_pours_reserved=False,power_and_return_extraction_required=True,
        previous_current_path_qualification_inherited=False,native_checks_pending=True,
        physical_qualified=False,fabrication_released=False),indent=2)+"\n")
    assert sha(source)==digest


if __name__=="__main__":
    run()
