"""Joint bounded return-site and three-object detour search; planning only."""
import copy,hashlib,json,math
from itertools import chain
from pathlib import Path
from shapely.geometry import Point,LineString,box
from shapely.ops import unary_union
from hardware.cad.two_board_sensor_05.signal_dac.visibility_path import visibility_path
from shapely.strtree import STRtree
from hardware.cad.two_board_sensor_05.signal_dac import adc_context_r134 as C
from hardware.fabrication import route_nf_surface as S
R=C.R;base=json.loads((R/'capture-r139/capture.json').read_text());plan=json.loads((R/'pd-rework-r140.json').read_text());ids={x['uuid']for x in plan['exact_three_authorized_replacements']};c=copy.deepcopy(base);c['objects']=[o for o in c['objects']if o['uuid']not in ids];via=plan['via_mm'];net='/A_ADC/PD_R';C.c=c;C.obs=[(o,S.shape(ps))for o in c['objects']for ps in o['layers'].values()if ps];C.tree=STRtree([g for _,g in C.obs]);c['zones']=[z for z in c['zones']if z['keepout']or z['net']!='LINK_AGND']
def addshape(c,uid,net,kind,g,layers,position):c['objects'].append({'uuid':uid,'net':net,'kind':kind,'position_mm':position,'layers':{l:[{'outer':list(g.exterior.coords)[:-1],'holes':[]}]for l in layers}})
addshape(c,'PD-via',net,'PCB_VIA',Point(via).buffer(.300002),base['copper_layers'],via);addshape(c,'PD-escape',net,'PCB_TRACK',LineString(plan['front_escape_mm']).buffer(.100002),['F.Cu'],plan['front_escape_mm'][0])
sites=[]
offsets=sorted([(i*.1,j*.1)for i in range(-25,26)for j in range(-25,26)if .9<=math.hypot(i*.1,j*.1)<=2.5],key=lambda p:math.hypot(*p))
for i,j in offsets:
 q=[round(via[0]+i,6),round(via[1]+j,6)];pt=Point(q)
 if any((o['kind']=='PAD'and not any(o['drill_mm'])and pt.distance(g)<.27)or(o['net']!='LINK_AGND'and pt.distance(g)<.51)for o,g in (C.obs[int(ix)]for ix in C.tree.query(pt.buffer(.52)))):continue
 if not C.return_field.covers(pt.buffer(.31)):continue
 if not any(LineString(p).length<=2.5 and LineString(p).buffer(.1).difference(Point(via).buffer(.515)).difference(C.return_field).area<1e-6 for p in chain(S.candidate_paths(via,q),C.v_paths(via,q))):continue
 if LineString(plan['front_escape_mm']).distance(pt)<=.51:continue
 if any(o['kind']=='PCB_VIA'and math.dist(q,o['position_mm'])<.86 for o in c['objects']):continue
 sites.append(q)
 if len(sites)>=24:break
print('bounded return sites',sites,flush=True);attempts=[];accepted=[]
for ret in sites:
 capture=copy.deepcopy(c);addshape(capture,'ground-return','LINK_AGND','PCB_VIA',Point(ret).buffer(.300002),base['copper_layers'],ret);rows=[]
 for before in plan['exact_three_authorized_replacements']:
  layer=before['layer'];S.SIGNAL_LAYERS=(layer,);S.WIDTH=before['width_mm'];screen=S.Screen(capture);start,end=before['before_path_mm'];paths=list(S.candidate_paths(start,end))
  for d in [.5,.75,1,1.25,1.5,2,3,-.5,-.75,-1,-1.25,-1.5,-2,-3]:paths.extend([[start,[start[0]+d,start[1]],[end[0]+d,end[1]],end],[start,[start[0],start[1]+d],[end[0],end[1]+d],end]])
  valid=[p for p in paths if screen.legal(before['net'],layer,p)]
  if not valid:
   window=box(72,73,80,83);obstacles=unary_union([g.buffer(d+.00002)for n,g,d in screen.geometry[layer]if n!=before['net']and g.intersects(window)]);domain=screen.outline.intersection(window).difference(obstacles)
   p=visibility_path(domain,start,end,max_nodes=2500)
   if p and screen.legal(before['net'],layer,p):valid=[p]
  if not valid:break
  path=min(valid,key=lambda p:LineString(p).length);row={**before,'path_mm':path,'after_length_mm':LineString(path).length};rows.append(row);addshape(capture,'replacement-'+before['uuid'],before['net'],'PCB_TRACK',LineString(path).buffer(before['width_mm']/2+.000002),[layer],start)
 attempts.append({'return_mm':ret,'routed_objects':len(rows)})
 if len(rows)==3:accepted.append({'return_mm':ret,'exact_replacements':rows});print('accepted planning',accepted[-1],flush=True)
 if len(accepted)>=3:break
out={'planning_only':True,'via_mm':via,'front_escape_mm':plan['front_escape_mm'],'bounded_attempts':attempts,'accepted':accepted,'source_sha256':{str(p.relative_to(R.parents[3])):hashlib.sha256(p.read_bytes()).hexdigest()for p in [Path(__file__),R/'capture-r139/capture.json',R/'pd-rework-r140.json',R/'adc_context_r134.py']}};p=R/'pd-joint-r144.json';assert not p.exists();p.write_text(json.dumps(out,indent=2)+'\n')
