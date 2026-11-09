"""Record remaining return-reference gaps and the added AUX bypass load."""
import json
from pathlib import Path
from shapely.geometry import Point,LineString
from shapely.ops import unary_union
from hardware.fabrication.integrate_two_board_signal import REPO,STAGING,sha,read_netlist
from hardware.fabrication.route_nf_surface import shape

p=STAGING/'two-board-power-fast-ov-native-03'
cp=STAGING/'two-board-power-routing-inputs-2383-fast-ov/capture.json'
pp=p/'fast-ov-plane-review.json';rp=p/'fast-ov-routing.json'
c,planes,r=[json.loads(q.read_text()) for q in [cp,pp,rp]]
for d in [c,planes,r]:
    for name,h in d['source_sha256'].items():assert sha(REPO/name)==h,name
objects={o['uuid']:o for o in c['objects']}
pad=next(o for o in objects.values() if o.get('ref')=='P_U101' and o.get('pin')=='8')
group=set(c['all_groups'][pad['group']]);zone_ids={z['uuid'] for z in planes['plane_contacts'] if group.intersection(z['directly_contacted_vias']) or any((ref,pin) in {(objects[u].get('ref'),objects[u].get('pin')) for u in group} for ref,pin in z['directly_contacted_pads'])}
adjacency={'F.Cu':['In1.Cu'],'In1.Cu':['F.Cu','In2.Cu'],'In2.Cu':['In1.Cu','In3.Cu'],'In3.Cu':['In2.Cu','In4.Cu'],'In4.Cu':['In3.Cu','In5.Cu'],'In5.Cu':['In4.Cu','In6.Cu'],'In6.Cu':['In5.Cu','B.Cu'],'B.Cu':['In6.Cu']}
checked={q['label'] for q in planes['new_route_reference_coverage']};remaining=[]
for route in r['routes']:
    if route['label'] in checked:continue
    projection=LineString(route['path_mm']).buffer(route['width_mm']/2)
    for o in objects.values():
        if o['kind']=='PCB_VIA' and o['net']==route['net'] and o['net']!='PWR_AGND':projection=projection.difference(Point(o['position_mm']).buffer(o['width_mm']/2+.215))
    layers=[]
    for layer in adjacency[route['layer']]:
        regions=[shape(z['polygons']) for z in c['zones'] if z['uuid'] in zone_ids and z['layer']==layer and z['net']=='PWR_AGND']
        ground=unary_union(regions)
        layers.append(dict(layer=layer,reference_regions=len(regions),uncovered_mm2=projection.difference(ground.buffer(.0015)).area))
    remaining.append(dict(label=route['label'],net=route['net'],layer=route['layer'],length_mm=route['length_mm'],adjacent_ground_plane_screens=layers,best_uncovered_mm2=min(z['uncovered_mm2'] for z in layers)))
oldp=STAGING/'two-board-aux-load-review-01/review.json';old=json.loads(oldp.read_text());parts,pins=read_netlist(p/'netlist.xml')
rail={(ref,pin) for (ref,pin),net in pins.items() if net=='PWR_V2V5_AUX'}
assert rail=={(q['ref'],q['pin']) for q in old['terminals']}|{('P_C114','1')}
assert parts['P_C114'].findtext('value')=='100nF 50V X7R C0603C104K5RACTU'
assert pins['P_C114','2']=='PWR_AGND'
paths=[Path(__file__),cp,pp,rp,oldp,p/'netlist.xml',REPO/'hardware/fabrication/route_nf_surface.py']
result=dict(source_sha256={str(q.relative_to(REPO)):sha(q) for q in paths},additional_route_reference_screens=remaining,
    scope='Geometry against adjacent U101-connected ground zones only; prior 22 reviewed surface paths are reported separately. Lack of a plane is a design-review item, not a computed electrical failure. Coverage is not impedance or inductance qualification.',
    all_new_routes_screened=len(checked)+len(remaining),remaining_reference_design_review_required=any(q['best_uncovered_mm2']>1e-6 for q in remaining),
    AUX_rail_terminals=len(rail),AUX_IC_supply_pins=old['categories']['IC_supply'],added_AUX_nominal_capacitance_F=1e-7,AUX_total_direct_nominal_capacitance_F=old['direct_nominal_capacitance_F']+1e-7,
    AUX_1ms_2p7V_ramp_added_nominal_average_A=1e-7*2.7/.001,AUX_capacitance_effective_minimum_or_upper_bound_verified=False,
    full_AUX_current_qualified=False,full_fast_OV_transient_qualified=False,fabrication_released=False)
with (p/'fast-ov-return-load-review.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
print(json.dumps({k:v for k,v in result.items() if k not in ['source_sha256','additional_route_reference_screens']},indent=2))
print(json.dumps(remaining,indent=2))
