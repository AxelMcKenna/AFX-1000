"""Continue residual routing using the second new central layer.

Existing through vias reach the new layer. Missing escapes use ordinary0.6/0.3
barrels and actual surface paths. C50 filled/capped processing is a receiving
requirement; own-net SMD lands do not impose an invented via prohibition. No
foreign land, track, drill or physical hardware reservation is waived. Native
refill, DRC, exact pad geometry and fresh power/return extraction remain required.
"""

import copy
import heapq
import itertools
import json
import math
import uuid
from pathlib import Path

import numpy as np
from scipy.ndimage import distance_transform_edt
from shapely.geometry import LineString, Point, box
from shapely.ops import unary_union
from shapely.prepared import prep

from hardware.electronics.common.sexpr import a, children, first, read_sexpr, sexpr
from hardware.electronics.rail_disconnect.revision26 import router as aid
from hardware.electronics.rail_disconnect.revision28.receiver_surface_path import connect
from hardware.electronics.rail_disconnect.revision28.repair import Router

from .route_e28 import WORK, sha

STEP=.05


def shape(g):
    if g["kind"]=="line":
        return LineString([g["start"],g["end"]]).buffer(g["width"]/2)
    if g["kind"]=="via":
        return Point(g["xy"]).buffer(g["radius"])
    x,y=g["xy"]
    w,h=g["size"]
    return box(x-w/2,y-h/2,x+w/2,y+h/2)


