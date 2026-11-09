"""Add short outer-layer control routes using complete native obstacles.

Only named control nets with a native output/open-collector driver qualify.
Power, force, sense, reference, gate and passive timer nets are excluded.
Existing copper, component placements, schematic and rules stay unchanged.
"""
import json
import math
import shutil
import uuid
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from pathlib import Path

from shapely.geometry import LineString
import hardware.fabrication.route_nf_surface as routing
from hardware.electronics.common.sexpr import a, children, first, read_sexpr, sexpr
from hardware.fabrication.integrate_two_board_signal import REPO, STAGING, sha

BASE=STAGING/'two-board-power-routed-native-02'
CAP=STAGING/'two-board-power-routing-inputs-2653/capture.json'
OUT=STAGING/'two-board-power-local-01'


def run():
    assert not OUT.exists()
    cap=json.loads(CAP.read_text())
    for name,h in cap['source_sha256'].items():assert sha(Path(name))==h,name
    tree=read_sexpr((BASE/'power_protection.kicad_pcb').read_text());base_count=len(tree)
    before=sexpr(tree)
    net_codes={str(n[2]):int(n[1]) for n in children(tree,'net')}
    native=ET.parse(BASE/'netlist.xml')
    allowed={};excluded=[]
    for net in native.findall('./nets/net'):
        name=net.attrib['name'];nodes=[n.attrib for n in net.findall('node')]
        if name not in cap['open_nets'] or not routing.is_logic_net(name):continue
        kinds={n.get('pintype') for n in nodes}
        if not kinds & {'output','open_collector'} or kinds & {'power_in','power_out'}:
            excluded.append(dict(net=name,reason='No declared logic driver, or a power terminal',nodes=nodes));continue
        allowed[name]=nodes
    routing.SIGNAL_LAYERS=('F.Cu','B.Cu');routing.WIDTH=.2
    screen=routing.Screen(cap)
    pads=defaultdict(list)
    for item in cap['objects']:
        if item['kind']=='PAD' and item.get('pin') and item['net'] in allowed:pads[item['net']].append(item)
    parent={k:k for k in cap['groups']}
    def root(k):
        while parent[k]!=k:parent[k]=parent[parent[k]];k=parent[k]
        return k
    candidates=[]
    for net,items in pads.items():
        for i,p in enumerate(items):
            for q in items[i+1:]:
                if p['group']==q['group']:continue
                distance=math.dist(p['position_mm'],q['position_mm'])
                layers=set(p['layers'])&set(q['layers'])&{'F.Cu','B.Cu'}
                if distance<=20 and distance>1e-6 and layers:candidates.append((distance,net,p['uuid'],q['uuid'],sorted(layers)))
    candidates.sort();objects={o['uuid']:o for o in cap['objects']};routes=[];deferred=[]
    for distance,net,pu,qu,layers in candidates:
        p,q=objects[pu],objects[qu]
        if root(p['group'])==root(q['group']):continue
        start,end=tuple(p['position_mm']),tuple(q['position_mm'])
        limit=min(26,1.5*distance+1);choices=[]
        for layer in layers:
            for path in routing.candidate_paths(start,end):
                path=[xy for i,xy in enumerate(path) if i==0 or xy!=path[i-1]]
                if len(path)<2:continue
                length=LineString(path).length
                if length<=limit and screen.legal(net,layer,path):choices.append((length,layer,path))
        if not choices:
            deferred.append(dict(net=net,endpoints=[[p['ref'],p['pin']],[q['ref'],q['pin']]],distance_mm=distance,
                reason='No short direct/orthogonal/45-degree candidate clears the complete native obstacles'));continue
        length,layer,path=min(choices,key=lambda c:c[0]);ids=[]
        for i,(start,end) in enumerate(zip(path,path[1:])):
            ident=str(uuid.uuid5(uuid.NAMESPACE_URL,f'AFX:TBPL01:{sha(CAP)}:{net}:{layer}:{start}:{end}'))
            tree.append([a('segment'),[a('start'),*start],[a('end'),*end],[a('width'),.2],
                [a('layer'),layer],[a('net'),net_codes[net]],[a('uuid'),ident]])
            ids.append(ident)
        screen.added.append((net,layer,LineString(path)));parent[root(q['group'])]=root(p['group'])
        routes.append(dict(net=net,layer=layer,width_mm=.2,path_mm=path,length_mm=length,
            endpoints=[[p['ref'],p['pin']],[q['ref'],q['pin']]],endpoint_pad_uuids=[pu,qu],
            source_groups=[p['group'],q['group']],segment_uuids=ids))
    assert sexpr(tree[:base_count])==before and routes
    shutil.copytree(STAGING/'two-board-power-integration-10',OUT)
    pcb=OUT/'power_protection.kicad_pcb';pcb.write_text(sexpr(tree)+'\n')
    paths=[Path(__file__),CAP,BASE/'power_protection.kicad_pcb',BASE/'netlist.xml',BASE/'copper-audit.json',
        REPO/'hardware/fabrication/route_nf_surface.py']
    record=dict(source_sha256={str(p.relative_to(REPO)):sha(p) for p in paths},candidate_PCB_sha256=sha(pcb),
        selected_control_net_nodes=allowed,excluded_name_matches=excluded,routes=routes,deferred=deferred,
        maximum_endpoint_distance_mm=20,maximum_route_length_mm=26,
        added_segments=sum(len(r['segment_uuids']) for r in routes),added_vias=0,
        existing_authored_geometry_exact=True,all_added_tracks_on_outer_layers=True,
        full_loaded_timing_noise_and_return_review_complete=False,native_validation_pending=True,fabrication_released=False)
    (OUT/'local-routing.json').write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps(dict(routes=len(routes),nets=len({r['net'] for r in routes}),segments=record['added_segments'],
        length_mm=sum(r['length_mm'] for r in routes),by_layer=dict(Counter(r['layer'] for r in routes)),deferred=len(deferred)),indent=2))


if __name__=='__main__':run()
