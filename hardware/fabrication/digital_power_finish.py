"""Close remaining ground pulls and attempt a wide Seed input supply branch."""
import heapq
import json
import math
import uuid
from pathlib import Path
from shapely.geometry import Point,LineString
from shapely.strtree import STRtree
from hardware.electronics.common.sexpr import a,read_sexpr,sexpr
from hardware.fabrication.audit_candidate import sha
from hardware.fabrication.route_nf_surface import shape,candidate_paths

ROOT=Path(__file__).resolve().parent

class Screen:
    def __init__(self,c):
        self.outline=shape(c['outline']);self.rows={};self.trees={};self.added=[]
        for face in ['F.Cu','B.Cu']:
            rows=[(o['net'],shape(o['layers'][face]),.211) for o in c['objects'] if o['layers'].get(face)]
            rows += [(None,Point(o['position_mm']).buffer(max(o['drill_mm'])/2),.261) for o in c['objects'] if o.get('npth')]
            self.rows[face]=rows;self.trees[face]=STRtree([g for n,g,gap in rows])
    def legal(self,net,face,path,width):
        line=LineString(path)
        if not self.outline.buffer(-(.51+width/2)).covers(line):return False
        for i in self.trees[face].query(line.buffer(width/2+.3)):
            other,g,gap=self.rows[face][int(i)]
            if other!=net and line.distance(g)<=gap+width/2:return False
        return all(n==net or l!=face or line.distance(g)>width/2+w/2+.211 for n,l,g,w in self.added)
    def route(self,net,face,start,end,width):
        paths=[]
        for p in candidate_paths(start,end):
            p=[v for i,v in enumerate(p) if not i or v!=p[i-1]]
            if len(p)>1 and self.legal(net,face,p,width):paths.append(p)
        if paths:return min(paths,key=lambda p:LineString(p).length)
        step=.2;origin=tuple(round(v/step) for v in start);goal=tuple(round(v/step) for v in end)
        def xy(k):return tuple(round(v*step,6) for v in k)
        if not self.legal(net,face,[start,xy(origin)],width) or not self.legal(net,face,[xy(goal),end],width):return None
        queue=[(math.dist(origin,goal),0.,origin)];cost={origin:0.};parent={};cache={};visits=0
        lower=[min(x,y)-40 for x,y in zip(origin,goal)];upper=[max(x,y)+40 for x,y in zip(origin,goal)]
        while queue and visits<25000:
            _,dist,k=heapq.heappop(queue)
            if dist>cost.get(k,math.inf)+1e-8:continue
            visits+=1
            if k==goal:
                keys=[k]
                while k in parent:k=parent[k];keys.append(k)
                path=[start]+[xy(k) for k in reversed(keys)]+[end]
                path=[v for i,v in enumerate(path) if not i or v!=path[i-1]]
                simple=[path[0]];i=0
                while i<len(path)-1:
                    j=i+1
                    for q in range(i+2,len(path)):
                        if self.legal(net,face,[path[i],path[q]],width):j=q
                    simple.append(path[j]);i=j
                return simple
            for dx,dy in [(-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1)]:
                q=(k[0]+dx,k[1]+dy);new=dist+math.hypot(dx,dy)
                if new>=cost.get(q,math.inf) or not all(lo<=v<=hi for lo,v,hi in zip(lower,q,upper)):continue
                key=tuple(sorted((k,q)))
                if key not in cache:cache[key]=self.legal(net,face,[xy(k),xy(q)],width)
                if not cache[key]:continue
                cost[q]=new;parent[q]=k;heapq.heappush(queue,(new+math.dist(q,goal),new,q))
        return None

def run():
    cp=ROOT/'staging/digital-plane-escape-inputs-286/capture.json';c=json.loads(cp.read_text())
    assert all(sha(Path(p))==h for p,h in c['source_sha256'].items())
    source=next(Path(p) for p in c['source_sha256'] if p.endswith('.kicad_pcb'))
    board=read_sexpr(source.read_text());old,count=sexpr(board),len(board)
    screen=Screen(c);pads={(o['ref'],o['pin']):o for o in c['objects'] if o['kind']=='PAD' and o.get('pin')}
    routes=[];deferred=[]
    def add(net,face,path,width,owner):
        for p,q in zip(path,path[1:]):
            ident=str(uuid.uuid5(uuid.NAMESPACE_URL,f'AFX:DC:finish:{sha(cp)}:{net}:{face}:{p}:{q}'))
            board.append([a('segment'),[a('start'),*p],[a('end'),*q],[a('width'),width],[a('layer'),face],[a('net'),net],[a('uuid'),ident]])
        screen.added.append((net,face,LineString(path),width))
        routes.append(dict(net=net,face=face,points_mm=path,width_mm=width,length_mm=LineString(path).length,owner=owner))
    for ref in ['R1005','R2003']:
        p=pads[(ref,'2')];start=tuple(p['position_mm']);targets=sorted([o for o in c['objects'] if o['net']=='AGND' and o['kind']=='PCB_VIA'],key=lambda o:math.dist(start,o['position_mm']))
        for q in targets[:8]:
            end=tuple(q['position_mm']);path=screen.route('AGND','B.Cu',start,end,.25)
            if path:add('AGND','B.Cu',path,.25,dict(ref=ref,pin='2',target_uuid=q['uuid']));break
        else:deferred.append(dict(ref=ref,pin='2'))
    start=tuple(pads[('R1001','2')]['position_mm']);end=tuple(pads[('U1001','39')]['position_mm'])
    path=screen.route('/PROCESSOR/SEED_VIN','B.Cu',start,end,1.)
    if path:add('/PROCESSOR/SEED_VIN','B.Cu',path,1.,dict(ref='R1001',pin='2',target_ref='U1001',target_pin='39'))
    else:deferred.append(dict(ref='R1001',pin='2',reason='No bounded 1 mm surface path to Seed VIN'))
    assert sexpr(board[:count])==old
    out=ROOT/'staging/digital-power-finish-01';out.mkdir(exist_ok=False);dest=out/source.name;dest.write_text(sexpr(board)+'\n')
    (out/'construction.json').write_text(json.dumps(dict(source_sha256={str(p):sha(p) for p in [source,cp,Path(__file__),ROOT/'route_nf_surface.py']},candidate_PCB_sha256=sha(dest),routes=routes,deferred=deferred,original_authored_geometry_exact=True,native_checks_pending=True,fabrication_released=False),indent=2)+'\n')
    print('Power finish',len(routes),'routes; deferred',deferred,flush=True)

if __name__=='__main__':run()
