"""Independent NUDGE UP source exit and complete receiving route."""
import hashlib,json,math
from pathlib import Path
from hardware.cad.two_board_installation_06.r38_nudge_up.search_corridor import route
H=Path(__file__).resolve().parent;R=H.parents[3];B=H.parent
w=route(150,29.6)
edges=[dict(id='S07',source='D_J2001:5',target='button_nudge_up:1',net='/D_CONTROLS/CONTROL_04',wire='Alpha5853 26AWG7/34',points_mm=[p.tolist() for p in w.points],primitives=w.primitives)]
sources=[Path(__file__),H/'search_corridor.py',B/'r15_right_ground/curves.py',B/'r37_tap_auto/routes.json',B/'r37_tap_auto/verification.json',B/'r12_ground/ground-routes.json',B/'r34_panel_inputs/routes.json',B/'r22_ground_signal_clearance/bows.json']
(H/'routes.json').write_text(json.dumps(dict(edges=edges,wire_radius_mm=.6,required_centerline_radius_mm=12,requires_r37_candidate=True,fabrication_released=False,opening_slack_qualified=False,source_sha256={str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}),indent=2)+'\n')
for filename,radius,prefix,group in [('routes.scad',.6,'panel_signal_','panel_nudge_up'),('clearance.scad',.88,'clearance_','nudge_up_control_clearance')]:
 lines=[]
 for e in edges:
  lines.append('module '+prefix+e['id']+'(){')
  for a,b in zip(e['points_mm'],e['points_mm'][1:]):lines.append('hull(){translate('+json.dumps(a)+')rotate([11,7,3])sphere(r='+str(radius).lstrip('0')+',$fn=24);translate('+json.dumps(b)+')rotate([11,7,3])sphere(r='+str(radius).lstrip('0')+',$fn=24);}')
  lines.append('}')
 lines.append('module '+group+'(){'+''.join(prefix+e['id']+'();' for e in edges)+'}')
 (H/filename).write_text('\n'.join(lines)+'\n')
