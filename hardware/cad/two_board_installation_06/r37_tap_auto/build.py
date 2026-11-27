"""Paired independent TAP/AUTO routes using the exact staged R36 exits."""
import hashlib,json,math
from pathlib import Path
from hardware.cad.two_board_installation_06.r15_right_ground.curves import Wire
H=Path(__file__).resolve().parent;R=H.parents[3];B=H.parent
exits=json.loads((B/'r36_scene0_relief/exits.json').read_text());datums=json.loads((B/'r12_ground/ground-routes.json').read_text())['endpoints_mm'];edges=[]
for old,low,turn_y,shift_y,lane in zip(exits['edges'],[29.6,31.2],[90,93],[75,77],[181.75,183.5]):
 p=old['primitives'][0];w=Wire(p['start']);w.arc(p['tangent'],p['normal'],p['radius_mm'],p['angle_degrees']);T=p['normal'];end=datums[old['target']]
 w.s_curve(T,[0,0,-1],12,w.p[2]-low)
 w.arc(T,[T[1],-T[0],0],12,39.6)
 assert w.p[1]<turn_y;w.line([w.p[0],turn_y,low]);w.arc([0,1,0],[1,0,0],12,180)
 assert w.p[1]>shift_y;w.line([w.p[0],shift_y,low]);dx=w.p[0]-lane;assert dx>0
 if dx>24:
  w.arc([0,-1,0],[-1,0,0],12,90);w.line([lane+12,w.p[1],low]);w.arc([-1,0,0],[0,-1,0],12,90)
 else:w.s_curve([0,-1,0],[-1,0,0],12,dx)
 if lane!=end[0]:
  assert w.p[1]>38;w.line([lane,38,low]);w.s_curve([0,-1,0],[-1,0,0],12,lane-end[0])
 rise=end[2]-low;run=24*math.sin(math.acos(1-rise/24));assert w.p[1]>=end[1]+run
 w.line([end[0],end[1]+run,low]);w.s_curve([0,-1,0],[0,0,1],12,rise)
 edges.append(dict(id=old['id'],source=old['source'],target=old['target'],net=old['net'],wire='Alpha5853 26AWG7/34',points_mm=[p.tolist() for p in w.points],primitives=w.primitives))
sources=[Path(__file__),B/'r15_right_ground/curves.py',B/'r36_scene0_relief/exits.json',B/'r36_scene0_relief/verification.json',B/'r19_panel_inventory/inventory.json',B/'r12_ground/ground-routes.json',B/'r34_panel_inputs/routes.json',B/'r22_ground_signal_clearance/bows.json']
(H/'routes.json').write_text(json.dumps(dict(edges=edges,wire_radius_mm=.6,required_centerline_radius_mm=12,requires_scene0_relief='r36',requires_S04_candidate=True,fabrication_released=False,opening_slack_qualified=False,source_sha256={str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}),indent=2)+'\n')
for filename,radius,prefix,group in [('routes.scad',.6,'panel_signal_','panel_tap_auto'),('clearance.scad',.88,'clearance_','tap_auto_control_clearance')]:
 lines=[]
 for e in edges:
  lines.append('module '+prefix+e['id']+'(){')
  for a,b in zip(e['points_mm'],e['points_mm'][1:]):lines.append('hull(){translate('+json.dumps(a)+')rotate([11,7,3])sphere(r='+str(radius).lstrip('0')+',$fn=24);translate('+json.dumps(b)+')rotate([11,7,3])sphere(r='+str(radius).lstrip('0')+',$fn=24);}')
  lines.append('}')
 lines.append('module '+group+'(){'+''.join(prefix+e['id']+'();' for e in edges)+'}')
 (H/filename).write_text('\n'.join(lines)+'\n')
