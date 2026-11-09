"""Bounded multilayer search with exact via bridges in regions the grid misses."""
import heapq,math,time
import numpy as np
from scipy.ndimage import distance_transform_edt
from shapely import contains_xy
from shapely.geometry import LineString,Point
from shapely.ops import unary_union
from hardware.fabrication.nf_pin_escape_routes import raster,STEP,WIDTH
import hardware.fabrication.route_nf_surface as surface

LAYERS=('In2.Cu','In3.Cu','B.Cu','F.Cu')

from hardware.fabrication.digital_via_spacing_v2 import via_mask
from hardware.fabrication.digital_continuous_via_bridges import bridges


def route_multi(screen,net,starts,ends,deadline,max_visits=400000):
    masks=[];safe=[]
    for layer in LAYERS:
        xs,ys,coarse=raster(screen,net,layer);safe.append(coarse)
        xx,yy=np.meshgrid(xs,ys)
        obstacles=[g.buffer(d+.000001) for n,g,d in screen.geometry[layer] if n!=net]
        obstacles += [g.buffer(WIDTH+surface.CLEARANCE+surface.MARGIN+.000001) for n,l,g in screen.added if l==layer and n!=net]
        obstacles += [Point(p).buffer(.3+WIDTH/2+.2+.01+.000001) for n,p in screen.new_vias if n!=net]
        valid=contains_xy(screen.outline,xx,yy)
        if obstacles:valid &= ~contains_xy(unary_union(obstacles),xx,yy)
        masks.append(valid)
    h,w=masks[0].shape;size=h*w;free=np.stack(masks).reshape(-1);safe=np.stack(safe).reshape(-1);edge_cache={}
    vm=via_mask(screen,net,xs,ys).ravel()
    extra,bridge_points=bridges(screen,net,xs,ys,LAYERS,free,vm,min(deadline,time.monotonic()+15))
    if bridge_points:print('Continuous via bridges',len(bridge_points),flush=True)
    def point(pos):return (round(float(xs[pos%w]),6),round(float(ys[pos//w]),6))
    def portals(rows,layer_index):
        result={};layer=LAYERS[layer_index]
        for row in rows:
            if layer not in row.get('layers',LAYERS):continue
            x,y=row['point'];ix=round((x-xs[0])/STEP);iy=round((y-ys[0])/STEP)
            for dx in range(-2,3):
                for dy in range(-2,3):
                    xx,yy=ix+dx,iy+dy
                    if not (0<=xx<w and 0<=yy<h):continue
                    pos=yy*w+xx;k=layer_index*size+pos
                    if not free[k]:continue
                    p=point(pos);dist=math.dist(row['point'],p)
                    if dist>1e-7 and not screen.legal(net,layer,[row['point'],p]):continue
                    cost=row['cost']+dist
                    if k not in result or result[k][0]>cost:result[k]=(cost,row)
        return result
    origins={};goals={}
    for li,layer in enumerate(LAYERS):origins.update(portals(starts,li));goals.update(portals(ends.get(layer,[]),li))
    if not origins or not goals:print('No legal portals',len(origins),len(goals),flush=True);return None
    gm=np.ones(size,dtype=bool)
    for k in goals:gm[k%size]=False
    heuristic=distance_transform_edt(gm.reshape(h,w)).ravel()*STEP*1.0
    for retry in range(3):
        distances=np.full(len(free),np.inf);parents=np.full(len(free),-1,dtype=np.int32)
        queue=[];parent_bridge={}
        for k,(cost,row) in origins.items():distances[k]=cost;heapq.heappush(queue,(cost+heuristic[k%size],cost,k))
        best=math.inf;found=None;visits=0
        while queue:
            est,cost,k=heapq.heappop(queue)
            if est>=best:break
            if cost>distances[k]+1e-9:continue
            if visits%1024==0 and (time.monotonic()>deadline or visits>=max_visits):print('Search bound',visits,'deadline',time.monotonic()>deadline,flush=True);return None
            visits+=1;pos=k%size;li=k//size;x,y=pos%w,pos//w
            if k in goals:
                found=k;break
            neighbors=[]
            for dx,dy in ((-1,0),(1,0),(0,-1),(0,1),(-1,-1),(-1,1),(1,-1),(1,1)):
                xx,yy=x+dx,y+dy
                if 0<=xx<w and 0<=yy<h:neighbors.append((li*size+yy*w+xx,math.sqrt(2)*STEP if dx and dy else STEP,None))
            if vm[pos]:neighbors += [(i*size+pos,2.5,None) for i in range(len(LAYERS)) if i!=li]
            neighbors += extra.get(k,[])
            for other,stepcost,bridge in neighbors:
                if not free[other]:continue
                if other//size==li and not(safe[k] and safe[other]):
                    edge=(min(k,other),max(k,other))
                    if edge not in edge_cache:edge_cache[edge]=screen.legal(net,LAYERS[li],[point(pos),point(other%size)])
                    if not edge_cache[edge]:continue
                nc=cost+stepcost
                if nc+1e-9>=distances[other]:continue
                distances[other]=nc;parents[other]=k
                if bridge is None:parent_bridge.pop(other,None)
                else:parent_bridge[other]=bridge
                heapq.heappush(queue,(nc+heuristic[other%size],nc,other))
        if found is None:print('Exhausted search',visits,flush=True);return None
        chain=[found];k=found
        while parents[k]>=0:k=int(parents[k]);chain.append(k)
        chain.reverse();start=origins[chain[0]][1];end=goals[found][1]
        runs=[];vias=list(start['vias'])+list(end['vias'])
        for k in chain:
            layer=LAYERS[k//size];p=point(k%size)
            if k in parent_bridge:
                via=parent_bridge[k]
                if runs[-1][1][-1]!=via:runs[-1][1].append(via)
                runs.append((layer,[via]))
                if p!=via:runs[-1][1].append(p)
                vias.append(via)
            elif not runs or runs[-1][0]!=layer:
                if runs:
                    assert runs[-1][1][-1]==p;vias.append(p)
                runs.append((layer,[p]))
            elif p!=runs[-1][1][-1]:runs[-1][1].append(p)
        runs[0][1].insert(0,start['point']);runs[-1][1].append(end['point'])
        simple=[]
        for layer,points in runs:
            points=[p for i,p in enumerate(points) if i==0 or p!=points[i-1]]
            if len(points)<2:continue
            corners=[points[0]]
            for i in range(1,len(points)-1):
                u,v,z=points[i-1:i+2]
                if abs((v[0]-u[0])*(z[1]-v[1])-(v[1]-u[1])*(z[0]-v[0]))>1e-8:corners.append(v)
            corners.append(points[-1]);pts=[corners[0]];i=0
            while i<len(corners)-1:
                target=i+1
                for j in range(min(len(corners)-1,i+100),i+1,-1):
                    if screen.legal(net,layer,[corners[i],corners[j]]):target=j;break
                pts.append(corners[target]);i=target
            if not screen.legal(net,layer,pts):print('Final segment check failed',layer,flush=True);return None
            simple.append((layer,pts))
        vias=sorted(set(tuple(p) for p in vias))
        bad=[p for p in vias if not screen.via_legal(net,p)]
        bad += [q for i,p in enumerate(vias) for q in vias[i+1:] if math.dist(p,q)<=.563]
        if not bad:
            return dict(runs=start['runs']+simple+end['runs'],vias=vias,groups=[start['group'],end['group']],portals=[start['point'],end['point']],search_visits=visits,continuous_via_bridge_candidates=len(bridge_points),layer_transition_count=len(runs)-1)
        print('Conflicting path vias',bad,flush=True)
        # Disable conflicting grid portals, then retry within the same deadline.
        xx,yy=np.meshgrid(xs,ys)
        for p in bad:
            vm[((xx-p[0])**2+(yy-p[1])**2).ravel()<=.564**2]=False
            extra={k:[r for r in rows if math.dist(r[2],p)>.564] for k,rows in extra.items()}
    return None
