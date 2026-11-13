"""Verify bounded r26 nut-tool access; never qualify mounting strength/process."""
import json,hashlib,re
from pathlib import Path
from hardware.cad.a12.thermal.enlarged_base.verify import mesh
H=Path(__file__).resolve().parent;R=H.parents[3];sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
centres=json.loads(re.search(r'r30_centres=(.*);', (H/'tools.scad').read_text()).group(1))
owner=json.loads((H.parent/'r25_touch_module/contract.json').read_text());assert centres==owner['mount_centres_mm']
c=json.loads((H.parent/'r26_touch_mount/contract.json').read_text());limits=c['receiving_requirements_mm']
assert limits['pocket_AF'][0]==4.15 and limits['pocket_ceiling'][1]==4.9 and c['supplier_mm']['nut_height'][0]==1.35
radial=(limits['pocket_AF'][0]-3.6)/2-.1;bore=(2.3-2)/2-.1;assert radial>0 and bore>0
assert abs(limits['pocket_ceiling'][1]-c['supplier_mm']['nut_height'][0]-3.55)<1e-8
records={}
for case in ['positive','access_positive','access_shell','nominal_hardware']:
 p=H/'native'/(case+'-r1')/'result.json';v=json.loads(p.read_text())
 for n,h in v['source_sha256'].items():assert sha(R/n)==h,n
 assert not v['runtime_failure']
 if case.endswith('positive'):assert v['mesh']['closed_oriented_boundary'] and v['mesh']['degenerate_triangles_excluded']==0 and mesh(p.parent/(case+'.stl'))==v['mesh']
 else:assert v['empty'] and not list(p.parent.glob('*.stl'))
 records[case]={'result_sha256':sha(p),'artifacts':{str(q.relative_to(R)):sha(q) for q in p.parent.iterdir() if q.suffix in ['.log','.stl']}}
r={'status':'CONDITIONAL_TOOL_ACCESS_ONLY','minimum_tool_pocket_radial_clearance_mm':radial,'minimum_screw_bore_radial_clearance_mm':bore,'maximum_tool_tip_z_mm':3.55,'native':records,'source_sha256':{str(p.relative_to(R)):sha(p) for p in [Path(__file__),H/'tools.scad',H.parent/'r26_touch_mount/contract.json',H.parent/'r25_touch_module/contract.json']},'full_current_assembly_checked':False,'washer_alignment_qualified':False,'nut_bearing_face_qualified':False,'tightening_strength_qualified':False}
(H/'verification.json').write_text(json.dumps(r,indent=2)+'\n');print(r['status'])
