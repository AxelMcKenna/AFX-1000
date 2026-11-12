"""Conservative receiving envelopes for the candidate dual-row panel connectors."""
import json,hashlib
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
manifest=ROOT/'hardware/cad/two_board_installation_06/r7/interface-manifest.json';cap=ROOT/'hardware/cad/two_board_print_01/capture.json'
m=json.loads(manifest.read_text());d=json.loads(cap.read_text())
refs=['D_J3002','D_J3003','D_J3004','D_J3005','D_J2001','D_J2002']
rows=[]
for j in m['interfaces']:
 if j['reference'] not in refs:continue
 n=len(j['pads']);cx=sum(p['xy'][0] for p in j['pads'])/n;cy=sum(p['xy'][1] for p in j['pads'])/n
 length=33.22 if n==26 else 20.52
 rows.append({'ref':j['reference'],'male':'901310133' if n==26 else '901310128','female':'901420026' if n==26 else '901420016','contact':'901192120','center_xy':[cx,cy],'latch_side':'negative Y','boxes':[[cx-length/2,cy-3.1,10.65,cx+length/2,cy+3.1,26.44],[cx-2,cy-4.9,10.65,cx+2,cy-3.1,26.44],[cx-n/4*2.54,cy-2.54,8.35,cx+n/4*2.54,cy+2.54,11.05]]})
obs=[[r,xy[0],xy[1],z[0],xy[2],xy[3],z[1]] for r,xy,z in d['component_envelopes']+d['tail_envelopes'] if r not in refs]
obs += [[r['id'],r['xy'][0],r['xy'][1],r['z'][0],r['xy'][2],r['xy'][3],r['z'][1]] for r in d['context']]
sc='// Candidate receiving reservation, not manufacturer-certified assembly CAD.\npart="installed";\nmodule tbh10_box(b){translate([b[0],b[1],b[2]])cube([b[3]-b[0],b[4]-b[1],b[5]-b[2]]);}\n'
sc+='module tbh10_panel_mates(){\n'+''.join('tbh10_box('+json.dumps(b)+');\n' for r in rows for b in r['boxes'])+'}\n'
sc+='module tbh10_obstacles(){\n'+''.join('tbh10_box('+json.dumps(r[1:])+');\n' for r in obs)+'}\n'
sc+='if(part=="installed")tbh10_panel_mates();\nif(part=="components")intersection(){tbh10_panel_mates();tbh10_obstacles();}\nif(part=="positive")intersection(){translate([0,3,0])tbh10_panel_mates();tbh10_obstacles();}\n'
(HERE/'panel_mates.scad').write_text(sc)
(HERE/'mate-envelopes.json').write_text(json.dumps({'scope':'Conditional receiving reservation; pending controlled female drawing/actual seated stack and keyed retention. Source geometry unchanged. Native tests demonstrate only these declared bounds.','project_receiving_limits':{'female_body_width_max':6.2,'female_height_max':15.39,'seated_bottom_z_range':[10.65,11.05],'female_top_z_max':26.44,'latch_width_max':4,'latch_extent_from_row_center_max':4.9,'latch_side':'negative Y','board_top_z':8.35},'mates':rows,'source_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [manifest,cap,Path(__file__)]}},indent=2)+'\n')
