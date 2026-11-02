"""Bounded DC02 supply/return escapes and wide exposed-pad copper branches.

All original geometry is retained. Native connectivity and refill are required;
these geometric screens do not qualify current capacity or thermal performance.
"""
import json
import math
import uuid
from pathlib import Path
from shapely.geometry import Point, LineString
from shapely.strtree import STRtree
from hardware.electronics.common.sexpr import a, children, read_sexpr, sexpr
from hardware.fabrication.audit_candidate import sha
from hardware.fabrication.route_nf_surface import shape, candidate_paths

ROOT = Path(__file__).resolve().parent

def run():
    cp = ROOT/'staging/digital-plane-inputs-384/capture.json'
    c = json.loads(cp.read_text())
    assert all(sha(Path(p)) == h for p,h in c['source_sha256'].items())
    source = next(Path(p) for p in c['source_sha256'] if p.endswith('.kicad_pcb'))
    b = read_sexpr(source.read_text()); original,count = sexpr(b),len(b)
    outline = shape(c['outline'])
    planes = {z['net']:(z['layer'],shape(z['polygons'])) for z in c['zones']}
    objs = {o['uuid']:o for o in c['objects']}
    pads = {(o['ref'],o['pin']):o for o in c['objects'] if o['kind']=='PAD' and o.get('pin')}
    copper = [(o,l,shape(ps)) for o in c['objects'] for l,ps in o['layers'].items() if ps]
    index = STRtree([g for o,l,g in copper])
    smd = [g for o,l,g in copper if o['kind']=='PAD' and not any(o['drill_mm']) and l in ['F.Cu','B.Cu']]
    smd_index = STRtree(smd)
    drills = [(o['position_mm'],max(o['drill_mm'])/2) for o in c['objects'] if o['kind']=='PAD' and any(o['drill_mm'])]
    drills += [(o['position_mm'],.15) for o in c['objects'] if o['kind']=='PCB_VIA']
    tracks,vias,results,deferred = [],[],[],[]
    def legal(net,face,path,width):
        line = LineString(path)
        if line.length<1e-7 or not outline.buffer(-(.51+width/2)).covers(line):return False
        for i in index.query(line.buffer(width/2+.4)):
            o,l,g = copper[int(i)]
            if l==face and o['net']!=net and line.distance(g)<=width/2+.211:return False
        if any(line.distance(Point(xy))<=r+width/2+.261 for xy,r in drills
               if any(o.get('npth') and o['position_mm']==xy for o in c['objects'])):return False
        for n,l,g,w in tracks:
            if n!=net and l==face and line.distance(g)<=width/2+w/2+.211:return False
        return all(n==net or line.distance(Point(xy))>width/2+.511 for n,xy in vias)
    def via_ok(net,xy):
        p=Point(xy)
        if not outline.buffer(-.81).covers(p) or not planes[net][1].covers(p.buffer(.3)):return False
        for i in index.query(p.buffer(.52)):
            o,l,g=copper[int(i)]
            if o['net']!=net and p.distance(g)<.511:return False
        if any(p.distance(smd[int(i)])<.301 for i in smd_index.query(p.buffer(.302))):return False
        if any(math.dist(xy,q)<r+.15+.261 for q,r in drills):return False
        if any(math.dist(xy,q)<(.611 if n==net else .811) for n,q in vias):return False
        return all(n==net or p.distance(g)>.3+w/2+.211 for n,l,g,w in tracks)
    def add(net,face,path,width,xy,owner):
        for p,q in zip(path,path[1:]):
            ident=str(uuid.uuid5(uuid.NAMESPACE_URL,f'AFX:DC:escape:{sha(cp)}:{net}:{face}:{p}:{q}:{width}'))
            b.append([a('segment'),[a('start'),*p],[a('end'),*q],[a('width'),width],[a('layer'),face],[a('net'),net],[a('uuid'),ident]])
        ident=str(uuid.uuid5(uuid.NAMESPACE_URL,f'AFX:DC:escapevia:{sha(cp)}:{net}:{xy}'))
        b.append([a('via'),[a('at'),*xy],[a('size'),.6],[a('drill'),.3],[a('layers'),'F.Cu','B.Cu'],[a('net'),net],[a('uuid'),ident]])
        tracks.append((net,face,LineString(path),width));vias.append((net,xy))
        results.append(dict(owner=owner,net=net,face=face,points_mm=path,width_mm=width,via_mm=xy,via_uuid=ident))
    thermal_groups=set()
    for ref in ['U3001','U3002','U3003','U3004']:
        ep=pads[(ref,'33')];cx,cy=ep['position_mm'];accepted=0
        for dy in [-6.,6.]:
            for dx in [-1.6,0.,1.6]:
                end=(cx+dx,cy+dy);start=(cx+dx,cy+math.copysign(5.,dy))
                if via_ok('AGND',end) and legal('AGND','F.Cu',[start,end],1.):
                    add('AGND','F.Cu',[start,end],1.,end,dict(ref=ref,pin='33',thermal_branch=True));accepted+=1
        if accepted:thermal_groups.add(ep['group'])
        if accepted<6:deferred.append(dict(ref=ref,pin='33',thermal_sites_accepted=accepted,thermal_sites_requested=6))
    offsets=sorted((math.hypot(dx,dy),dx*.1,dy*.1) for dx in range(-30,31) for dy in range(-30,31) if 4<=math.hypot(dx,dy)<=30)
    for key,ids in c['groups'].items():
        net=objs[ids[0]]['net']
        if net not in planes or key in thermal_groups:continue
        layer,plane=planes[net]
        if any(layer in objs[i]['layers'] and shape(objs[i]['layers'][layer]).intersection(plane).area>1e-8 for i in ids):continue
        contacts=[objs[i] for i in ids if objs[i]['kind']=='PAD' and objs[i].get('pin')]
        contacts.sort(key=lambda o:(not o['ref'].startswith('C'),o['ref'],o['pin']))
        chosen=None
        for p in contacts:
            if p['pin']=='33' and p['ref'] in ['U3001','U3002','U3003','U3004']:continue
            face=next((l for l in ['F.Cu','B.Cu'] if l in p['layers']),None)
            if not face:continue
            start=tuple(p['position_mm']);width=.3
            if p['ref'].startswith('U'):width=.25
            if p['ref']=='R1001':width=1.
            if p['ref'] in ['C3013','C3014','C3002','C3004','C3006','C3008','C2004']:width=.5
            for _,dx,dy in offsets:
                xy=(round(start[0]+dx,6),round(start[1]+dy,6))
                if not via_ok(net,xy):continue
                for path in candidate_paths(start,xy):
                    path=[v for i,v in enumerate(path) if not i or v!=path[i-1]]
                    if sum(math.dist(v,w) for v,w in zip(path,path[1:]))>3.5:continue
                    if legal(net,face,path,width):chosen=(p,face,path,width,xy);break
                if chosen:break
            if chosen:break
        if chosen:
            p,face,path,width,xy=chosen
            add(net,face,path,width,xy,dict(ref=p['ref'],pin=p['pin'],native_source_group=key))
        else:deferred.append(dict(group=key,net=net,contacts=[(p['ref'],p['pin']) for p in contacts],reason='No bounded escape passing geometric screens'))
    assert sexpr(b[:count])==original
    out=ROOT/'staging/digital-plane-escapes-01';out.mkdir(exist_ok=False);dest=out/source.name
    dest.write_text(sexpr(b)+'\n')
    (out/'construction.json').write_text(json.dumps(dict(source_sha256={str(p):sha(p) for p in [source,cp,Path(__file__),ROOT/'route_nf_surface.py']},
        candidate_PCB_sha256=sha(dest),routes=results,deferred=deferred,added_vias=len(vias),
        added_segments=len(children(b,'segment'))-len(children(read_sexpr(original),'segment')),
        original_authored_geometry_exact=True,native_checks_pending=True,
        minimum_screened_hole_edge_to_SMD_copper_mm=.151,thermal_current_capacity_and_process_qualified=False,
        fabrication_released=False),indent=2)+'\n')
    print('Escapes',len(results),'deferred',len(deferred),flush=True)

if __name__=='__main__':run()
