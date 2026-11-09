"""Plan startup logic joins over anchored return fields, preserving prior fields.

This is a geometric planning screen. Native fill, DRC, connectivity and an
independent return-field audit are mandatory before accepting its copper.
"""
import itertools
import json
import math
import xml.etree.ElementTree as ET
from pathlib import Path
from shapely.geometry import LineString, Point, Polygon
from shapely.ops import unary_union
from shapely.prepared import prep
from shapely.strtree import STRtree
from hardware.fabrication.integrate_two_board_signal import REPO, STAGING, sha
from hardware.fabrication.route_two_board_power_local_v2 import MountScreen
import hardware.fabrication.route_nf_surface as routing

BASE=STAGING/'two-board-power-aux-feedback-native-01'
CAP=STAGING/'two-board-power-routing-inputs-2172-aux-feedback-01/capture.json'
OUT=STAGING/'two-board-startup-control-plan-02'


def anchored_fields(cap):
    fields={};excluded=[]
    for layer in cap['copper_layers']:
        contacts=[(o['group'],routing.shape(o['layers'][layer])) for o in cap['objects']
                  if o['net']=='PWR_AGND' and o['layers'].get(layer)]
        tree=STRtree([g for _,g in contacts])
        for z in cap['zones']:
            if z['net']!='PWR_AGND' or z['layer']!=layer:continue
            for p in z['polygons']:
                g=Polygon(p['outer'],p['holes']);margin=g.buffer(.0015)
                groups={contacts[int(i)][0] for i in tree.query(margin)
                        if margin.intersection(contacts[int(i)][1]).area>1e-9}
                assert len(groups)<=1
                if groups:fields.setdefault((layer,next(iter(groups))),[]).append(g)
                else:excluded.append(dict(zone_uuid=z['uuid'],area_mm2=g.area))
    return {k:unary_union(v) for k,v in fields.items()},excluded


