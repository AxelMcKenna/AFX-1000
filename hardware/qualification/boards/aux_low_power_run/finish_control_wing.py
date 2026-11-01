"""One bounded In4 reference-link attempt and local control-wing ground pour.

Use native pad polygons, all foreign barrels, existing In4 tracks, actual outline
and track keepouts. No new drills or changes to existing copper/poses are made.
Native refill/DRC and return continuity extraction remain authoritative.
"""

import argparse
import copy
import heapq
import itertools
import json
import math
import uuid
from pathlib import Path

import numpy as np
from scipy.ndimage import distance_transform_edt
from shapely import contains_xy
from shapely.geometry import LineString, Point, Polygon
from shapely.ops import polygonize, unary_union
from shapely.prepared import prep

from hardware.electronics.common.sexpr import a, children, first, read_sexpr, sexpr

from .route_e28 import WORK, sha

STEP=.1
NET="REF_LOW_OK"


def run():
    parser=argparse.ArgumentParser()
    parser.add_argument("--label",default="control-wing-return-smoothed")
    args=parser.parse_args()
    assert args.label and all(c.isalnum() or c in "-_" for c in args.label)
    source=WORK/"generated/control-wing-routes/rail_disconnect.kicad_pcb"
    evidence=WORK/"generated/native-control-wing-routes/review.json"
    graph=WORK/"generated/control-wing-routing-inputs/components.json"
    pads=WORK/"generated/control-wing-routing-inputs/pads.json"
    inputs=json.loads(graph.read_text())
    assert json.loads(evidence.read_text())["uncapped_missing_connections"]==9
    assert json.loads(evidence.read_text())["source_sha256"][str(source)]==sha(source)
    out=WORK/"generated"/args.label
    out.mkdir(exist_ok=False)
    tree=read_sexpr(source.read_text())
    count,frozen=len(tree),sexpr(tree)
    names={str(n[1]):str(n[2]).lstrip("/") for n in children(tree,"net")}
    codes={v:k for k,v in names.items()}
    objects={str(first(n,"uuid")[1]):n for kind in ("segment","via") for n in children(tree,kind)}
    group=next(g for g in inputs["inventory"][NET]["components"] if any(p.get("ref")=="U10" for p in g))
    goals=[]
    for obj in group:
        if obj["kind"]!="PCB_VIA":
            continue
        via=objects[obj["uuid"]]
        xy=tuple(float(v)-100 for v in first(via,"at")[1:3])
        assert names[str(first(via,"net")[1])]==NET and math.dist(xy,obj["position_mm"])<1e-6
        goals.append(xy)
    start=(64.9,56.)
    assert any(names[str(first(v,"net")[1])]==NET and math.dist(start,tuple(float(x)-100 for x in first(v,"at")[1:3]))<1e-6 for v in children(tree,"via"))
    edge=[LineString([tuple(float(v)-100 for v in first(n,k)[1:3]) for k in ("start","end")])
          for n in children(tree,"gr_line") if first(n,"layer")[1]=="Edge.Cuts"]
    outlines=list(polygonize(edge))
    assert len(outlines)==1
    outline=outlines[0]
    nx,ny=1561,601
    xx,yy=np.arange(nx)[:,None]*STEP,np.arange(ny)[None,:]*STEP
    blocked=~contains_xy(outline.buffer(-.62),xx,yy)
    obstacles=[]
    for n in children(tree,"via"):
        if names[str(first(n,"net")[1])]!=NET:
            obstacles.append(Point(*(float(v)-100 for v in first(n,"at")[1:3])).buffer(float(first(n,"size")[1])/2))
    for n in children(tree,"segment"):
        if first(n,"layer")[1]=="In4.Cu" and names[str(first(n,"net")[1])]!=NET:
            obstacles.append(LineString([tuple(float(v)-100 for v in first(n,k)[1:3]) for k in ("start","end")]).buffer(float(first(n,"width")[1])/2))
    for row in json.loads(pads.read_text())["pad_polygons"]:
        if row["net"]==NET:
            continue
        for poly in row["layers"].get("In4.Cu",[]):
            obstacles.append(Polygon([(x-100,y-100) for x,y in poly["outer"]],
                [[(x-100,y-100) for x,y in hole] for hole in poly["holes"]]))
    for zone in children(tree,"zone"):
        if not children(zone,"keepout"):
            continue
        layers=first(zone,"layers")[1:] if children(zone,"layers") else first(zone,"layer")[1:]
        if "*.Cu" not in layers and "In4.Cu" not in layers:
            continue
        if first(first(zone,"keepout"),"tracks")[1]=="not_allowed":
            obstacles.append(Polygon([tuple(float(v)-100 for v in p[1:3]) for p in first(first(zone,"polygon"),"pts")[1:]]))
    for poly in obstacles:
        grown=poly.buffer(.312)
        x0,y0,x1,y1=grown.bounds
        a0,a1=max(0,math.floor(x0/STEP)),min(nx,math.ceil(x1/STEP)+1)
        b0,b1=max(0,math.floor(y0/STEP)),min(ny,math.ceil(y1/STEP)+1)
        if a0<a1 and b0<b1:
            blocked[a0:a1,b0:b1]|=contains_xy(grown,xx[a0:a1],yy[:,b0:b1])
    targets={(round(x/STEP),round(y/STEP)):(x,y) for x,y in goals}
    targets={k:v for k,v in targets.items() if not blocked[k]}
    origin=tuple(round(v/STEP) for v in start)
    assert not blocked[origin] and targets
    distance=np.ones(blocked.shape,bool)
    for k in targets:
        distance[k]=False
    heuristic=distance_transform_edt(distance)
    serial=itertools.count()
    queue=[(1.8*heuristic[origin],next(serial),origin)]
    costs={origin:0.}
    previous,visited={},set()
    found=None
    while queue:
        _,_,p=heapq.heappop(queue)
        if p in visited:
            continue
        visited.add(p)
        if len(visited)>600000:
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
                heapq.heappush(queue,(cost+1.8*heuristic[q],next(serial),q))
    result=dict(connected=False,visited=len(visited),search_node_budget=600000)
    if found is not None:
        nodes=[found]
        while nodes[-1]!=origin:
            nodes.append(previous[nodes[-1]])
        nodes.reverse()
        points=[start]
        direction=None
        for p,q in zip(nodes,nodes[1:]):
            delta=(q[0]-p[0],q[1]-p[1])
            if delta!=direction:
                points.append((p[0]*STEP,p[1]*STEP))
                direction=delta
        points.extend([(found[0]*STEP,found[1]*STEP),targets[found]])
        points=[p for i,p in enumerate(points) if not i or p!=points[i-1]]
        foreign=unary_union(obstacles)
        raw_length=LineString(points).length
        raw_segments=len(points)-1
        free=prep(outline.buffer(-.62).difference(foreign.buffer(.312)))
        smooth=[points[0]]
        i=0
        while i<len(points)-1:
            for j in range(len(points)-1,i,-1):
                if free.covers(LineString([points[i],points[j]])):
                    break
            else:
                raise AssertionError("Original path segment lost its guarded clearance")
            smooth.append(points[j])
            i=j
        points=smooth
        path=LineString(points)
        clearance=path.distance(foreign)-.1
        legal=clearance>=.200001 and outline.contains(path.buffer(.1+.5))
        result.update(exact_segment_clearance_mm=clearance,exact_path_legal=legal,
                      raw_length_mm=raw_length,smoothed_length_mm=path.length,
                      raw_segment_count=raw_segments,smoothed_segment_count=len(points)-1)
        if legal:
            for i,(p,q) in enumerate(zip(points,points[1:])):
                uid=uuid.uuid5(uuid.NAMESPACE_URL,f"AX03:wing:In4:{sha(source)}:{i}")
                tree.append(read_sexpr(f'(segment (start {p[0]+100} {p[1]+100}) (end {q[0]+100} {q[1]+100}) (width .2) (layer "In4.Cu") (net {codes[NET]}) (uuid {uid}))'))
            result.update(connected=True,points_relative_mm=points)
    zone=copy.deepcopy(next(z for z in children(tree,"zone") if children(z,"net_name") and first(z,"net_name")[1]=="/AGND"))
    zone[:]=[n for n in zone if not (isinstance(n,list) and n and n[0] in ("filled_polygon","fill_segments"))]
    first(zone,"layer")[1]="In4.Cu"
    first(zone,"uuid")[1]=a(str(uuid.uuid5(uuid.NAMESPACE_URL,f"AX03:wing:return:{sha(source)}")))
    first(zone,"polygon")[:]=read_sexpr('(polygon (pts (xy 105.6 153) (xy 174.4 153) (xy 174.4 159.4) (xy 105.6 159.4)))')
    tree.append(zone)
    assert sexpr(tree[:count])==frozen
    pcb=out/source.name
    pcb.write_text(sexpr(tree)+"\n")
    (out/"return-review.json").write_text(json.dumps(dict(source_sha256={str(p):sha(p) for p in (source,evidence,graph,pads,Path(__file__))},
        candidate_sha256=sha(pcb),reference_link=result,new_layer="In4.Cu",new_drills=0,
        local_AGND_zone_cad_bounds_mm=[105.6,153,174.4,159.4],
        all_existing_copper_and_poses_exact=True,native_refill_and_continuity_check_pending=True,
        return_impedance_and_fault_current_unqualified=True,
        physical_qualified=False,fabrication_released=False),indent=2)+"\n")
    print("In4 reference link",{k:v for k,v in result.items() if k!="points_relative_mm"},"; local AGND pour staged",flush=True)


if __name__=="__main__":
    run()
