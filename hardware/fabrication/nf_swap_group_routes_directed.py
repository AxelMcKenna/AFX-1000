"""Join affected native connectivity groups after the explicit logic-site swap.

Existing group contacts and vias are reused. Fine pin escapes are generated only
when a group has no inner-layer access. Every addition still needs native review.
"""
import argparse,json,math,time,uuid
from pathlib import Path
from shapely.geometry import LineString,Point
from hardware.electronics.common.sexpr import a,read_sexpr,sexpr
from hardware.fabrication.nf_extended_fanout_routes import fanouts
from hardware.fabrication.nf_multilayer_raster_directed import route_multi,LAYERS
from hardware.fabrication.nf_softstart_joint_screen import ExistingViaScreen
from hardware.fabrication.audit_candidate import sha
import hardware.fabrication.route_nf_surface as surface
import hardware.fabrication.nf_minimum_logic as routing

ROOT=Path(__file__).resolve().parent
WIDTH=.16

def run():
    ap=argparse.ArgumentParser();ap.add_argument('--capture',required=True);ap.add_argument('--label',required=True);ap.add_argument('--seconds',type=int,default=300);ap.add_argument('--max-joins',type=int,default=32);ap.add_argument('--nets',default='');args=ap.parse_args()
    assert all(v and all(c.isalnum() or c in '-_' for c in v) for v in [args.capture,args.label]);assert 30<=args.seconds<=600 and 1<=args.max_joins<=48
    cp=ROOT/'staging'/args.capture/'capture.json';c=json.loads(cp.read_text());assert all(sha(Path(p))==h for p,h in c['source_sha256'].items())
    source=next(Path(p) for p in c['source_sha256'] if p.endswith('.kicad_pcb'));board=read_sexpr(source.read_text());original=sexpr(board);original_len=len(board)
    prep=ROOT/'staging/nf-logic-swap-prepared-01/construction.json';allowed=set(json.loads(prep.read_text())['affected_nets']);assert not allowed&{'/AGND','/AUX2V6'}
    if args.nets:
        requested=set(args.nets.split(','));assert requested<=allowed;allowed=requested
    surface.WIDTH=routing.WIDTH=WIDTH;surface.MARGIN=.001;screen=ExistingViaScreen(c)
    objects={o['uuid']:o for o in c['objects']};groups={g:[objects[u] for u in ids] for g,ids in c['groups'].items() if objects[ids[0]]['net'] in allowed}
    parent={g:g for g in groups};net_of={g:os[0]['net'] for g,os in groups.items()};contacts={};new_contacts={g:[] for g in groups};fanout_cache={};route_rows=[];attempts=[];failed=set();started=time.monotonic();deadline=started+args.seconds
    polygons={(o['uuid'],l):surface.shape(p) for os in groups.values() for o in os for l,p in o['layers'].items() if l in LAYERS}
    def root(g):
        while parent[g]!=g:parent[g]=parent[parent[g]];g=parent[g]
        return g
    def members(g):return [k for k in groups if root(k)==root(g)]
    def native_contacts(g):
        rows=[]
        for k in members(g):
            for o in groups[k]:
                for layer in o['layers']:
                    if layer not in LAYERS:continue
                    for pt in [o['position_mm']]+([o['end_mm']] if 'end_mm' in o else []):rows.append(dict(point=tuple(pt),layers=[layer],runs=[],vias=[],cost=0,group=root(g)))
            for row in new_contacts[k]:rows.append(dict(row,group=root(g)))
        unique={}
        for r in rows:
            key=r['point'];unique.setdefault(key,dict(r,layers=[]))['layers']+=r['layers']
        for row in unique.values():row['layers']=sorted(set(row['layers']))
        return list(unique.values())
    def portals(g,other_rows):
        rows=native_contacts(g);net=net_of[g]
        if not any(set(r['layers'])&{'In2.Cu','In3.Cu'} for r in rows):
            pads=[o for k in members(g) for o in groups[k] if o['kind']=='PAD' and len(o['layers'])==1]
            for pad in pads:
                key=pad['uuid']
                if key not in fanout_cache:fanout_cache[key]=fanouts(screen,pad,limit=16)
                for p in fanout_cache[key]:
                    if all(screen.via_legal(net,xy) for xy in p['vias']) and all(screen.legal(net,l,pts) for l,pts in p['runs']):rows.append(dict(p,group=root(g),layers=list(LAYERS)))
        if len(rows)>120:
            points=[r['point'] for r in other_rows]
            rows=sorted(rows,key=lambda r:min(math.dist(r['point'],p) for p in points)+r['cost'])[:120]
        return rows
    while time.monotonic()<deadline and len(route_rows)<args.max_joins:
        roots=sorted({root(g) for g in groups});pairs=[];base={g:native_contacts(g) for g in roots}
        for i,left in enumerate(roots):
            for right in roots[i+1:]:
                if net_of[left]!=net_of[right]:continue
                key=(tuple(sorted(members(left))),tuple(sorted(members(right))))
                if key in failed:continue
                distance=min(math.dist(p['point'],q['point']) for p in base[left] for q in base[right])
                pairs.append((distance,net_of[left],left,right,key))
        if not pairs:break
        distance,net,left,right,key=min(pairs);print('Planning groups',net,'gap',round(distance,2),flush=True)
        starts=portals(left,base[right]);targets=portals(right,base[left]);ends={l:[r for r in targets if l in r['layers']] for l in LAYERS}
        found=None
        direct=[]
        for p in starts:
            for q in targets:
                for layer in set(p['layers'])&set(q['layers']):direct.append((math.dist(p['point'],q['point'])+p['cost']+q['cost'],layer,p,q))
        for cost,layer,p,q in sorted(direct,key=lambda r:r[0])[:24]:
            if cost>distance*1.35+5:continue
            for points in surface.candidate_paths(p['point'],q['point']):
                points=[v for i,v in enumerate(points) if i==0 or v!=points[i-1]]
                if len(points)>1 and screen.legal(net,layer,points):
                    found=dict(runs=p['runs']+[(layer,points)]+q['runs'],vias=p['vias']+q['vias'],groups=[left,right],search_visits=0);break
            if found:break
        if not found and time.monotonic()<deadline:found=route_multi(screen,net,starts,ends,min(deadline,time.monotonic()+120),max_visits=1600000)
        if not found:
            failed.add(key);attempts.append(dict(net=net,groups=[left,right],start_portals=len(starts),end_portals=len(targets),found=False));print('No group route',net,flush=True);continue
        runs=found['runs'];assert all(screen.legal(net,l,p) for l,p in runs)
        fresh=[]
        for point in sorted(set(tuple(p) for p in found['vias'])):
            if any(n==net and math.dist(point,p)<1e-7 for n,p in screen.vias+screen.new_vias):continue
            used_layers={l for l,points in runs if LineString(points).distance(Point(point))<1e-7}
            if len(used_layers)<2:continue
            fresh.append(point)
        if not all(screen.via_legal(net,p) for p in fresh) or any(math.dist(p,q)<=.86 for i,p in enumerate(fresh) for q in fresh[i+1:]):
            failed.add(key);attempts.append(dict(net=net,groups=[left,right],found=False,reason='prospective via conflict'));continue
        joined={root(left),root(right)}
        for g,os in groups.items():
            if net_of[g]!=net:continue
            if any(any((o['uuid'],l) in polygons and LineString(points).distance(polygons[o['uuid'],l])<=WIDTH/2+.000001 for l,points in runs) or any(Point(pt).distance(polygons[o['uuid'],l])<=.3+.000001 for pt in fresh for l in o['layers'] if (o['uuid'],l) in polygons) for o in os):joined.add(root(g))
        for g in joined:parent[root(g)]=root(left)
        group=root(left)
        for layer,points in runs:
            screen.added.append((net,layer,LineString(points)))
            for p,q in zip(points,points[1:]):
                if math.dist(p,q)<1e-7:continue
                uid=str(uuid.uuid5(uuid.NAMESPACE_URL,f'AFX:NF:swap-groups:{sha(cp)}:{net}:{layer}:{p}:{q}'))
                board.append([a('segment'),[a('start'),*p],[a('end'),*q],[a('width'),WIDTH],[a('layer'),layer],[a('net'),net],[a('uuid'),uid]])
            new_contacts[group]+=[dict(point=tuple(p),layers=[layer],runs=[],vias=[],cost=0,group=group) for p in [points[0],points[-1]]]
        for pt in fresh:
            uid=str(uuid.uuid5(uuid.NAMESPACE_URL,f'AFX:NF:swap-group-via:{sha(cp)}:{net}:{pt}'))
            board.append([a('via'),[a('at'),*pt],[a('size'),.6],[a('drill'),.3],[a('layers'),'F.Cu','B.Cu'],[a('tenting'),[a('front'),a('yes')],[a('back'),a('yes')]],[a('net'),net],[a('uuid'),uid]])
            screen.new_vias.append((net,pt));new_contacts[group].append(dict(point=pt,layers=list(LAYERS),runs=[],vias=[],cost=0,group=group))
        route_rows.append(dict(net=net,groups=[left,right],joined_roots=sorted(joined),runs=runs,new_vias_mm=fresh,planar_length_mm=sum(LineString(p).length for l,p in runs),search_visits=found['search_visits']))
        attempts.append(dict(net=net,groups=[left,right],found=True));print('Joined',net,'groups',len(joined),'vias',len(fresh),'length',round(route_rows[-1]['planar_length_mm'],2),flush=True)
    assert sexpr(board[:original_len])==original
    out=ROOT/'staging'/args.label;out.mkdir(exist_ok=False);pcb=out/source.name;pcb.write_text(sexpr(board)+'\n')
    inputs=[source,cp,prep,Path(__file__),*[ROOT/n for n in ['nf_connected_fanout_routes.py','nf_extended_fanout_routes.py','nf_pin_escape_routes.py','nf_multilayer_raster.py','nf_multilayer_raster_exact.py','nf_multilayer_raster_guided.py','nf_multilayer_raster_directed.py','nf_softstart_joint_screen.py','nf_softstart_cell_routes.py','nf_minimum_logic.py','route_nf_surface.py']]]
    (out/'construction.json').write_text(json.dumps(dict(source_sha256={str(p):sha(p) for p in inputs},candidate_PCB_sha256=sha(pcb),routes=route_rows,attempts=attempts,allowed_nets=sorted(allowed),all_original_objects_exact=True,new_signal_width_mm=WIDTH,new_via_mm=[.6,.3],elapsed_seconds=time.monotonic()-started,uncompleted_group_counts={n:len({root(g) for g in groups if net_of[g]==n}) for n in sorted(set(net_of.values()))},native_checks_pending=True,physical_qualified=False,fabrication_released=False),indent=2)+'\n')
    print('Completed',len(route_rows),'group routes',flush=True)

if __name__=='__main__':run()
