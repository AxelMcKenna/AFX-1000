"""Verify conditional replacement hardware evidence; no mounting qualification."""
import json,hashlib
from pathlib import Path
from hardware.cad.a12.thermal.enlarged_base.verify import mesh
H=Path(__file__).resolve().parent;R=H.parents[3];sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
c=json.loads((H/'hardware-budget.json').read_text())
for n,h in c['source_sha256'].items():assert sha(R/n)==h,n
assert c['mount']=='H_NEW5' and not c['nut_pocket_changed'] and not c['sensor_owned_mounts_changed']
records={}
for case in ['positive','receiver_positive','population','controls','wires','raw_support','raw_shell']:
 p=H/'native'/(case+'-hardware1')/'result.json';v=json.loads(p.read_text())
 for n,h in v['source_sha256'].items():assert sha(R/n)==h,n
 assert not v['runtime_failure']
 if case.endswith('positive'):
  assert v['mesh']['closed_oriented_boundary'] and v['mesh']['degenerate_triangles_excluded']==0 and mesh(p.parent/(case+'.stl'))==v['mesh'];status='CLOSED_POSITIVE'
 elif case.startswith('raw_'):
  m=v['mesh'];expected=12.5 if case=='raw_support' else 1.8;assert mesh(p.parent/(case+'.stl'))==m and m['volume_mm3']<1e-9 and m['min_mm'][2]==m['max_mm'][2] and abs(m['min_mm'][2]-expected)<1e-6
  assert m['min_mm'][0]>=161.29 and m['max_mm'][0]<=166.71 and m['min_mm'][1]>=110.29 and m['max_mm'][1]<=115.71;status='RAW_SEAT_PLANE_ONLY_NOT_WAIVED_SOLID'
 else:assert v['empty'] and not list(p.parent.glob('*.stl'));status='EMPTY'
 records[case]={'status':status,'result_sha256':sha(p),'artifacts':{str(q.relative_to(R)):sha(q) for q in p.parent.iterdir() if q.suffix in ['.log','.stl']}}
r={'status':'CONDITIONAL_REPLACEMENT_STACK_VERIFIED','mount':'H_NEW5','source_sha256':{str(p.relative_to(R)):sha(p) for p in [Path(__file__),H/'hardware-budget.json',H/'hardware.scad']},'native':records,'budget':c['budget'],'full_assembly_checked':False,'physical_qualified':False,'only_old_head_to_replace':{'xy':[164,113],'diameter':4.5,'z':[9.5,12.]},'nut_pocket_changed':False,'completed_touch_wires':0}
(H/'hardware-verification.json').write_text(json.dumps(r,indent=2)+'\n');print(r['status'])
