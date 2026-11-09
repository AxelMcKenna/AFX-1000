"""Bounded two-via detours for nearby control groups blocked on one face."""
import itertools
import json
import math
import shutil
import uuid
import xml.etree.ElementTree as ET
from pathlib import Path
from shapely.geometry import LineString, Point
from shapely.strtree import STRtree
from hardware.electronics.common.sexpr import a, children, read_sexpr, sexpr
from hardware.fabrication.integrate_two_board_signal import REPO, STAGING, sha
from hardware.fabrication.route_two_board_power_local_v2 import MountScreen
import hardware.fabrication.route_nf_surface as routing

BASE=STAGING/'two-board-power-routed-native-06'
CAP=STAGING/'two-board-power-routing-inputs-2572/capture.json'
OUT=STAGING/'two-board-power-layer-detours-01'


class ViaScreen(MountScreen):
    def __init__(self,cap):
        super().__init__(cap)
        assert not cap['zones']
        self.copper=[(o['net'],routing.shape(ps)) for o in cap['objects'] for ps in o['layers'].values() if ps]
        self.copper_tree=STRtree([g for n,g in self.copper])
        self.smd=[routing.shape(ps) for o in cap['objects'] if o['kind']=='PAD' and not any(o['drill_mm'])
            for layer,ps in o['layers'].items() if layer in ['F.Cu','B.Cu'] and ps]
        self.smd_tree=STRtree(self.smd)
        self.holes=[];self.vias=[];self.via_outline=routing.shape(cap['outline']).buffer(-.81)
        for o in cap['objects']:
            d=o.get('drill_mm',0);r=max(d)/2 if isinstance(d,list) else d/2
            if r:self.holes.append((o['position_mm'],r))

    def via_legal(self,net,xy):
        pt=Point(xy)
        if not self.via_outline.covers(pt):return False
        if any(pt.distance(p)<=r+.31 for ref,p,r in self.mounts):return False
        for i in self.copper_tree.query(pt.buffer(.52)):
            other,g=self.copper[int(i)]
            if other!=net and pt.distance(g)<=.51:return False
        if any(pt.distance(self.smd[int(i)])<=.31 for i in self.smd_tree.query(pt.buffer(.32))):return False
        if any(math.dist(xy,p)<=.15+r+.26 for p,r in self.holes):return False
        if any(math.dist(xy,p)<=(.56 if other==net else .81) for other,p in self.vias):return False
        if any(other!=net and pt.distance(g)<=.61 for other,layer,g in self.added):return False
        return True

    def simple(self,net,layer,start,end,limit):
        best=None
        for path in routing.candidate_paths(start,end):
            path=[p for i,p in enumerate(path) if not i or p!=path[i-1]]
            if len(path)<2:continue
            length=LineString(path).length
            if length>limit or (best and length>=best[0]):continue
            if self.legal(net,layer,path):best=(length,path)
        return best

    def escapes(self,net,layer,point):
        sites=sorted((math.dist(point,(ix/2,iy/2)),(ix/2,iy/2))
            for ix in range(math.floor((point[0]-3.5)*2),math.ceil((point[0]+3.5)*2)+1)
            for iy in range(math.floor((point[1]-3.5)*2),math.ceil((point[1]+3.5)*2)+1))
        candidates=[];legal=[]
        for distance,xy in sites:
            if distance>3.5 or not self.via_legal(net,xy):continue
            legal.append((distance,xy));path=self.simple(net,layer,point,xy,5.5)
            if path:candidates.append((path[0],xy,path[1]))
            if len(candidates)>=12:break
        if not candidates:
            for distance,xy in legal[:4]:
                path=self.grid_path(net,layer,point,xy,budget=2000)
                if path and LineString(path).length<=5.5:candidates.append((LineString(path).length,xy,path))
        return sorted(candidates)[:12]


