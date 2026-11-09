"""Short opposite-face logic routes with conventional all-layer-screened vias.

This constructor adds copper only. Full native DRC and an independent geometry,
connection and drill/SMD audit are required before selecting its output.
"""
import json
import math
import shutil
import uuid
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path
from shapely.geometry import LineString, Point
from shapely.strtree import STRtree
from hardware.electronics.common.sexpr import a, children, read_sexpr, sexpr
from hardware.fabrication.integrate_two_board_signal import REPO, STAGING, sha
import hardware.fabrication.route_nf_surface as routing
from hardware.fabrication.route_two_board_power_local_v2 import MountScreen

BASE=STAGING/'two-board-power-routed-native-04'
CAP=STAGING/'two-board-power-routing-inputs-2619/capture.json'
OUT=STAGING/'two-board-power-vias-01'


def run():
    assert not OUT.exists()
    cap=json.loads(CAP.read_text())
    for name,h in cap['source_sha256'].items():assert sha(Path(name))==h,name
    assert not cap['zones']
    pcb=read_sexpr((BASE/'power_protection.kicad_pcb').read_text());count=len(pcb);original=sexpr(pcb)
    codes={str(n[2]):int(n[1]) for n in children(pcb,'net')}
    allowed={}
    for net in ET.parse(BASE/'netlist.xml').findall('./nets/net'):
        name=net.attrib['name'];nodes=[n.attrib for n in net.findall('node')];types={n.get('pintype') for n in nodes}
        if name in cap['open_nets'] and routing.is_logic_net(name) and types&{'output','open_collector'} and not types&{'power_in','power_out'}:
            allowed[name]=nodes
    routing.SIGNAL_LAYERS=('F.Cu','B.Cu');routing.WIDTH=.2
    screen=MountScreen(cap)
    copper=[(o,routing.shape(ps)) for o in cap['objects'] for ps in o['layers'].values() if ps]
    copper_tree=STRtree([g for o,g in copper])
    smd=[routing.shape(ps) for o in cap['objects'] if o['kind']=='PAD' and not any(o['drill_mm'])
        for layer,ps in o['layers'].items() if layer in routing.SIGNAL_LAYERS and ps]
    smd_tree=STRtree(smd)
    holes=[]
    for o in cap['objects']:
        drill=o.get('drill_mm',0)
        radius=max(drill)/2 if isinstance(drill,list) else drill/2
        if radius:holes.append((o['position_mm'],radius))
    outline=routing.shape(cap['outline']).buffer(-.81)
    vias=[]
    def via_ok(net,xy):
        pt=Point(xy)
        if not outline.covers(pt):return False
        if any(pt.distance(center)<=radius+.31 for ref,center,radius in screen.mounts):return False
        # Via edge to foreign copper >= .21mm on every layer, including inner.
        for i in copper_tree.query(pt.buffer(.52)):
            other,g=copper[int(i)]
            if other['net']!=net and pt.distance(g)<=.51:return False
        # No via-in-pad, including same-net lands: copper disc stays .01mm away.
        if any(pt.distance(smd[int(i)])<=.31 for i in smd_tree.query(pt.buffer(.32))):return False
        # All existing plated/NPTH drills; slots use a conservative bounding disc.
        if any(math.dist(xy,p)<=.15+r+.26 for p,r in holes):return False
        if any(math.dist(xy,v['position_mm'])<=(.56 if v['net']==net else .81) for v in vias):return False
        if any(other!=net and pt.distance(g)<=.61 for other,layer,g in screen.added):return False
        return True
    def path_for(net,layer,start,end,limit):
        choices=[]
        for path in routing.candidate_paths(start,end):
            path=[p for i,p in enumerate(path) if i==0 or p!=path[i-1]]
            if len(path)<2:continue
            length=LineString(path).length
            if length<=limit and screen.legal(net,layer,path):choices.append((length,path))
        return min(choices,key=lambda c:c[0]) if choices else None
    pads=defaultdict(list);objects={o['uuid']:o for o in cap['objects']}
    for o in objects.values():
        if o['kind']=='PAD' and o.get('pin') and o['net'] in allowed:pads[o['net']].append(o)
    parent={k:k for k in cap['groups']}
    def root(k):
        while parent[k]!=k:parent[k]=parent[parent[k]];k=parent[k]
        return k
    tasks=[]
    for net,items in pads.items():
        for i,p in enumerate(items):
            for q in items[i+1:]:
                pl=set(p['layers'])&set(routing.SIGNAL_LAYERS);ql=set(q['layers'])&set(routing.SIGNAL_LAYERS)
                d=math.dist(p['position_mm'],q['position_mm'])
                if p['group']!=q['group'] and pl and ql and not pl&ql and d<=20:
                    tasks.append((d,net,p['uuid'],q['uuid'],next(iter(pl)),next(iter(ql))))
    routes=[];deferred=[];digest=sha(CAP)
    for d,net,pu,qu,pl,ql in sorted(tasks):
        p,q=objects[pu],objects[qu]
        if root(p['group'])==root(q['group']):continue
        start,end=tuple(p['position_mm']),tuple(q['position_mm']);limit=min(30,1.7*d+3)
        # Half-mm grid spanning both endpoint neighborhoods and their corridor.
        sites=[]
        for ix in range(math.floor((min(start[0],end[0])-3)*2),math.ceil((max(start[0],end[0])+3)*2)+1):
            for iy in range(math.floor((min(start[1],end[1])-3)*2),math.ceil((max(start[1],end[1])+3)*2)+1):
                xy=(ix/2,iy/2);lower=math.dist(start,xy)+math.dist(end,xy)
                if lower<=limit:sites.append((lower,xy))
        selected=None;tested=0
        for lower,xy in sorted(sites):
            if selected and lower>=selected[0]:break
            if not via_ok(net,xy):continue
            tested+=1
            left=path_for(net,pl,start,xy,limit);right=path_for(net,ql,xy,end,limit)
            if left and right and left[0]+right[0]<=limit:
                choice=(left[0]+right[0],[(pl,left[1]),(ql,right[1])],xy)
                if not selected or choice[0]<selected[0]:selected=choice
            if tested>=300:break
        endpoints=[[p['ref'],p['pin']],[q['ref'],q['pin']]]
        if selected is None:
            deferred.append(dict(net=net,endpoints=endpoints,legal_via_sites_tested=tested,reason='No bounded one-via route cleared all screens'))
            print('Deferred',net,endpoints,tested,flush=True);continue
        length,paths,xy=selected;declared=[]
        for layer,path in paths:
            ids=[]
            for pt,qt in zip(path,path[1:]):
                uid=str(uuid.uuid5(uuid.NAMESPACE_URL,f'AFX:TBPV01:{digest}:{net}:{layer}:{pt}:{qt}'))
                pcb.append([a('segment'),[a('start'),*pt],[a('end'),*qt],[a('width'),.2],[a('layer'),layer],[a('net'),codes[net]],[a('uuid'),uid]])
                ids.append(uid)
            declared.append(dict(layer=layer,path_mm=path,segment_uuids=ids));screen.added.append((net,layer,LineString(path)))
        uid=str(uuid.uuid5(uuid.NAMESPACE_URL,f'AFX:TBPV01:via:{digest}:{net}:{xy}'))
        pcb.append([a('via'),[a('at'),*xy],[a('size'),.6],[a('drill'),.3],[a('layers'),'F.Cu','B.Cu'],[a('net'),codes[net]],[a('uuid'),uid]])
        v=dict(uuid=uid,net=net,position_mm=xy);vias.append(v)
        # Screen.added uses track centreline clearance .41; buffer .20 gives
        # the required .61 centre-to-centre distance for a .60mm via and track.
        for layer in routing.SIGNAL_LAYERS:screen.added.append((net,layer,Point(xy).buffer(.2)))
        parent[root(q['group'])]=root(p['group'])
        routes.append(dict(net=net,endpoints=endpoints,endpoint_pad_uuids=[pu,qu],paths=declared,via=v,length_mm=length,
            legal_via_sites_tested=tested,source_groups=[p['group'],q['group']]))
        print('Routed',net,endpoints,round(length,3),'mm',flush=True)
    assert routes and sexpr(pcb[:count])==original
    shutil.copytree(STAGING/'two-board-power-integration-10',OUT)
    dest=OUT/'power_protection.kicad_pcb';dest.write_text(sexpr(pcb)+'\n')
    inputs=[Path(__file__),CAP,BASE/'power_protection.kicad_pcb',BASE/'netlist.xml',BASE/'additive-audit.json',
        *[REPO/'hardware/fabrication'/n for n in ['route_nf_surface.py','route_two_board_power_local_v2.py','route_two_board_power_local.py']]]
    record=dict(source_sha256={str(p.relative_to(REPO)):sha(p) for p in inputs},candidate_PCB_sha256=sha(dest),
        selected_control_net_nodes=allowed,routes=routes,deferred=deferred,
        added_segments=sum(len(p['segment_uuids']) for r in routes for p in r['paths']),added_vias=len(vias),
        existing_authored_geometry_exact=True,all_new_tracks_on_outer_layers=True,
        via_size_drill_mm=[.6,.3],screened_copper_clearance_mm=.21,screened_hole_clearance_mm=.26,
        screened_via_copper_to_SMD_copper_mm=.01,minimum_via_drill_edge_to_SMD_copper_mm=.16,
        mount_reserves_mm='max(3.6, hole radius + .5); additional .01mm margin',
        maximum_endpoint_distance_mm=20,maximum_total_track_length_mm=30,
        native_validation_pending=True,loaded_timing_noise_and_return_review_complete=False,fabrication_released=False)
    (OUT/'via-routing.json').write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps(dict(routes=len(routes),nets=len({r['net'] for r in routes}),segments=record['added_segments'],vias=len(vias),deferred=len(deferred))))


if __name__=='__main__':run()
