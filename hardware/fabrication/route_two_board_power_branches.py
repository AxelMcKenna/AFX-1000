"""Join nearby logic groups at native pad/track/via contacts on either face."""
import itertools
import json
import math
import shutil
import uuid
import xml.etree.ElementTree as ET
from pathlib import Path
from shapely.geometry import LineString
from hardware.electronics.common.sexpr import a, children, read_sexpr, sexpr
from hardware.fabrication.integrate_two_board_signal import REPO, STAGING, sha
from hardware.fabrication.route_two_board_power_local_v2 import MountScreen
import hardware.fabrication.route_nf_surface as routing

BASE=STAGING/'two-board-power-routed-native-05'
CAP=STAGING/'two-board-power-routing-inputs-2599/capture.json'
OUT=STAGING/'two-board-power-branches-01'


def run():
    assert not OUT.exists()
    cap=json.loads(CAP.read_text())
    for name,h in cap['source_sha256'].items():assert sha(Path(name))==h,name
    pcb=read_sexpr((BASE/'power_protection.kicad_pcb').read_text());count=len(pcb);original=sexpr(pcb)
    codes={str(n[2]):int(n[1]) for n in children(pcb,'net')};allowed={}
    for net in ET.parse(BASE/'netlist.xml').findall('./nets/net'):
        name=net.attrib['name'];nodes=[n.attrib for n in net.findall('node')];types={n.get('pintype') for n in nodes}
        if name in cap['open_nets'] and routing.is_logic_net(name) and types&{'output','open_collector'} and not types&{'power_in','power_out'}:
            allowed[name]=nodes
    routing.SIGNAL_LAYERS=('F.Cu','B.Cu');routing.WIDTH=.2;screen=MountScreen(cap)
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
            options=sorted((math.dist(p,q),layer,p,q) for layer,p in contacts[left] for qlayer,q in contacts[right]
                if layer==qlayer and 1e-6<math.dist(p,q)<=20)
            if options:tasks.append((options[0][0],net,left,right,options[:40]))
    routes=[];deferred=[];digest=sha(CAP)
    for distance,net,left,right,options in sorted(tasks):
        if root(left)==root(right):continue
        selected=None
        for d,layer,start,end in options:
            if selected and d>=selected[0]:break
            limit=min(26,1.5*d+1)
            for path in routing.candidate_paths(start,end):
                path=[p for i,p in enumerate(path) if not i or p!=path[i-1]]
                if len(path)<2:continue
                length=LineString(path).length
                if length>limit or (selected and length>=selected[0]):continue
                if screen.legal(net,layer,path):selected=(length,layer,path)
        pu,qu=witness[left],witness[right];p,q=objects[pu],objects[qu]
        endpoints=[[p['ref'],p['pin']],[q['ref'],q['pin']]]
        if not selected:
            deferred.append(dict(net=net,endpoints=endpoints,closest_contact_mm=distance,reason='No short screened surface path among sampled native contacts'));continue
        length,layer,path=selected;ids=[]
        for pt,qt in zip(path,path[1:]):
            uid=str(uuid.uuid5(uuid.NAMESPACE_URL,f'AFX:TBPB01:{digest}:{net}:{layer}:{pt}:{qt}'))
            pcb.append([a('segment'),[a('start'),*pt],[a('end'),*qt],[a('width'),.2],[a('layer'),layer],[a('net'),codes[net]],[a('uuid'),uid]]);ids.append(uid)
        screen.added.append((net,layer,LineString(path)));parent[root(right)]=root(left)
        routes.append(dict(net=net,endpoints=endpoints,endpoint_pad_uuids=[pu,qu],source_groups=[left,right],
            endpoint_scope='Physical pad witnesses for the two native groups; route may attach to existing track/via contacts',
            layer=layer,path_mm=path,segment_uuids=ids,length_mm=length))
        print('Joined',net,round(length,3),'mm',flush=True)
    assert routes and sexpr(pcb[:count])==original
    shutil.copytree(STAGING/'two-board-power-integration-10',OUT)
    dest=OUT/'power_protection.kicad_pcb';dest.write_text(sexpr(pcb)+'\n')
    inputs=[Path(__file__),CAP,BASE/'power_protection.kicad_pcb',BASE/'netlist.xml',BASE/'additive-audit.json',
        *[REPO/'hardware/fabrication'/n for n in ['route_nf_surface.py','route_two_board_power_local_v2.py','route_two_board_power_local.py']]]
    record=dict(source_sha256={str(p.relative_to(REPO)):sha(p) for p in inputs},candidate_PCB_sha256=sha(dest),
        selected_control_net_nodes=allowed,routes=routes,deferred=deferred,
        added_segments=sum(len(r['segment_uuids']) for r in routes),added_vias=0,
        existing_authored_geometry_exact=True,all_new_tracks_on_outer_layers=True,
        native_validation_pending=True,loaded_timing_noise_and_return_review_complete=False,fabrication_released=False)
    (OUT/'branch-routing.json').write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps(dict(routes=len(routes),nets=len({r['net'] for r in routes}),segments=record['added_segments'],deferred=len(deferred))))


if __name__=='__main__':run()
