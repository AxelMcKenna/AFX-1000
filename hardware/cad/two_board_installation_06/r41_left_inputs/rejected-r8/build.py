"""NUDGE DOWN and SOURCE INPUT formed receiving routes."""
import hashlib,json,math
from pathlib import Path
from hardware.cad.two_board_installation_06.r41_left_inputs.search_corridor import route_west_rise,route_source_low_west
H=Path(__file__).resolve().parent;R=H.parents[3];B=H.parent
edges=[]
for id,source,target,net,w in [('S12','D_J2001:7','button_nudge_down:1','/D_CONTROLS/CONTROL_03',route_west_rise(130,25.2,127,145)),('S13','D_J2001:3','button_source_input:1','/D_CONTROLS/CONTROL_05',route_source_low_west(155,24.6,2.5,27.8,150))]:
 edges.append(dict(id=id,source=source,target=target,net=net,wire='Alpha5853 26AWG7/34',points_mm=[p.tolist() for p in w.points],primitives=w.primitives))
sources=[Path(__file__),H/'search_corridor.py',B/'r15_right_ground/curves.py',B/'r40_isolate_upper_pair/routes.json',B/'r40_isolate_upper_pair/verification.json',B/'r39_isolate_pair/routes.json',B/'r39_isolate_pair/verification.json',B/'r38_nudge_up/routes.json',B/'r38_nudge_up/verification.json',B/'r37_tap_auto/routes.json',B/'r37_tap_auto/verification.json',B/'r12_ground/ground-routes.json',B/'r34_panel_inputs/routes.json',B/'r22_ground_signal_clearance/bows.json']
(H/'routes.json').write_text(json.dumps(dict(edges=edges,wire_radius_mm=.6,required_centerline_radius_mm=12,requires_r37_candidate=True,fabrication_released=False,opening_slack_qualified=False,source_sha256={str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}),indent=2)+'\n')
for filename,radius,prefix,group in [('routes.scad',.6,'panel_signal_','panel_left_inputs'),('clearance.scad',.863,'clearance_','left_inputs_control_clearance')]:
 facets=24 if filename=="routes.scad" else 32
 rotation="[11,7,3]" if filename=="routes.scad" else "[17,23,31]"
 lines=[]
 for e in edges:
  lines.append('module '+prefix+e['id']+'(){')
  for a,b in zip(e['points_mm'],e['points_mm'][1:]):lines.append('hull(){translate('+json.dumps(a)+')rotate('+rotation+')sphere(r='+str(radius).lstrip('0')+',$fn='+str(facets)+');translate('+json.dumps(b)+')rotate('+rotation+')sphere(r='+str(radius).lstrip('0')+',$fn='+str(facets)+');}')
  lines.append('}')
 lines.append('module '+group+'(){'+''.join(prefix+e['id']+'();' for e in edges)+'}')
 (H/filename).write_text('\n'.join(lines)+'\n')
