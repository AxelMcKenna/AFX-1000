"""Finite three-obstacle replacement plan around the native-proven PD via."""
import copy,json,hashlib
from pathlib import Path
from shapely.geometry import Point,LineString,box
from shapely.ops import unary_union
from hardware.fabrication import route_nf_surface as S
from hardware.cad.two_board_sensor_05.signal_dac.visibility_path import visibility_path
R=Path(__file__).resolve().parent;c=json.loads((R/'capture-r139/capture.json').read_text());objects={o['uuid']:o for o in c['objects']};ids=['b1c1865b-7772-58be-ab73-298eb697dc74','094cfe15-e54e-5a1a-86f3-64eb7dd586b8','e278094b-72b0-5e04-90d5-578081219fd8'];via=[75.8,77.65];net='/A_ADC/PD_R';capture=copy.deepcopy(c);capture['objects']=[o for o in c['objects']if o['uuid']not in ids];circle=Point(via).buffer(.300002);poly=[{'outer':list(circle.exterior.coords)[:-1],'holes':[]}];capture['objects'].append({'uuid':'prospective-PD-via','net':net,'kind':'PCB_VIA','layers':{l:poly for l in c['copper_layers']}});escape=LineString([[77.1125,77.675],via]).buffer(.100002);capture['objects'].append({'uuid':'prospective-PD-escape','net':net,'kind':'PCB_TRACK','layers':{'F.Cu':[{'outer':list(escape.exterior.coords)[:-1],'holes':[]}]}})
# Native-derived ground clearance cutback is a separately audited hypothesis.
capture['zones']=[z for z in capture['zones']if z['keepout']or z['net']!='LINK_AGND'];rows=[]
for uid in ids:
 o=objects[uid];layer,=o['layers'];S.SIGNAL_LAYERS=(layer,);S.WIDTH=o['width_mm'];screen=S.Screen(capture);start,end=o['position_mm'],o['end_mm'];paths=list(S.candidate_paths(start,end))
 for d in [.5,1,1.5,2,3,-.5,-1,-1.5,-2,-3]:paths.extend([[start,[start[0]+d,start[1]],[end[0]+d,end[1]],end],[start,[start[0],start[1]+d],[end[0],end[1]+d],end]])
 valid=[p for p in paths if screen.legal(o['net'],layer,p)];method='finite'
 if not valid:
  window=box(min(start[0],end[0])-3,min(start[1],end[1])-3,max(start[0],end[0])+3,max(start[1],end[1])+3);obstacles=unary_union([g.buffer(d+.00002)for n,g,d in screen.geometry[layer]if n!=o['net']and g.intersects(window)]);domain=screen.outline.intersection(window).difference(obstacles);p=visibility_path(domain,start,end,max_nodes=2500)
  if p and screen.legal(o['net'],layer,p):valid=[p];method='visibility'
 row={'uuid':uid,'net':o['net'],'layer':layer,'width_mm':o['width_mm'],'before_path_mm':[start,end],'before_length_mm':LineString([start,end]).length,'valid_paths':len(valid),'method':method}
 if valid:
  path=min(valid,key=lambda p:LineString(p).length);row.update(path_mm=path,after_length_mm=LineString(path).length);g=LineString(path).buffer(o['width_mm']/2+.000002);capture['objects'].append({'uuid':'prospective-replacement-'+uid,'net':o['net'],'kind':'PCB_TRACK','layers':{layer:[{'outer':list(g.exterior.coords)[:-1],'holes':[list(x.coords)[:-1]for x in g.interiors]}]}})
 rows.append(row);print(row,flush=True)
paths=[Path(__file__),R/'capture-r139/capture.json',R/'pd-probe-review-r138.json',R/'visibility_path.py'];out={'planning_only':True,'via_mm':via,'front_escape_mm':[[77.1125,77.675],via],'exact_three_authorized_replacements':rows,'source_sha256':{str(p.relative_to(R.parents[3])):hashlib.sha256(p.read_bytes()).hexdigest()for p in paths},'reference_and_native_checks_pending':True};p=R/'pd-rework-r140.json';assert not p.exists();p.write_text(json.dumps(out,indent=2)+'\n')
