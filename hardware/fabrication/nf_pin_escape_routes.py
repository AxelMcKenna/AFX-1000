"""Additive logic routing with explicit fanouts and conservative raster paths.

Host planning only. Every resulting segment is screened against native-captured
geometry; independent native DRC/ERC, refill and connectivity audits are required.
"""
import argparse
import hashlib
import heapq
import json
import math
import time
import uuid
from pathlib import Path

import numpy as np
from shapely import contains_xy
from shapely.geometry import LineString, Point
from shapely.ops import unary_union

import hardware.fabrication.route_nf_surface as surface
import hardware.fabrication.nf_minimum_logic as routing
from hardware.fabrication.nf_softstart_joint_screen import ExistingViaScreen
from hardware.electronics.common.sexpr import a, first, read_sexpr, sexpr

ROOT=Path(__file__).resolve().parent
STEP=.1
# Every grid edge is at most sqrt(2)*STEP. Expanding by half that distance
# makes an edge safe when both endpoints are outside all expanded obstacles.
RASTER_MARGIN=math.sqrt(2)*STEP/2+.002
INNER=('In2.Cu','In3.Cu','B.Cu')
WIDTH=.16

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def fanouts(screen,pad,limit=32):
    net=pad['net']; start=tuple(pad['position_mm']); layer=next(iter(pad['layers']))
    choices=[]
    for x in range(round((start[0]-4)/.2),round((start[0]+4)/.2)+1):
        for y in range(round((start[1]-4)/.2),round((start[1]+4)/.2)+1):
            pt=(round(x*.2,6),round(y*.2,6))
            if math.dist(start,pt)>4 or not screen.via_legal(net,pt): continue
            best=None
            for path in surface.candidate_paths(start,pt):
                path=[p for i,p in enumerate(path) if i==0 or p!=path[i-1]]
                if screen.legal(net,layer,path):
                    length=LineString(path).length
                    if best is None or length<best[0]: best=(length,path)
            if best: choices.append(dict(point=pt,runs=[(layer,best[1])],vias=[pt],cost=best[0],group=pad['group'],pad=[pad['ref'],pad['pin']]))
    # Keep spatially different portals, rather than many adjacent grid points.
    picked=[]
    for row in sorted(choices,key=lambda x:x['cost']):
        if all(math.dist(row['point'],p['point'])>=.39 for p in picked): picked.append(row)
        if len(picked)>=limit:break
    return picked


def raster(screen,net,layer):
    xmin,ymin,xmax,ymax=screen.outline.bounds
    xs=np.arange(math.floor(xmin/STEP),math.ceil(xmax/STEP)+1)*STEP
    ys=np.arange(math.floor(ymin/STEP),math.ceil(ymax/STEP)+1)*STEP
    xx,yy=np.meshgrid(xs,ys)
    obstacles=[g.buffer(d+RASTER_MARGIN) for n,g,d in screen.geometry[layer] if n!=net]
    obstacles += [g.buffer(WIDTH+surface.CLEARANCE+surface.MARGIN+RASTER_MARGIN) for n,l,g in screen.added if l==layer and n!=net]
    obstacles += [Point(p).buffer(.3+WIDTH/2+.2+.01+RASTER_MARGIN) for n,p in screen.new_vias if n!=net]
    valid=contains_xy(screen.outline.buffer(-RASTER_MARGIN),xx,yy)
    if obstacles:valid &= ~contains_xy(unary_union(obstacles),xx,yy)
    return xs,ys,valid


