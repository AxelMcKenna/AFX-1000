from pathlib import Path
import json,math,numpy as np,shutil
from hardware.cad.two_board_installation_06.r15_right_ground.curves import Wire
H=Path('hardware/cad/two_board_installation_06/r29_touch_inline'); prior=json.loads((H.parent/'r27_touch_host/direct-exits.json').read_text()); host=json.loads((H.parent/'r26_touch_mount/contract.json').read_text())
rows=[]
for i,(old,info) in enumerate(zip(prior['edges'],host['wires'])):
 w=Wire(old['points_mm'][0]);w.points=[np.array(p) for p in old['points_mm'][:-1]];w.primitives=old['primitives'][:-1]
 w.line([185+2*i,w.p[1],27]);w.arc([-1,0,0],[0,1,0],13,90);w.line([w.p[0],113.5,27])
 v=Wire([172+2*i,136.5,27]);y=info['trill_xy_mm'][1]
 if i==3:
  v.line([v.p[0],138,27]);v.s_curve([0,1,0],[0,0,1],13,5)
 v.line([v.p[0],y-13,v.p[2]]);v.arc([0,1,0],[-1,0,0],13,90);v.line([137,y,v.p[2]]);v.s_curve([-1,0,0],[0,0,1],13,35.25-v.p[2]);v.line([97.1971,y,35.25]);v.arc([-1,0,0],[0,0,-1],13,90)
 rows.append({'id':old['id'],'host':old['source'],'net':info['net'],'trill_pin':info['trill_pin'],'cavity_project':i+1,'segments':[{'points_mm':[p.tolist() for p in z.points],'primitives':z.primitives} for z in [w,v]]})
(H/'route-draft.json').write_text(json.dumps({'edges':rows,'status':'UNVERIFIED_RECEIVING_STUDY','completed_touch_wires':0,'completed_panel_edges':0,'wire_radius_mm':.65,'bend_radius_mm':13,'connector_box_mm':[[169.5,113.5,21.5],[180.5,136.5,32.5]],'connector_status':'Project receiving envelope; no controlled housing tolerances or terminal exit registration yet. No installed part or solder termination claim.'},indent=2)+'\n')
s=['module touch_inline_receiving(){translate([169.5,113.5,21.5])cube([11,23,11]);}']
for row in rows:
 s.append('module touch_wire_'+row['id']+'(){')
 for seg in row['segments']:
  for a,b in zip(seg['points_mm'],seg['points_mm'][1:]):s.append('hull(){translate('+json.dumps(a)+')sphere(r=.65,$fn=32);translate('+json.dumps(b)+')sphere(r=.65,$fn=32);}')
 s.append('}')
s.append('module touch_wires(){'+''.join('touch_wire_'+r['id']+'();' for r in rows)+'}');s.append('module touch_candidate(){touch_wires();touch_inline_receiving();}')
(H/'route-draft.scad').write_text('\n'.join(s)+'\n')
shutil.copy(H.parent/'r27_touch_host/run.py',H/'run.py')
probe=(H.parent/'r27_touch_host/probe.scad').read_text().replace('use <direct-exits.scad>','use <route-draft.scad>').replace('use <sensor-source-extract.scad>','use <../r27_touch_host/sensor-source-extract.scad>').replace('use <population.scad>','use <../r27_touch_host/population.scad>').replace('touch_direct_exits()','touch_candidate()')
probe+='\nif(part=="mutual")union(){intersection(){touch_wire_TH1();touch_wire_TH2();}intersection(){touch_wire_TH1();touch_wire_TH3();}intersection(){touch_wire_TH1();touch_wire_TH4();}intersection(){touch_wire_TH2();touch_wire_TH3();}intersection(){touch_wire_TH2();touch_wire_TH4();}intersection(){touch_wire_TH3();touch_wire_TH4();}}\n'
(H/'probe.scad').write_text(probe)
