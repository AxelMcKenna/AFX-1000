"""Shared formed-route planner retaining independent source/terminal identities."""
from pathlib import Path
import json,hashlib,math
from hardware.cad.two_board_installation_06.r15_right_ground.curves import Wire
HERE=Path(__file__).resolve().parent;BASE=HERE.parent;REPO=HERE.parents[3]
sources=[Path(__file__),BASE/'r15_right_ground/curves.py',BASE/'r19_panel_inventory/inventory.json',BASE/'r12_ground/ground-routes.json',BASE/'r20_scene_signal/route.json',BASE/'r22_ground_signal_clearance/bows.json',BASE/'r21_adjacent_signals/routes.json']
inventory=json.loads(sources[2].read_text());datums=json.loads(sources[3].read_text())['endpoints_mm'];edges=[]
for name,sid,source_radius,low in [('scene_4','S04',12,23.2)]:
 row=next(w for w in inventory['wires'] if w['target']=='button_'+name+':1');end=datums[row['target']];start=row['source_xy_mm']+[27.04]
 angle=216;az=math.radians(angle);T=[math.cos(az),math.sin(az),0]
 w=Wire(start);w.arc([0,0,1],T,source_radius,90)
 down=math.sqrt(.96) if sid=="S02" else 1
 N=[.2*T[1],-.2*T[0],-down] if sid=="S02" else [0,0,-1]
 w.s_curve(T,N,12,(27.04+source_radius-low)/down)
 w.arc(T,[-T[1],T[0],0],14,360-angle);assert end[0]-14>w.p[0];w.line([end[0]-14,w.p[1],low]);w.arc([1,0,0],[0,1,0],14,90)
 if sid=='S04':
  run=18;dz=end[2]-low;R=(run*run+dz*dz)/(2*dz);assert w.p[1]<=end[1]-run;w.line([end[0],end[1]-run,low]);w.arc([0,1,0],[0,0,1],R,math.degrees(2*math.atan2(dz,run)))
 else:
  w.s_curve([0,1,0],[0,0,1],12,end[2]-low);assert w.p[1]<=end[1],(sid,w.p,end);w.line(end)

 edges.append(dict(id=sid,source=row['source'],target=row['target'],net=row['net'],wire='Alpha5853 26AWG7/34',points_mm=[p.tolist() for p in w.points],primitives=w.primitives))
out=dict(source_sha256={str(p.relative_to(REPO)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},edges=edges,wire_radius_mm=.6,required_centerline_radius_mm=12,fabrication_released=False,opening_slack_qualified=False)
(HERE/'routes.json').write_text(json.dumps(out,indent=2)+'\n');lines=[]
for e in edges:
 lines.append('module panel_signal_'+e['id']+'(){')
 for a,b in zip(e['points_mm'],e['points_mm'][1:]):lines.append('hull(){translate('+json.dumps(a)+')sphere(r=.6,$fn=32);translate('+json.dumps(b)+')sphere(r=.6,$fn=32);}')
 lines.append('}')
lines.append('module panel_next_inputs(){panel_signal_S04();}');(HERE/'routes.scad').write_text('\n'.join(lines)+'\n')
# Verification-only outer tube: fn32 sphere radius .87 contains the ideal .85 sphere.
# This is .25 mm additional receiving margin around the .6 mm physical wire radius.
clearance=['// Verification only: .87 fn32 contains ideal .85 outer sphere.']
for e in edges:
 clearance.append('module clearance_'+e['id']+'(){')
 for a,b in zip(e['points_mm'],e['points_mm'][1:]):clearance.append('hull(){translate('+json.dumps(a)+')sphere(r=.87,$fn=32);translate('+json.dumps(b)+')sphere(r=.87,$fn=32);}')
 clearance.append('}')
clearance.append('module next_input_control_clearance(){clearance_S04();}')
(HERE/'clearance.scad').write_text('\n'.join(clearance)+'\n')
