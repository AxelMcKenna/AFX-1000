"""Exact no-replacement ADC control additions and retained native group audit."""
import collections,hashlib,json
from pathlib import Path
from shapely.geometry import LineString
from hardware.fabrication.route_nf_surface import shape
from hardware.electronics.common.sexpr import read_sexpr,children,first,sexpr
from hardware.cad.two_board_sensor_05.signal_dac.copper_inventory import validate_inventory
R=Path(__file__).resolve().parent;REPO=R.parents[3]
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def objects(p):
 t=read_sexpr(p.read_text());result={}
 for tag in ['footprint','segment','via','zone','gr_line','gr_rect','gr_arc','gr_circle','gr_poly']:
  for row in children(t,tag):
   uid=first(row,'uuid')
   if uid is None:continue
   if tag=='zone':row=[x for x in row if not(isinstance(x,list)and x and x[0]=='filled_polygon')]
   result[uid[1]]={'kind':tag,'authored':sexpr(row)}
 return result
before=objects(R/'native-r89/signal_main.kicad_pcb');after=objects(R/'native-r95/signal_main.kicad_pcb');original=objects(R.parent/'signal_input/native-r7/signal_main.kicad_pcb');candidate=objects(R/'candidate-r95/signal_main.kicad_pcb');routing=read(R/'candidate-r95/routing.json');assert routing['declared_removed_since_r89']==[]
validate_inventory(before,after,original,[],candidate)
b=read(R/'capture-r89/capture.json');c=read(R/'capture-r95/capture.json');new_group={u:g for g,m in c['all_groups'].items()for u in m};old={o['uuid']:o for o in b['objects']};merged=collections.defaultdict(list)
for group,members in b['all_groups'].items():
 assert all(u in new_group for u in members);dest={new_group[u]for u in members};assert len(dest)==1;merged[next(iter(dest))].append(group)
merges=[]
for dest,gs in merged.items():
 if len(gs)==1:continue
 nets={old[b['all_groups'][g][0]]['net']for g in gs};assert len(nets)==1 and next(iter(nets))in routing['ADC_selected_nets'];merges.append({'net':next(iter(nets)),'before_groups':gs,'after_group':dest})
assert sum(len(m['before_groups'])-1 for m in merges)==10
old_routes=read(R/'candidate-r89/routing.json')['routes'];assert routing['routes'][:len(old_routes)]==old_routes
new_routes=routing['routes'][len(old_routes):];assert len(new_routes)==18 and all(x['layer']in ['F.Cu','B.Cu','In3.Cu','In5.Cu']and x['net']in routing['ADC_selected_nets']for x in new_routes)
added=set(after)-set(before);assert all(after[u]['kind']in ['segment','via','zone']for u in added)
new_objects={o['uuid']:o for o in c['objects']};length=sum(LineString([new_objects[u]['position_mm'],new_objects[u]['end_mm']]).length for u in sorted(added)if u in new_objects and new_objects[u]['kind']=='PCB_TRACK');assert abs(length-sum(LineString(r['path_mm']).length for r in new_routes))<1e-6
context=[]
for route in new_routes:
 copper=LineString(route['path_mm']).buffer(route['width_mm']/2);near=[]
 for o in c['objects']:
  if o['net']in [route['net'],'LINK_AGND']or not o['layers'].get(route['layer']):continue
  near.append({'uuid':o['uuid'],'net':o['net'],'kind':o['kind'],'edge_spacing_mm':copper.distance(shape(o['layers'][route['layer']]))})
 near.sort(key=lambda v:v['edge_spacing_mm']);context.append({**route,'length_mm':LineString(route['path_mm']).length,'closest_same_layer_foreign_copper':near[:3]})
paths=[Path(__file__),R/'copper_inventory.py',R/'test_copper_inventory.py',R/'native-r89/signal_main.kicad_pcb',R/'native-r95/signal_main.kicad_pcb',R/'candidate-r89/routing.json',R/'candidate-r95/routing.json',R/'candidate-r95/signal_main.kicad_pcb',R/'capture-r89/capture.json',R/'capture-r95/capture.json',R.parent/'signal_input/native-r7/signal_main.kicad_pcb']
report={'original_copper_unchanged':True,'all_r89_authored_objects_unchanged':True,'all_r89_native_groups_preserved':True,'new_group_merges':merges,'removed_agent_copper':[],'added_inventory':[{ 'uuid':u,**after[u]}for u in sorted(added)],'new_routes':new_routes,'geometry_context':context,'new_trace_length_mm':length,'source_sha256':{str(p.relative_to(REPO)):sha(p)for p in paths},'noise_stability_crosstalk_qualified':False}
(R/'replacement-audit-r95.json').write_text(json.dumps(report,indent=2)+'\n');print('PASS exact additions only; all r89 groups retained; new control joins 10')
