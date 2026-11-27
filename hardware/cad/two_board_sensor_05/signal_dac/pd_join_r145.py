"""Bounded PD_R inner route and physical return after exact authorized rework."""
import copy,json,hashlib,math
from pathlib import Path
from shapely.geometry import Point,LineString,box
from shapely.ops import unary_union
from shapely.strtree import STRtree
from hardware.cad.two_board_sensor_05.signal_dac import adc_context_r134 as C
R=C.R;c=json.loads((R/'capture-r139/capture.json').read_text());joint=json.loads((R/'pd-joint-r144.json').read_text());choice=joint['accepted'][0];plan={**joint,'exact_three_authorized_replacements':choice['exact_replacements']};ids={x['uuid']for x in plan['exact_three_authorized_replacements']};c['objects']=[o for o in c['objects']if o['uuid']not in ids];net='/A_ADC/PD_R';via=plan['via_mm']
for row in plan['exact_three_authorized_replacements']:
 for i,(p,q)in enumerate(zip(row['path_mm'],row['path_mm'][1:])):
  g=LineString([p,q]).buffer(row['width_mm']/2+.000002);c['objects'].append({'uuid':row['uuid']+'-'+str(i),'net':row['net'],'kind':'PCB_TRACK','position_mm':p,'end_mm':q,'width_mm':row['width_mm'],'layers':{row['layer']:[{'outer':list(g.exterior.coords)[:-1],'holes':[]}]}})
C.c=c;C.screen=C.S.Screen(c);C.base_legal=C.screen.legal;C.screen.legal=C.ref_legal;C.front_allow.clear();C.front_dynamic_key=None;C.obs=[(o,C.S.shape(ps))for o in c['objects']for ps in o['layers'].values()if ps];C.tree=STRtree([g for _,g in C.obs]);C.prospective_holes=[via]
assert C.vialegal(via,net);ret=choice['return_mm'];assert C.return_field.covers(Point(ret).buffer(.31));assert C.screen.legal(net,'F.Cu',plan['front_escape_mm']);assert LineString(plan['front_escape_mm']).distance(Point(ret))>.51
print('return',ret,flush=True)
targets=[o for o in c['objects']if o['net']==net and o['kind']=='PCB_VIA'];found=[]
for o in targets:
 end=o['position_mm'];paths=[p for p in C.S.candidate_paths(via,end)if C.base_legal(net,'In3.Cu',p)and LineString(p).distance(Point(ret))>.51]
 if not paths:
  window=box(min(via[0],end[0])-3,min(via[1],end[1])-3,max(via[0],end[0])+3,max(via[1],end[1])+3);obstacles=unary_union([g.buffer(d+.00002)for n,g,d in C.screen.geometry['In3.Cu']if n!=net and g.intersects(window)]+[Point(ret).buffer(.61)]);domain=C.screen.outline.intersection(window).difference(obstacles);p=C.visibility_path(domain,via,end,max_nodes=3000)
  if p and C.base_legal(net,'In3.Cu',p):paths=[p]
 for p in paths:found.append({'inner_path_mm':p,'target_uuid':o['uuid'],'target_group':o['group'],'length_mm':LineString(p).length})
assert found,'No bounded In3 path';best=min(found,key=lambda x:x['length_mm']);print(best,flush=True)
existing=next((o for o in c['objects']if o['kind']=='PCB_VIA'and o['net']=='LINK_AGND'and o['position_mm']==ret),None)
out={**plan,'return_at':ret,'return_existing_uuid':existing['uuid']if existing else None,**best,'planning_only':True,'source_sha256':{str(p.relative_to(R.parents[3])):hashlib.sha256(p.read_bytes()).hexdigest()for p in [Path(__file__),R/'pd-joint-r144.json',R/'capture-r139/capture.json',R/'adc_context_r134.py',R/'visibility_path.py']}};p=R/'pd-join-r145.json';assert not p.exists();p.write_text(json.dumps(out,indent=2)+'\n')