def run():
    assert not OUT.exists()
    cap=json.loads(CAP.read_text())
    for n,h in cap['source_sha256'].items():assert sha(Path(n) if Path(n).is_absolute() else REPO/n)==h,n
    fields,excluded=anchored_fields(cap)
    main=next(o['group'] for o in cap['objects'] if o.get('ref')=='P_C103' and o.get('pin')=='2')
    adjacent={'F.Cu':'In1.Cu','B.Cu':'In6.Cu'}
    returns={layer:fields[(inner,main)] for layer,inner in adjacent.items()}
    # Preserve all previously credited surface return fields for adjacent inner
    # tracks, including isolated grounds. Allow clearance plus half the native
    # minimum plane thickness so refill cannot leave a clipped narrow remnant.
    viaholes={}
    for o in cap['objects']:
        if o['kind']=='PCB_VIA':viaholes.setdefault(o['net'],[]).append(Point(o['position_mm']).buffer(o['width_mm']/2+.215))
    viaholes={n:unary_union(v) for n,v in viaholes.items()}
    protected={layer:[] for layer in adjacent};preserved=[]
    for o in cap['objects']:
        if o['kind']!='PCB_TRACK' or o['net']=='PWR_AGND':continue
        layer,=o['layers']
        for outer,inner in adjacent.items():
            if layer!=inner:continue
            band=LineString([o['position_mm'],o['end_mm']]).buffer(o['width_mm']/2).difference(viaholes.get(o['net'],Polygon()))
            if band.is_empty:continue
            for (fl,gid),field in fields.items():
                if fl==outer and band.difference(field.buffer(.0015)).area<1e-6:
                    protected[outer].append(band.buffer(.435))
                    preserved.append(dict(track_uuid=o['uuid'],reference_layer=outer,ground_group=gid))
    protected={l:unary_union(v) for l,v in protected.items()}
    routing.SIGNAL_LAYERS=('F.Cu','B.Cu');routing.WIDTH=.2
    screen_cap=dict(cap,zones=[z for z in cap['zones'] if z['keepout']])
    reference_cache={}
    def reference(net,layer):
        key=(net,layer)
        if key not in reference_cache:
            reference_cache[key]=prep(returns[layer].buffer(.0015).union(viaholes.get(net,Polygon())).buffer(-.100001))
        return reference_cache[key]
    class ReferencedScreen(MountScreen):
        def legal(self,net,layer,points):
            line=LineString(points)
            if not reference(net,layer).covers(line):return False
            if line.intersects(protected[layer]):return False
            return super().legal(net,layer,points)
    screen=ReferencedScreen(screen_cap)
    allowed={}
    for n in ET.parse(BASE/'netlist.xml').findall('./nets/net'):
        name=n.attrib['name'];nodes=[p.attrib for p in n.findall('node')];types={p.get('pintype') for p in nodes}
        if not ('E28_' in name or name.rsplit('/',1)[-1] in ['ANA_PG','DIG_PG','DIG_PG3_SCHMITT','PWR_ALL_RAILS_ALLOW']):continue
        if name not in cap['open_nets'] or not types&{'output','open_collector'} or types&{'power_in','power_out'}:continue
        if name.endswith(('_SENSE','_CT','_DIV')):continue
        allowed[name]=nodes
    objects={o['uuid']:o for o in cap['objects']};groups={};contacts={}
    for gid,members in cap['groups'].items():
        net=objects[members[0]]['net']
        if net not in allowed:continue
        groups.setdefault(net,[]).append(gid);points=set()
        for u in members:
            o=objects[u]
            for layer in set(o['layers'])&set(adjacent):
                for p in [o['position_mm']]+([o['end_mm']] if 'end_mm' in o else []):points.add((layer,tuple(p)))
        contacts[gid]=points
    parent={g:g for g in contacts}
    def root(g):
        while parent[g]!=g:parent[g]=parent[parent[g]];g=parent[g]
        return g
    tasks=[]
    for net,gs in groups.items():
        for a,b in itertools.combinations(gs,2):
            options=sorted((math.dist(p,q),l,p,q) for l,p in contacts[a] for m,q in contacts[b]
                           if l==m and 1e-6<math.dist(p,q)<=100)
            if options:tasks.append((options[0][0],net,a,b,options[:24]))
    routes=[];deferred=[]
    for d,net,a,b,options in sorted(tasks):
        if root(a)==root(b):continue
        best=None
        for distance,layer,p,q in options:
            for path in routing.candidate_paths(p,q):
                path=[x for i,x in enumerate(path) if not i or x!=path[i-1]]
                if len(path)<2:continue
                length=LineString(path).length
                if length>min(120,1.8*distance+5) or best and length>=best[0]:continue
                if screen.legal(net,layer,path):best=(length,layer,path)
        if best is None and d<=50:
            for distance,layer,p,q in options[:3]:
                if not reference(net,layer).covers(Point(p)) or not reference(net,layer).covers(Point(q)):continue
                path=screen.grid_path(net,layer,p,q,budget=10000)
                if path and LineString(path).length<=min(120,1.8*distance+5):
                    best=(LineString(path).length,layer,path);break
        if best:
            length,layer,path=best;parent[root(b)]=root(a)
            screen.added.append((net,layer,LineString(path)))
            routes.append(dict(net=net,source_groups=[a,b],layer=layer,path_mm=path,width_mm=.2,length_mm=length,reference_layer=adjacent[layer],ground_group=main))
            print('Joined',net,round(length,3),flush=True)
        else:
            deferred.append(dict(net=net,source_groups=[a,b],nearest_mm=d))
            print('Deferred',net,round(d,2),flush=True)
    OUT.mkdir()
    sources=[Path(__file__),CAP,BASE/'netlist.xml',REPO/'hardware/fabrication/route_two_board_power_local_v2.py',REPO/'hardware/fabrication/route_nf_surface.py']
    result=dict(source_sha256={str(p.relative_to(REPO)):sha(p) for p in sources},routes=routes,
        deferred_pairs=deferred,selected_nets=allowed,expected_closed_connections=len(routes),
        prior_surface_reference_bands=preserved,excluded_unanchored_fragments=excluded,
        new_vias=0,track_width_mm=.2,provisional_mount_reserves=15,
        native_validation_pending=True,fabrication_released=False)
    (OUT/'plan.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(routes=len(routes),nets=len({r['net'] for r in routes}),deferred_pairs=len(deferred),protected_reference_bands=len(preserved))))


if __name__=='__main__':run()
