"""Join RUN through vias selected in one common free inner-layer region.

This is an explicit power-pour-cut trial. Fresh native refill and full electrical
extraction are mandatory; the previous filled-power reservation is not inherited.
"""

import json
import math
import uuid
from pathlib import Path

import numpy as np
from scipy.ndimage import label

from hardware.electronics.common.sexpr import a, children, read_sexpr, sexpr
from hardware.electronics.rail_disconnect.revision26 import router as aid
from hardware.electronics.rail_disconnect.revision28.band_router import BandRouter
from hardware.electronics.rail_disconnect.revision28.component_routes import connect_components
from hardware.electronics.rail_disconnect.revision28.receiver_surface_path import connect

from .route_e28 import WORK, sha


def run():
    source=WORK/"generated/power-edge-08-trial/rail_disconnect.kicad_pcb"
    filled=WORK/"generated/native-power-edge-08/rail_disconnect.kicad_pcb"
    out=WORK/"generated/run-common-region-trial"
    out.mkdir(exist_ok=False)
    tree=read_sexpr(source.read_text())
    count,frozen=len(tree),sexpr(tree)
    pads=json.loads((WORK/"generated/routing-inputs/pads.json").read_text())
    rt=BandRouter(tree,read_sexpr(filled.read_text()),pads,step=.05)
    rt.force_guard=None
    blocked,via=rt.masks("RUN_BUFFERED",.2)
    regions,n=label(~blocked[3])
    sizes=np.bincount(regions.ravel())
    sizes[0]=0
    biggest=int(sizes.argmax())
    assert sizes[biggest]>10000
    shared=regions==biggest
    results,escaped=[],[]
    for ref,pin in (("U28","1"),("U43","4")):
        pad=next(p for p in rt.by_ref[ref] if p["pin"]==pin)
        x,y=pad["xy"]
        d2=(rt.xx-x)**2+(rt.yy-y)**2
        ix,iy=np.where(shared & ~via & ~blocked[pad["layers"][0]] & (d2<12**2))
        choices=sorted(zip(ix,iy),key=lambda p:float(d2[p]))
        targets=[]
        for u,v in choices:
            xy=(round(u*.05,6),round(v*.05,6))
            if all(math.dist(xy,p["xy"])>=.65 for p in targets):
                targets.append(dict(xy=xy,net="RUN_BUFFERED",layers=list(range(6))))
            if len(targets)==100:
                break
        result,reason=connect(rt,pad,targets,radius=12,step=.025,budget=400000)
        aid.STEP=.05
        if result:
            xy=result["target"]["xy"]
            rt.via("RUN_BUFFERED",xy)
            escaped.append(dict(xy=xy,layers=[3],kind="PCB_VIA",ref=ref))
        results.append(dict(ref=ref,connected=bool(result),result=result,reason=reason))
        print(ref,bool(result),reason,flush=True)
    if len(escaped)==2:
        rt.cached={}
        masks=rt.masks

        def one_layer(net,width):
            blocked,via=masks(net,width)
            blocked=blocked.copy()
            blocked[[0,1,2,4,5]]=True
            return blocked,np.ones(via.shape,dtype=bool)

        rt.masks=one_layer
        result=connect_components(rt,dict(net="RUN_BUFFERED",components=[[escaped[0]],[escaped[1]]]),
                                  width=.2,budget=1200000)
        results.append(dict(stage="common_In3_join",**result))
        print("RUN common In3",result.get("connected"),result.get("visited"),result.get("reason"),flush=True)
    assert sexpr(tree[:count])==frozen
    for index,node in enumerate(tree):
        if isinstance(node,list) and node and node[0] in ("segment","via") and not children(node,"uuid"):
            node.append([a("uuid"),a(str(uuid.uuid5(uuid.NAMESPACE_URL,f"rmx:AX03:common:{sha(source)}:{index}:{sexpr(node)}")))])
    pcb=out/source.name
    pcb.write_text(sexpr(tree)+"\n")
    (out/"routes.json").write_text(json.dumps(dict(source_sha256=sha(source),candidate_sha256=sha(pcb),
        filled_source_sha256=sha(filled),recipe_sha256=sha(Path(__file__)),results=results,routes=rt.routes,
        shared_layer="In3.Cu",shared_component_cells=int(sizes[biggest]),grid_mm=.05,
        all_original_objects_preserved=True,power_pour_cuts_allowed=True,
        native_refill_and_complete_power_review_pending=True,fabrication_released=False),indent=2)+"\n")


if __name__=="__main__":
    run()