def run():
    assert not OUT.exists()
    cap=json.loads(CAP.read_text())
    for name,h in cap['source_sha256'].items():assert sha(Path(name))==h,name
    pcb=read_sexpr((BASE/'power_protection.kicad_pcb').read_text());count=len(pcb);original=sexpr(pcb)
    codes={str(n[2]):int(n[1]) for n in children(pcb,'net')};allowed={}
    for net in ET.parse(BASE/'netlist.xml').findall('./nets/net'):
        name=net.attrib['name'];nodes=[n.attrib for n in net.findall('node')];types={n.get('pintype') for n in nodes}
        if name in cap['open_nets'] and routing.is_logic_net(name) and types&{'output','open_collector'} and not types&{'power_in','power_out'}:allowed[name]=nodes
    routing.SIGNAL_LAYERS=('F.Cu','B.Cu');routing.WIDTH=.2;screen=ViaScreen(cap)
    objects={o['uuid']:o for o in cap['objects']};groups={};contacts={};witness={}
    for key,members in cap['groups'].items():
        net=objects[members[0]]['net']
        if net not in allowed:continue
        groups.setdefault(net,[]).append(key);points=set();pads=[]
        for uid in members:
            o=objects[uid]
            if o['kind']=='PAD' and o.get('pin'):pads.append(uid)
            for layer in set(o['layers'])&set(routing.SIGNAL_LAYERS):
                for xy in [o['position_mm']]+([o['end_mm']] if o.get('end_mm') else []):points.add((layer,tuple(xy)))
        assert pads
        witness[key]=min(pads);contacts[key]=points
    parent={k:k for k in contacts}
    def root(k):
        while parent[k]!=k:parent[k]=parent[parent[k]];k=parent[k]
        return k
    tasks=[]
    for net,keys in groups.items():
        for left,right in itertools.combinations(keys,2):
            options=sorted((math.dist(p,q),layer,p,q) for layer,p in contacts[left] for other,q in contacts[right]
                if layer==other and 1e-6<math.dist(p,q)<=20)
            if options:tasks.append((options[0][0],net,left,right,options[:6]))
    routes=[];deferred=[];digest=sha(CAP)
    for distance,net,left,right,options in sorted(tasks):
        if root(left)==root(right):continue
        selected=None;grid=[];escapes={}
        for d,layer,start,end in options:
            opposite='B.Cu' if layer=='F.Cu' else 'F.Cu';limit=min(32,1.8*d+6)
            for p in [start,end]:
                key=(layer,p)
                if key not in escapes:escapes[key]=screen.escapes(net,layer,p)
            pairs=sorted((a[0]+math.dist(a[1],b[1])+b[0],a,b)
                for a in escapes[layer,start] for b in escapes[layer,end] if math.dist(a[1],b[1])>.56)
            for lower,a0,b0 in pairs:
                if lower>limit or (selected and lower>=selected[0]):continue
                middle=screen.simple(net,opposite,a0[1],b0[1],limit-a0[0]-b0[0])
                if middle:
                    length=a0[0]+middle[0]+b0[0]
                    if not selected or length<selected[0]:selected=(length,[(layer,a0[2]),(opposite,middle[1]),(layer,list(reversed(b0[2])))],[a0[1],b0[1]])
                else:grid.append((lower,limit,layer,opposite,a0,b0))
        if selected is None:
            for lower,limit,layer,opposite,a0,b0 in sorted(grid)[:4]:
                path=screen.grid_path(net,opposite,a0[1],b0[1],budget=6000)
                if path and a0[0]+LineString(path).length+b0[0]<=limit:
                    selected=(a0[0]+LineString(path).length+b0[0],[(layer,a0[2]),(opposite,path),(layer,list(reversed(b0[2])))],[a0[1],b0[1]]);break
        pu,qu=witness[left],witness[right];p,q=objects[pu],objects[qu]
        endpoints=[[p['ref'],p['pin']],[q['ref'],q['pin']]]
        if selected is None:
            deferred.append(dict(net=net,endpoints=endpoints,closest_contact_mm=distance,reason='No bounded two-via detour cleared all screens'))
            print('Deferred',net,endpoints,flush=True);continue
        length,paths,xyvias=selected;declared=[];vias=[]
        for layer,path in paths:
            ids=[]
            for pt,qt in zip(path,path[1:]):
                uid=str(uuid.uuid5(uuid.NAMESPACE_URL,f'AFX:TBLD01:{digest}:{net}:{layer}:{pt}:{qt}'))
                pcb.append([a('segment'),[a('start'),*pt],[a('end'),*qt],[a('width'),.2],[a('layer'),layer],[a('net'),codes[net]],[a('uuid'),uid]]);ids.append(uid)
            screen.added.append((net,layer,LineString(path)));declared.append(dict(layer=layer,path_mm=path,segment_uuids=ids))
        for xy in xyvias:
            uid=str(uuid.uuid5(uuid.NAMESPACE_URL,f'AFX:TBLD01:via:{digest}:{net}:{xy}'))
            pcb.append([a('via'),[a('at'),*xy],[a('size'),.6],[a('drill'),.3],[a('layers'),'F.Cu','B.Cu'],[a('net'),codes[net]],[a('uuid'),uid]])
            vias.append(dict(uuid=uid,net=net,position_mm=xy));screen.vias.append((net,xy))
            for layer in routing.SIGNAL_LAYERS:screen.added.append((net,layer,Point(xy).buffer(.2)))
        parent[root(right)]=root(left)
        routes.append(dict(net=net,endpoints=endpoints,endpoint_pad_uuids=[pu,qu],source_groups=[left,right],
            endpoint_scope='Native-group physical pad witnesses; actual paths may attach to existing tracks or vias',
            paths=declared,vias=vias,length_mm=length))
        print('Joined',net,round(length,3),'mm, 2 vias',flush=True)
    assert routes and sexpr(pcb[:count])==original
    shutil.copytree(STAGING/'two-board-power-integration-10',OUT)
    dest=OUT/'power_protection.kicad_pcb';dest.write_text(sexpr(pcb)+'\n')
    inputs=[Path(__file__),CAP,BASE/'power_protection.kicad_pcb',BASE/'netlist.xml',BASE/'additive-audit.json',BASE/'retained-via-clearance.json',
        *[REPO/'hardware/fabrication'/n for n in ['route_nf_surface.py','route_two_board_power_local_v2.py','route_two_board_power_local.py']]]
    record=dict(source_sha256={str(p.relative_to(REPO)):sha(p) for p in inputs},candidate_PCB_sha256=sha(dest),
        selected_control_net_nodes=allowed,routes=routes,deferred=deferred,
        added_segments=sum(len(p['segment_uuids']) for r in routes for p in r['paths']),added_vias=sum(len(r['vias']) for r in routes),
        existing_authored_geometry_exact=True,all_new_tracks_on_outer_layers=True,
        maximum_track_length_mm=32,maximum_contact_distance_mm=20,maximum_local_escape_length_mm=5.5,
        via_size_drill_mm=[.6,.3],screened_via_to_foreign_copper_mm=.21,screened_hole_to_hole_mm=.26,
        screened_via_copper_to_SMD_mm=.01,provisional_mount_reserves_checked=15,
        native_validation_pending=True,loaded_timing_noise_and_return_review_complete=False,fabrication_released=False)
    (OUT/'via-routing.json').write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps(dict(routes=len(routes),nets=len({r['net'] for r in routes}),segments=record['added_segments'],vias=record['added_vias'],deferred=len(deferred))))


if __name__=='__main__':run()
