"""Bounded read-only D101 pose hypotheses: pad clearance before route planning."""
import json,hashlib,math
from shapely.affinity import rotate,translate
from shapely.geometry import Point
from shapely.strtree import STRtree
from hardware.cad.two_board_sensor_05.signal_dac import adc_context_r108 as C
R=C.R;ref='A_D101';origin=(75,66);stubids={'718b29e7-1ba2-58be-8881-8126cfeebf60','f684c170-6e78-5642-9206-0e97f42c9885'}
pads=[(o,C.S.shape(o['layers']['B.Cu']))for o in C.c['objects']if o.get('ref')==ref]
obs=[(o,C.S.shape(o['layers']['B.Cu']))for o in C.c['objects']if o.get('ref')!=ref and o['uuid']not in stubids and o['layers'].get('B.Cu')];tree=STRtree([g for o,g in obs]);valid=[];tested=0
# The known left pin-7 opening is screened independently against all-layer copper.
points=[[75.90+i*.025,65.575+j*.025]for i in range(5)for j in range(4)]
fixed=[(o,g)for o,g in C.obs if o.get('ref')!=ref and o['uuid']not in stubids]
via_points=[q for q in points if all(Point(q).distance(g)>=(.27 if o['net']=='/A_ADC/PD_L'and o['kind']=='PAD'and not any(o['drill_mm'])else .51)for o,g in fixed if not(o['net']=='/A_ADC/PD_L'and o['kind']=='PCB_TRACK'))and all(math.dist(q,o['position_mm'])>=.86 for o in C.c['objects']if o['kind']=='PCB_VIA')]
for angle in [0,180,90,270]:
 for dx,dy in sorted([(i*.1,j*.1)for i in range(-10,11)for j in range(-10,11)],key=lambda v:math.hypot(*v)):
  tested+=1;moved=[(o,translate(rotate(g,angle,origin=origin),xoff=dx,yoff=dy))for o,g in pads];clear=True;minimum=math.inf
  for o,g in moved:
   for ix in tree.query(g.buffer(.21)):
    other,h=obs[int(ix)]
    if other['net']==o['net']:continue
    distance=g.distance(h);minimum=min(minimum,distance)
    if distance<.200002:clear=False;break
   if not clear:break
  if not clear:continue
  available=[q for q in via_points if all(Point(q).distance(g)>=.51 for o,g in moved)]
  if available:valid.append({'world_rotation_degrees':angle,'translation_mm':[round(dx,6),round(dy,6)],'possible_via_sites':available,'moved_pad_minimum_observed_foreign_clearance_mm':minimum if math.isfinite(minimum)else'>0.21'})
print('bounded poses',tested,'via-site baseline',len(via_points),'legal access hypotheses',len(valid));print(json.dumps(valid[:12],indent=2))
paths=[R/'pd_pose_screen_r114.py',R/'adc_context_r108.py',R/'capture-r107/capture.json'];out={'planning_only':True,'physical_source_board_unchanged':True,'reference':ref,'removed_stub_uuids':sorted(stubids),'tested_poses':tested,'pose_grid_mm':.1,'rotation_family_degrees':[0,180,90,270],'legal_pad_and_via_hypotheses':valid,'source_sha256':{str(p.relative_to(R.parents[3])):hashlib.sha256(p.read_bytes()).hexdigest()for p in paths}};p=R/'pd-pose-screen-r114.json';assert not p.exists();p.write_text(json.dumps(out,indent=2)+'\n')