def run():
    source=WORK/"generated/eight-layer-routes/rail_disconnect.kicad_pcb"
    graph=WORK/"generated/eight-routing-inputs/components.json"
    out=WORK/"generated/eight-layer-followup"
    out.mkdir(exist_ok=False)
    tree=read_sexpr(source.read_text())
    count,frozen=len(tree),sexpr(tree)
    # Surface geometry keeps its original six-layer indices in this private
    # planning copy. Only F/B escapes and newly created In3 tracks are copied.
    virtual=copy.deepcopy(tree)
    new_tracks=[n for n in children(virtual,"segment") if first(n,"layer")[1] in ("In3.Cu","In4.Cu")]
    virtual[:]=[n for n in virtual if n not in new_tracks]
    mapping={"In5.Cu":"In3.Cu","In6.Cu":"In4.Cu"}

    def rename(node):
        for i,value in enumerate(node):
            if isinstance(value,list):
                rename(value)
            elif value in mapping:
                node[i]=mapping[value]

    rename(virtual)
    vcount=len(virtual)
    aid.STEP=STEP
    rt=Router(virtual)
    nx,ny=round(156/STEP)+1,round(54.5/STEP)+1
    xx,yy=np.arange(nx)[:,None]*STEP,np.arange(ny)[None,:]*STEP
    names={str(n[1]):str(n[2]).lstrip("/") for n in children(virtual,"net")}
    editable={str(first(n,"uuid")[1]):names[str(first(n,"net")[1])]
              for kind in ("segment","via") for n in children(virtual,kind)}
    # Retain the actual added-layer traces as drill obstacles. They have no
    # F/B surface extent in the six-layer planning view.
    for node in new_tracks:
        rt.geometry.append(dict(kind="line",net=names[str(first(node,"net")[1])],layers=(99,),
            start=tuple(float(v)-100 for v in first(node,"start")[1:3]),
            end=tuple(float(v)-100 for v in first(node,"end")[1:3]),width=float(first(node,"width")[1])))

    def mask(net,width=.2):
        edge=.52+width/2
        blocked=((xx<edge)|(xx>156-edge)|(yy<edge)|(yy>54.5-edge)
                 |((xx<5+edge)&(yy>35-edge))|((xx>154.5-edge)&(yy>35.25-edge)))
        obstacles=[g for g in rt.geometry if g["net"]!=net and
                   ((g["kind"]=="via" and len(g["layers"])==6) or g.get("through")
                    or (g["kind"]=="rect" and len(g["layers"])==6))]
        # Only new In3 traces exist on the added layer; old In3 is now In5.
        obstacles += [dict(kind="line",start=p,end=q,width=r["width_mm"],net=r["net"])
                      for r in rt.routes if r["layer"]=="In4.Cu" and r["net"]!=net
                      for p,q in zip(r["points_relative_mm"],r["points_relative_mm"][1:]) if p!=q]
        for g in obstacles:
            poly=shape(g).buffer(.2+width/2+.012)
            x0,y0,x1,y1=poly.bounds
            ix0,ix1=max(0,math.floor(x0/STEP)),min(nx,math.ceil(x1/STEP)+1)
            iy0,iy1=max(0,math.floor(y0/STEP)),min(ny,math.ceil(y1/STEP)+1)
            if ix0>=ix1 or iy0>=iy1:
                continue
            x,y=xx[ix0:ix1],yy[:,iy0:iy1]
            extra=.2+width/2+.012
            if g["kind"]=="via":
                hit=(x-g["xy"][0])**2+(y-g["xy"][1])**2<=(g["radius"]+extra)**2
            elif g["kind"]=="rect":
                hit=np.maximum(abs(x-g["xy"][0])-g["size"][0]/2,0)**2+np.maximum(abs(y-g["xy"][1])-g["size"][1]/2,0)**2<=extra**2
            else:
                p,q=g["start"],g["end"]
                dx,dy=q[0]-p[0],q[1]-p[1]
                t=np.clip(((x-p[0])*dx+(y-p[1])*dy)/max(dx*dx+dy*dy,1e-30),0,1)
                hit=(x-p[0]-t*dx)**2+(y-p[1]-t*dy)**2<=(g["width"]/2+extra)**2
            blocked[ix0:ix1,iy0:iy1]|=hit
        return blocked

    escapes=[]

    def access(net,group):
        points=[]
        for obj in group:
            if obj["kind"]=="PCB_VIA" and editable.get(obj["uuid"])==net:
                points.append(obj["position_mm"])
            elif obj["kind"]=="PAD":
                p=next((p for p in rt.by_ref[obj["ref"]] if p["pin"]==obj["pin"]),None)
                if p and p["through"]:
                    points.append(p["xy"])
        if points:
            return points
        pad_objects=[p for p in group if p["kind"]=="PAD"]
        if not pad_objects:
            return []
        free=~mask(net,width=.6)
        foreign=prep(unary_union([shape(g) for g in rt.geometry if
            g["net"]!=net or g.get("through") or g["kind"]=="via"]).buffer(.512))
        for obj in pad_objects:
            pad=next(p for p in rt.by_ref[obj["ref"]] if p["pin"]==obj["pin"])
            x,y=pad["xy"]
            choices=[]
            for ix in range(max(17,round((x-5)/.1)),min(1552,round((x+5)/.1))+1):
                for iy in range(max(17,round((y-5)/.1)),min(536,round((y+5)/.1))+1):
                    xy=(round(ix*.1,6),round(iy*.1,6))
                    if not free[round(xy[0]/STEP),round(xy[1]/STEP)] or foreign.intersects(Point(xy)):
                        continue
                    choices.append((math.dist(pad["xy"],xy),xy))
            goals=[]
            for _,xy in sorted(choices):
                if all(math.dist(xy,p["xy"])>=.5 for p in goals):
                    goals.append(dict(xy=xy,net=net,layers=list(range(6))))
                if len(goals)==100:
                    break
            result,reason=connect(rt,pad,goals,radius=5,step=.025,budget=200000)
            aid.STEP=STEP
            escapes.append(dict(net=net,ref=obj["ref"],pin=obj["pin"],connected=bool(result),reason=reason,result=result))
            if result:
                xy=result["target"]["xy"]
                rt.via(net,xy)
                return [xy]
        return []

    def join(net,starts,goals):
        if not starts or not goals:
            return dict(connected=False,reason="surface_access_missing")
        width=1. if net=="P19" else .2
        blocked=mask(net,width)
        sources={(round(x/STEP),round(y/STEP)):(x,y) for x,y in starts}
        targets={(round(x/STEP),round(y/STEP)):(x,y) for x,y in goals}
        for p in sources.keys()|targets.keys():
            blocked[p]=False
        distance=np.ones(blocked.shape,bool)
        for p in targets:
            distance[p]=False
        heuristic=distance_transform_edt(distance)
        serial=itertools.count()
        queue=[(1.5*heuristic[p],next(serial),p) for p in sources]
        heapq.heapify(queue)
        costs=dict.fromkeys(sources,0.)
        previous,visited={},set()
        found=None
        while queue:
            _,_,p=heapq.heappop(queue)
            if p in visited:
                continue
            visited.add(p)
            if len(visited)>1000000:
                break
            if p in targets:
                found=p
                break
            for dx,dy in ((1,0),(-1,0),(0,1),(0,-1),(1,1),(1,-1),(-1,1),(-1,-1)):
                q=(p[0]+dx,p[1]+dy)
                if not (0<=q[0]<nx and 0<=q[1]<ny) or blocked[q]:
                    continue
                cost=costs[p]+math.hypot(dx,dy)
                if cost<costs.get(q,float("inf")):
                    costs[q]=cost
                    previous[q]=p
                    heapq.heappush(queue,(cost+1.5*heuristic[q],next(serial),q))
        if found is None:
            return dict(connected=False,visited=len(visited),reason="no_path_or_budget")
        nodes=[found]
        while nodes[-1] in previous:
            nodes.append(previous[nodes[-1]])
        nodes.reverse()
        points=[sources[nodes[0]],(nodes[0][0]*STEP,nodes[0][1]*STEP)]
        direction=None
        for p,q in zip(nodes,nodes[1:]):
            delta=(q[0]-p[0],q[1]-p[1])
            if delta!=direction:
                points.append((p[0]*STEP,p[1]*STEP))
                direction=delta
        points.extend([(found[0]*STEP,found[1]*STEP),targets[found]])
        rt.path(net,4,points,width)
        return dict(connected=True,visited=len(visited))

    inventory=json.loads(graph.read_text())
    tasks=[]
    for net,row in inventory["inventory"].items():
        groups=[access(net,g) for g in row["components"]]
        tasks.append((net,groups))
    results=[]
    for net,groups in tasks:
        joined=groups[0]
        for group in groups[1:]:
            result=join(net,joined,group)
            results.append(dict(net=net,**result))
            print(net,result.get("connected"),result.get("visited"),result.get("reason"),flush=True)
            if result.get("connected"):
                joined+=group
    assert sexpr(tree[:count])==frozen
    for index,node in enumerate(virtual[vcount:]):
        assert node[0] in ("segment","via")
        if not children(node,"uuid"):
            node.append([a("uuid"),a(str(uuid.uuid5(uuid.NAMESPACE_URL,f"rmx:AX03:8layer:{sha(source)}:{index}:{sexpr(node)}")))])
        tree.append(node)
    pcb=out/source.name
    pcb.write_text(sexpr(tree)+"\n")
    (out/"routes.json").write_text(json.dumps(dict(source_sha256=sha(source),candidate_sha256=sha(pcb),
        recipe_sha256=sha(Path(__file__)),original_inventory_sha256=sha(graph),results=results,escapes=escapes,
        routes=rt.routes,all_original_XY_copper_and_footprints_preserved=True,
        new_logic_layer="In4.Cu",new_layer_copper_nominal_mm=.035,
        C50_filled_capped_process_receiving_required=True,force_cuts_from_new_drills_require_review=True,
        native_checks_pending=True,physical_qualified=False,fabrication_released=False),indent=2)+"\n")


if __name__=="__main__":
    run()
