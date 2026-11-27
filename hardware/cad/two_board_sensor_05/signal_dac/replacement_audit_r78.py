"""Bind exact reworked copper, retained checkpoint groups and RX_POS_R geometry context."""
import collections
import hashlib
import json
from pathlib import Path
from shapely.geometry import LineString
from hardware.electronics.common.sexpr import read_sexpr, children, first, sexpr
from hardware.fabrication.route_nf_surface import shape

R=Path(__file__).resolve().parent
REPO=R.parents[3]
def read(p): return json.loads(p.read_text())
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def objects(p):
    tree=read_sexpr(p.read_text())
    result={}
    for tag in ['footprint','segment','via','zone','gr_line','gr_rect','gr_arc','gr_circle','gr_poly']:
        for row in children(tree,tag):
            uid=first(row,'uuid')
            if uid is None: continue
            if tag=='zone':
                row=[x for x in row if not(isinstance(x,list)and x and x[0]=='filled_polygon')]
            result[uid[1]]={'kind':tag,'authored':sexpr(row)}
    return result

before=objects(R/'native-r62/signal_main.kicad_pcb')
after=objects(R/'native-r78/signal_main.kicad_pcb')
candidate=objects(R/'candidate-r78/signal_main.kicad_pcb')
original=objects(R.parent/'signal_input/native-r7/signal_main.kicad_pcb')
routing=read(R/'candidate-r78/routing.json')
declared={x['uuid']:x for x in routing['declared_removed_agent_copper']}
from hardware.cad.two_board_sensor_05.signal_dac.copper_inventory import validate_inventory
assert len(declared)==8
validate_inventory(before,after,original,routing['declared_removed_agent_copper'],candidate)

b=read(R/'capture-r62/capture.json');c=read(R/'capture-r78/capture.json')
new_group={u:g for g,members in c['all_groups'].items()for u in members}
old_objects={o['uuid']:o for o in b['objects']}
merged=collections.defaultdict(list)
for group,members in b['all_groups'].items():
    retained=[u for u in members if u not in declared]
    assert retained and all(u in new_group for u in retained)
    destination={new_group[u]for u in retained}
    assert len(destination)==1,('split accepted checkpoint group',group)
    merged[next(iter(destination))].append(group)
merges=[]
for target,groups in merged.items():
    if len(groups)==1: continue
    nets={old_objects[b['all_groups'][g][0]]['net']for g in groups}
    assert nets=={'/A_DAC/RX_POS_R'} and len(groups)==2
    merges.append({'net':'/A_DAC/RX_POS_R','before_groups':groups,'after_group':target})
assert len(merges)==1

net='/A_DAC/RX_POS_R'
new_objects={o['uuid']:o for o in c['objects']}
new_routing=read(R/'candidate-r77/routing.json')
route_rows=[r for r in new_routing['routes']if r['net']==net]
full_net_authored_length=sum(LineString(r['path_mm']).length for r in routing['routes']if r['net']==net)
authored_length=sum(LineString(r['path_mm']).length for r in route_rows)
added_rx=[new_objects[u]for u in sorted(set(after)-set(before))if u in new_objects and new_objects[u]['kind']=='PCB_TRACK'and new_objects[u]['net']==net]
native_length=sum(LineString([o['position_mm'],o['end_mm']]).length for o in added_rx)
assert abs(authored_length-native_length)<1e-6
assert abs(authored_length-routing['RX_POS_R_trace_length_mm'])<1e-9
layers=c['copper_layers'];context=[]
for row in route_rows:
    copper=LineString(row['path_mm']).buffer(row['width_mm']/2)
    index=layers.index(row['layer'])
    adjacent={layers[i]for i in [index-1,index+1]if 0<=i<len(layers)}
    same=[];projected=[]
    for o in c['objects']:
        if o['net']in [net,'LINK_AGND']: continue
        for layer in [row['layer'],*sorted(adjacent)]:
            if not o['layers'].get(layer): continue
            g=shape(o['layers'][layer]);distance=copper.distance(g)
            entry={k:o.get(k)for k in ['uuid','net','kind','ref','pin']}
            entry.update(layer=layer,projected_edge_distance_mm=distance)
            if layer==row['layer']: same.append(entry)
            elif distance<=1: projected.append(entry)
    same.sort(key=lambda x:x['projected_edge_distance_mm'])
    projected.sort(key=lambda x:x['projected_edge_distance_mm'])
    context.append({'layer':row['layer'],'role':row['role'],'path_mm':row['path_mm'],
                    'length_mm':LineString(row['path_mm']).length,
                    'closest_foreign_same_layer_copper':same[:5],
                    'adjacent_layer_foreign_copper_within_1mm_projection':projected,
                    'projection_is_not_vertical_spacing_or_noise_qualification':True})
paths=[Path(__file__),R/'copper_inventory.py',R/'test_copper_inventory.py',R/'native-r62/signal_main.kicad_pcb',R/'native-r78/signal_main.kicad_pcb',
       R/'candidate-r78/signal_main.kicad_pcb',R/'candidate-r78/routing.json',R/'candidate-r77/routing.json',
       R/'capture-r62/capture.json',R/'capture-r78/capture.json',R.parent/'signal_input/native-r7/signal_main.kicad_pcb']
report={'original_copper_unchanged':True,'retained_r62_authored_objects_unchanged':True,
        'all_r62_native_groups_preserved':True,'new_r62_group_merge':merges,
        'removed_agent_copper':list(declared.values()),
        'added_copper_and_reference_inventory':[{ 'uuid':u,**after[u]}for u in sorted(set(after)-set(before))],
        'RX_POS_R_all_DAC_authored_route_length_mm':full_net_authored_length,'RX_POS_R_authored_trace_length_mm':authored_length,'RX_POS_R_native_trace_length_mm':native_length,
        'RX_POS_R_geometry_context':context,'noise_stability_crosstalk_qualified':False,
        'source_sha256':{str(p.relative_to(REPO)):sha(p)for p in paths}}
(R/'replacement-audit-r78.json').write_text(json.dumps(report,indent=2)+'\n')
print('PASS exact eight-object replacement; all r62 groups preserved; RX_POS_R length',native_length)
