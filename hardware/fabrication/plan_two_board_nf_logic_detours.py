"""Add bounded, referenced layer detours to the startup surface plan."""
import itertools
import json
import math
from pathlib import Path
from shapely.geometry import LineString, Point, Polygon
from shapely.ops import unary_union
from shapely.prepared import prep
from hardware.fabrication.integrate_two_board_signal import REPO, STAGING, sha
from hardware.fabrication.plan_two_board_startup_controls import anchored_fields
BASE=STAGING/'two-board-power-nf-logic-routes-native-01'
CAP=STAGING/'two-board-power-routing-inputs-nf-logic-routes-01/capture.json'
from hardware.fabrication.route_two_board_power_layer_detours import ViaScreen
import hardware.fabrication.route_nf_surface as routing

PLAN=STAGING/'two-board-nf-logic-route-plan-02/plan.json'
OUT=STAGING/'two-board-nf-logic-detour-plan-01'


def run():
    assert not OUT.exists()
    c=json.loads(CAP.read_text());p=json.loads(PLAN.read_text())
    for data in [c,p]:
        for n,h in data['source_sha256'].items():assert sha(Path(n) if Path(n).is_absolute() else REPO/n)==h,n
    audit_path=BASE/'nf-logic-review.json'
    audit=json.loads(audit_path.read_text())
    assert audit['closed_connections']==6 and audit['all_other_native_groups_preserved']
    for name,h in audit['source_sha256'].items():assert sha(REPO/name)==h,name
    fields,excluded=anchored_fields(c)
    objects={o['uuid']:o for o in c['objects']}
    main=next(o['group'] for o in c['objects'] if o.get('ref')=='P_C103' and o.get('pin')=='2')
    reference={'F.Cu':'In1.Cu','In2.Cu':'In1.Cu'}
    holes={}
    for o in c['objects']:
        if o['kind']=='PCB_VIA':holes.setdefault(o['net'],[]).append(Point(o['position_mm']).buffer(o['width_mm']/2+.215))
    holes={n:unary_union(v) for n,v in holes.items()}
    protected={l:[] for l in c['copper_layers']};retained=[]
    for o in c['objects']:
        if o['kind']!='PCB_TRACK' or o['net']=='PWR_AGND':continue
        layer,=o['layers'];i=c['copper_layers'].index(layer)
        adjacent={c['copper_layers'][j] for j in [i-1,i+1] if 0<=j<len(c['copper_layers'])}
        band=LineString([o['position_mm'],o['end_mm']]).buffer(o['width_mm']/2).difference(holes.get(o['net'],Polygon()))
        if band.is_empty:continue
        for (l,gid),f in fields.items():
            if l in adjacent and band.difference(f.buffer(.0015)).area<1e-6:
                protected[l].append(band);retained.append(dict(track_uuid=o['uuid'],reference_layer=l,ground_group=gid))
    # Inflate once, then use prepared fields for the many exact route screens.
    protected_lines={l:prep(unary_union(v).buffer(.435)) for l,v in protected.items()}
    protected_vias=prep(unary_union([x for v in protected.values() for x in v]).buffer(.64))
    existing_fields={l:fields[r,main].buffer(.0015) for l,r in reference.items()}
    cache={};newreferences=[]
    def routefield(net,layer):
        key=(net,layer)
        if key not in cache:cache[key]=prep(existing_fields[layer].union(holes.get(net,Polygon())).buffer(-.100001))
        return cache[key]
    supply={l:unary_union([routing.shape(z['polygons']) for z in c['zones'] if z['layer']==l and z['net']!='PWR_AGND']) for l in c['copper_layers']}
    all_supply=prep(unary_union(list(supply.values())).buffer(.55))
    supply_lines={l:prep(supply[l].buffer(.315)) for l in reference}
    quietpaths=[STAGING/'two-board-power-digital-startup-native-02/digital-startup-routing.json',STAGING/'two-board-power-analog-cells-native-03/analog-cell-routing.json']
    quietids={u for f in quietpaths for q in json.loads(f.read_text())['quiet_ground_islands'] for u in q['zone_uuids']}
    quiet=prep(unary_union([routing.shape(z['authored_outline']).buffer(.55) for z in c['zones'] if z['uuid'] in quietids]))
    routing.SIGNAL_LAYERS=tuple(reference);routing.WIDTH=.2
    class ReferencedViaScreen(ViaScreen):
        def legal(self,net,layer,points):
            line=LineString(points)
            if supply_lines[layer].intersects(line) or quiet.intersects(line):return False
            if not routefield(net,layer).covers(line) or protected_lines[layer].intersects(line):return False
            if any(n!=net and l==layer and line.distance(band)<=.435 for n,l,band in newreferences):return False
            return super().legal(net,layer,points)
        def via_legal(self,net,xy):
            point=Point(xy)
            if all_supply.intersects(point) or quiet.intersects(point):return False
            if protected_vias.intersects(point):return False
            if any(n!=net and point.distance(band)<=.64 for n,l,band in newreferences):return False
            return super().via_legal(net,xy)
    assert not any(z['keepout'] for z in c['zones'])
    screen=ReferencedViaScreen(dict(c,zones=[]));routes=[];vias=[]
    for r in routes:
        line=LineString(r['path_mm']);screen.added.append((r['net'],r['layer'],line))
        newreferences.append((r['net'],r['reference_layer'],line.buffer(.1)))
    groups={};contacts={}
    for gid,members in c['groups'].items():
        net=objects[members[0]]['net']
        if net not in p['selected_nets']:continue
        groups.setdefault(net,[]).append(gid);pts=set()
        for u in members:
            o=objects[u]
            for layer in set(o['layers'])&{'F.Cu'}:
                for xy in [o['position_mm']]+([o['end_mm']] if 'end_mm' in o else []):pts.add((layer,tuple(xy)))
        contacts[gid]=pts
    parent={g:g for g in contacts}
    def root(g):
        while parent[g]!=g:parent[g]=parent[parent[g]];g=parent[g]
        return g
    for r in routes:
        a,b=r['source_groups'];parent[root(b)]=root(a)
    tasks=[]
    for net,gs in groups.items():
        for a,b in itertools.combinations(gs,2):
            options=sorted((math.dist(x,y),l,x,m,y) for l,x in contacts[a] for m,y in contacts[b] if 1e-6<math.dist(x,y)<=100)
            if options:tasks.append((options[0][0],net,a,b,options[:6]))
    joins=[dict(net=r['net'],source_groups=r['source_groups']) for r in routes];deferred=[]
    for d,net,a,b,options in sorted(tasks):
        if root(a)==root(b):continue
        best=None;escapes={};grid=[]
        for distance,l,x,m,y in options:
            # Reject endpoints outside the currently anchored return field.
            if not routefield(net,l).covers(Point(x)) or not routefield(net,m).covers(Point(y)):continue
            for layer,pt in [(l,x),(m,y)]:
                if (layer,pt) not in escapes:escapes[layer,pt]=screen.escapes(net,layer,pt)[:6]
            limit=min(130,1.8*distance+8)
            pairs=sorted((ea[0]+math.dist(ea[1],eb[1])+eb[0],ea,eb)
                         for ea in escapes[l,x] for eb in escapes[m,y] if math.dist(ea[1],eb[1])>.81)
            for lower,ea,eb in pairs:
                if lower>limit or best and lower>=best[0]:continue
                for middlelayer in ['In2.Cu']:
                    middle=screen.simple(net,middlelayer,ea[1],eb[1],limit-ea[0]-eb[0])
                    if middle:
                        length=ea[0]+middle[0]+eb[0]
                        if best is None or length<best[0]:best=(length,[(l,ea[2]),(middlelayer,middle[1]),(m,list(reversed(eb[2])))],[ea[1],eb[1]])
                    elif distance<=50:grid.append((lower,limit,l,m,middlelayer,ea,eb))
        if best is None:
            for lower,limit,l,m,middlelayer,ea,eb in sorted(grid)[:4]:
                path=screen.grid_path(net,middlelayer,ea[1],eb[1],budget=6000)
                if path and ea[0]+LineString(path).length+eb[0]<=limit:
                    best=(ea[0]+LineString(path).length+eb[0],[(l,ea[2]),(middlelayer,path),(m,list(reversed(eb[2])))],[ea[1],eb[1]]);break
        if best is None:
            deferred.append(dict(net=net,source_groups=[a,b],nearest_mm=d))
            print('Deferred',net,round(d,2),flush=True);continue
        length,paths,positions=best
        for layer,path in paths:
            routes.append(dict(net=net,layer=layer,path_mm=path,width_mm=.2,reference_layer=reference[layer],ground_group=main))
            line=LineString(path);screen.added.append((net,layer,line))
            newreferences.append((net,reference[layer],line.buffer(.1)))
        for xy in positions:
            vias.append(dict(net=net,position_mm=xy,size_mm=.6,drill_mm=.3))
            screen.vias.append((net,xy))
            for layer in routing.SIGNAL_LAYERS:screen.added.append((net,layer,Point(xy).buffer(.2)))
        parent[root(b)]=root(a);joins.append(dict(net=net,source_groups=[a,b],length_mm=length))
        print('Joined',net,round(length,3),'2 vias',flush=True)
    sources=[Path(__file__),CAP,PLAN,audit_path,*quietpaths,BASE/'netlist.xml',REPO/'hardware/fabrication/plan_two_board_startup_controls.py',REPO/'hardware/fabrication/route_two_board_power_layer_detours.py',REPO/'hardware/fabrication/route_two_board_power_local_v2.py',REPO/'hardware/fabrication/route_nf_surface.py']
    result=dict(source_sha256={str(s.relative_to(REPO)):sha(s) for s in sources},routes=routes,vias=vias,joins=joins,
        expected_closed_connections=len(joins),deferred_pairs=deferred,retained_reference_bands=retained,
        excluded_unanchored_fragments=excluded,selected_nets=p['selected_nets'],
        reference_transitions=[dict(net=v['net'],position_mm=v['position_mm'],reference_layers=['In1.Cu'],same_reference_plane=True) for v in vias],
        detour_scope='Front-to-In2-to-front with common In1 ground reference; supply copper and quiet-ground outlines excluded.',
        native_validation_pending=True,fabrication_released=False)
    OUT.mkdir();(OUT/'plan.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(joins=len(joins),paths=len(routes),vias=len(vias),retained_references=len(retained),deferred_pairs=len(deferred))))


if __name__=='__main__':run()
