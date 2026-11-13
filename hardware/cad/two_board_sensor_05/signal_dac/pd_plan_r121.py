"""Plan one FDA PD_L closure with a bounded, source-declared D101 translation."""
import copy,json,hashlib,math
from pathlib import Path
from shapely.affinity import translate,rotate
from shapely.geometry import Point,LineString,box
from shapely.ops import unary_union,nearest_points
from shapely.strtree import STRtree
from hardware.cad.two_board_sensor_05.signal_dac import adc_context_r108 as C
R=C.R;base=copy.deepcopy(C.c);net='/A_ADC/PD_L'
pose=json.loads((R/'pd-courtyard-r119.json').read_text());assert any(x['world_rotation_degrees']==270 and x['translation_mm']==[.8,-.8]for x in pose['accepted'])
access=json.loads((R/'pd-access-r120-A_U101.json').read_text());via=access['candidates'][0]['at'];ret=access['candidates'][0]['return_at'];stubids={'718b29e7-1ba2-58be-8881-8126cfeebf60','f684c170-6e78-5642-9206-0e97f42c9885'};stubs=[]
def point_transform(p):return [75.8+(p[1]-66),65.2-(p[0]-75)]
for item in base['objects']:
 if item.get('ref')=='A_D101':
  item['position_mm']=point_transform(item['position_mm'])
  for layer,ps in item['layers'].items():
   g=translate(rotate(C.S.shape(ps),270,origin=(75,66)),xoff=.8,yoff=-.8);item['layers'][layer]=[{'outer':list(g.exterior.coords)[:-1],'holes':[list(r.coords)[:-1]for r in g.interiors]}]
 if item['uuid']in stubids:
  before=copy.deepcopy(item);item['position_mm']=point_transform(item['position_mm']);g=LineString([item['position_mm'],item['end_mm']]).buffer(item['width_mm']/2+.000002);item['layers']={'B.Cu':[{'outer':list(g.exterior.coords)[:-1],'holes':[]}]};stubs.append({'uuid':item['uuid'],'net':item['net'],'layer':'B.Cu','width_mm':item['width_mm'],'before_path_mm':[before['position_mm'],before['end_mm']],'path_mm':[item['position_mm'],item['end_mm']]})
C.c=base;C.screen=C.S.Screen(base);C.base_legal=C.screen.legal;C.screen.legal=C.ref_legal;C.front_allow.clear();C.front_dynamic_key=None;C.obs=[(o,C.S.shape(ps))for o in base['objects']for ps in o['layers'].values()if ps];C.tree=STRtree([g for o,g in C.obs]);C.prospective_holes=[via]
assert C.vialegal(via,net) and C.return_site(via)==ret
for s in stubs:assert C.base_legal(s['net'],'B.Cu',s['path_mm']),s
assert C.screen.legal(net,'F.Cu',access['candidates'][0]['escape'])
oldtrack=next(o for o in base['objects']if o['uuid']=='f7da0c13-089a-5300-8247-dc2b485ebc01');line=LineString([oldtrack['position_mm'],oldtrack['end_mm']]);q=nearest_points(line,Point(via))[0];targets=[[round(q.x,6),round(q.y,6)],oldtrack['position_mm'],oldtrack['end_mm']];found=[]
for endpoint in targets:
 paths=[p for p in C.S.candidate_paths(via,endpoint)if C.base_legal(net,'In3.Cu',p)]
 if not paths:
  window=box(min(via[0],endpoint[0])-3,min(via[1],endpoint[1])-3,max(via[0],endpoint[0])+3,max(via[1],endpoint[1])+3);obstacles=unary_union([g.buffer(d+.00001)for n,g,d in C.screen.geometry['In3.Cu']if n!=net and g.intersects(window)]);domain=window.intersection(C.screen.outline).difference(obstacles);p=C.visibility_path(domain,via,endpoint,max_nodes=3500)
  if p and C.base_legal(net,'In3.Cu',p):paths.append(p)
 if paths:found.append(min(paths,key=lambda p:LineString(p).length))
assert found,'No route in bounded internal family'
path=min(found,key=lambda p:LineString(p).length);print('INNER',path,'length',LineString(path).length,flush=True)
result={'planning_only':True,'physical_source_board_unchanged':True,'move':{'reference':'A_D101','before_mm':[75,66],'after_mm':[75.8,65.2],'side':'B.Cu','orientation_degrees':90,'world_rotation_degrees':270,'courtyard_bounds_before_mm':[73.07,64.3,76.93,67.7],'courtyard_bounds_after_mm':[74.1,63.27,77.5,67.13]},'exact_stub_reworks':stubs,'signal_via_at':via,'return_at':ret,'front_escape':access['candidates'][0]['escape'],'inner_path':path,'new_join_net':net,'new_signal_length_mm':LineString(path).length+LineString(access['candidates'][0]['escape']).length,'native_acceptance_pending':True}
paths=[Path(__file__),R/'pd-courtyard-r119.json',R/'pd-access-r120-A_U101.json',R/'adc_context_r108.py',R/'capture-r107/capture.json',R/'visibility_path.py'];result['source_sha256']={str(p.relative_to(R.parents[3])):hashlib.sha256(p.read_bytes()).hexdigest()for p in paths};out=R/'pd-plan-r121.json';assert not out.exists();out.write_text(json.dumps(result,indent=2)+'\n')
