from pathlib import Path
import json,hashlib,math,numpy as np
from hardware.cad.two_board_installation_06.r15_right_ground.curves import Wire
HERE=Path(__file__).resolve().parent;BASE=HERE.parent;REPO=HERE.parents[3]
sources=[Path(__file__),BASE/'r15_right_ground/curves.py',BASE/'r19_panel_inventory/inventory.json',BASE/'r12_ground/ground-routes.json',BASE/'r10_interfaces/mate-envelopes.json']
i=json.loads(sources[2].read_text());row=next(w for w in i['wires'] if w['target']=='button_scene_2:1');assert row['source']=='D_J2002:2' and row['net']=='/D_CONTROLS/CONTROL_21'
end=json.loads(sources[3].read_text())['endpoints_mm']['button_scene_2:1'];start=row['source_xy_mm']+[27.04]
az=math.radians(210);T=[math.cos(az),math.sin(az),0]
w=Wire(start);w.arc([0,0,1],T,12,90);w.s_curve(T,[0,0,-1],12,39.04-28.2)
w.arc(T,[-T[1],T[0],0],14,150);w.line([264,w.p[1],28.2]);w.arc([1,0,0],[0,1,0],14,180)
dy=end[1]-w.p[1];w.s_curve([-1,0,0],[0,dy,3.4],14,math.hypot(dy,3.4));w.line(end)

out=dict(source_sha256={str(p.relative_to(REPO)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},edges=[dict(id='S01',source=row['source'],target=row['target'],net=row['net'],wire='Alpha5853 26AWG7/34',points_mm=[p.tolist() for p in w.points],primitives=w.primitives)],wire_radius_mm=.6,required_centerline_radius_mm=12,receiving_mate='Molex901420016 / contact901192120 / male901310128; r10 conditional receiving limits',fabrication_released=False,opening_slack_qualified=False)
(HERE/'route.json').write_text(json.dumps(out,indent=2)+'\n');lines=['module panel_scene_signal(){']
for a,b in zip(w.points,w.points[1:]):lines.append('hull(){translate('+json.dumps(a.tolist())+')sphere(r=.6,$fn=28);translate('+json.dumps(b.tolist())+')sphere(r=.6,$fn=28);}')
lines.append('}');(HERE/'route.scad').write_text('\n'.join(lines)+'\n')