def route_layer(screen,net,layer,starts,ends,deadline):
    xs,ys,valid=raster(screen,net,layer); height,width=valid.shape
    def point(k):return (round(float(xs[k%width]),6),round(float(ys[k//width]),6))
    def portals(rows):
        result={}
        for row in rows:
            x,y=row['point']; ix=round((x-xs[0])/STEP);iy=round((y-ys[0])/STEP)
            for dx in range(-2,3):
                for dy in range(-2,3):
                    xx,yy=ix+dx,iy+dy
                    if not (0<=xx<width and 0<=yy<height and valid[yy,xx]):continue
                    k=yy*width+xx;p=point(k);dist=math.dist(row['point'],p)
                    if dist>1e-7 and not screen.legal(net,layer,[row['point'],p]):continue
                    cost=row['cost']+dist
                    if k not in result or result[k][0]>cost: result[k]=(cost,row)
        return result
    origins,goals=portals(starts),portals(ends)
    if not origins or not goals:return None
    gx=[k%width for k in goals];gy=[k//width for k in goals]
    box=(min(gx),max(gx),min(gy),max(gy))
    def heuristic(k):
        x,y=k%width,k//width;dx=max(box[0]-x,0,x-box[1]);dy=max(box[2]-y,0,y-box[3])
        return (max(dx,dy)+(math.sqrt(2)-1)*min(dx,dy))*STEP
    distances={k:v[0] for k,v in origins.items()};parents={};queue=[(v[0]+heuristic(k),v[0],k) for k,v in origins.items()];heapq.heapify(queue)
    best=math.inf;found=None;visits=0
    flat=valid.ravel()
    while queue:
        estimate,cost,k=heapq.heappop(queue)
        if estimate>=best:break
        if cost>distances[k]+1e-9:continue
        if visits%2048==0 and time.monotonic()>deadline:return None
        visits+=1
        if k in goals and cost+goals[k][0]<best:best=cost+goals[k][0];found=k
        x,y=k%width,k//width
        for dx,dy in ((-1,0),(1,0),(0,-1),(0,1),(-1,-1),(-1,1),(1,-1),(1,1)):
            xx,yy=x+dx,y+dy
            if not (0<=xx<width and 0<=yy<height):continue
            other=yy*width+xx
            if not flat[other]:continue
            nc=cost+(math.sqrt(2)*STEP if dx and dy else STEP)
            if nc+1e-9>=distances.get(other,math.inf):continue
            distances[other]=nc;parents[other]=k
            heapq.heappush(queue,(nc+heuristic(other),nc,other))
    if found is None:return None
    chain=[found];k=found
    while k in parents:k=parents[k];chain.append(k)
    chain.reverse();start=origins[chain[0]][1];end=goals[found][1]
    points=[start['point']]+[point(k) for k in chain]+[end['point']]
    points=[p for i,p in enumerate(points) if i==0 or p!=points[i-1]]
    # Linear collinearity reduction followed by bounded, exact shortcuts.
    corners=[points[0]]
    for i in range(1,len(points)-1):
        u,v,w=points[i-1:i+2]
        if abs((v[0]-u[0])*(w[1]-v[1])-(v[1]-u[1])*(w[0]-v[0]))>1e-8:corners.append(v)
    corners.append(points[-1]);simple=[corners[0]];i=0
    while i<len(corners)-1:
        target=i+1
        for j in range(min(len(corners)-1,i+100),i+1,-1):
            if screen.legal(net,layer,[corners[i],corners[j]]):target=j;break
        simple.append(corners[target]);i=target
    assert screen.legal(net,layer,simple),(net,layer,'raster path failed exact check')
    return dict(runs=start['runs']+[(layer,simple)]+end['runs'],vias=start['vias']+end['vias'],groups=[start['group'],end['group']],portals=[start['point'],end['point']],search_visits=visits)


def run():
    ap=argparse.ArgumentParser();ap.add_argument('--label',required=True);ap.add_argument('--pins',default='1,8,9,11,12');ap.add_argument('--seconds',type=int,default=30);args=ap.parse_args()
    assert args.label and all(c.isalnum() or c in '-_' for c in args.label)
    out=ROOT/'staging'/args.label;assert not out.exists()
    capture_path=ROOT/'staging/nf-softstart-cell-inputs-163/capture.json';c=json.loads(capture_path.read_text())
    assert all(sha(p)==d for p,d in c['source_sha256'].items())
    source=next(Path(p) for p in c['source_sha256'] if p.endswith('.kicad_pcb'));board=read_sexpr(source.read_text());original=sexpr(board);count=len(board)
    surface.WIDTH=routing.WIDTH=WIDTH;surface.MARGIN=.001
    screen=ExistingViaScreen(c);routes=[];attempts=[]
    for pin in args.pins.split(','):
        pad=next(o for o in c['objects'] if o.get('ref')=='U44' and o.get('pin')==pin);net=pad['net']
        print('Planning U44.'+pin,net,flush=True)
        starts=fanouts(screen,pad);ends={l:[] for l in INNER}
        others=[o for o in c['objects'] if o['net']==net and o['group']!=pad['group']]
        for obj in others:
            for layer in INNER:
                if layer in obj['layers']:
                    for point in [obj['position_mm']]+([obj['end_mm']] if 'end_mm' in obj else []):
                        ends[layer].append(dict(point=tuple(point),runs=[],vias=[],cost=0,group=obj['group']))
        # Explicit escapes are needed for isolated surface target pads too.
        for obj in others:
            if obj['kind']=='PAD' and obj['group'] and len(c['groups'][obj['group']])==1:
                for portal in fanouts(screen,obj,limit=16):
                    for layer in INNER:ends[layer].append(portal)
        found=None
        for layer in INNER:
            if starts and ends[layer]:found=route_layer(screen,net,layer,starts,ends[layer],time.monotonic()+args.seconds)
            if found:break
        attempts.append(dict(pin=pin,net=net,start_portals=len(starts),end_portals={l:len(e) for l,e in ends.items()},found=bool(found)))
        if not found:print('No route',pin,flush=True);continue
        assert all(screen.legal(net,l,p) for l,p in found['runs'])
        vias=sorted(set(tuple(p) for p in found['vias']))
        assert all(screen.via_legal(net,p) for p in vias)
        assert all(math.dist(p,q)>.86 for i,p in enumerate(vias) for q in vias[i+1:])
        for layer,points in found['runs']:
            screen.added.append((net,layer,LineString(points)))
            for p,q in zip(points,points[1:]):
                if math.dist(p,q)<1e-7:continue
                uid=str(uuid.uuid5(uuid.NAMESPACE_URL,f'AFX:NF:pin-escape:{sha(capture_path)}:{net}:{layer}:{p}:{q}'))
                board.append([a('segment'),[a('start'),*p],[a('end'),*q],[a('width'),WIDTH],[a('layer'),layer],[a('net'),net],[a('uuid'),uid]])
        for p in vias:
            uid=str(uuid.uuid5(uuid.NAMESPACE_URL,f'AFX:NF:pin-escape-via:{sha(capture_path)}:{net}:{p}'))
            board.append([a('via'),[a('at'),*p],[a('size'),.6],[a('drill'),.3],[a('layers'),'F.Cu','B.Cu'],[a('tenting'),[a('front'),a('yes')],[a('back'),a('yes')]],[a('net'),net],[a('uuid'),uid]])
            screen.new_vias.append((net,p))
        found.update(net=net,pin=pin,new_vias_mm=vias,planar_length_mm=sum(LineString(p).length for l,p in found['runs']));routes.append(found)
        print('Planned',pin,layer,round(found['planar_length_mm'],3),'mm',len(vias),'vias',flush=True)
    assert sexpr(board[:count])==original
    out.mkdir();pcb=out/source.name;pcb.write_text(sexpr(board)+'\n')
    inputs=[source,capture_path,Path(__file__),ROOT/'route_nf_surface.py',ROOT/'nf_minimum_logic.py',ROOT/'nf_softstart_joint_screen.py',ROOT/'nf_softstart_cell_routes.py']
    (out/'construction.json').write_text(json.dumps(dict(source_sha256={str(p):sha(p) for p in inputs},candidate_PCB_sha256=sha(pcb),routes=routes,attempts=attempts,route_count=len(routes),all_original_objects_exact=True,new_width_mm=WIDTH,new_via_mm=[.6,.3],reserved_planes_have_no_new_tracks=True,raster_step_mm=STEP,raster_extra_margin_mm=RASTER_MARGIN,native_checks_pending=True,physical_qualified=False,fabrication_released=False),indent=2)+'\n')
    print('Finished',len(routes),'routes',flush=True)

if __name__=='__main__':run()
