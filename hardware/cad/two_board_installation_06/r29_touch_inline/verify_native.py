"""Bind a local candidate checkpoint to fresh native evidence; no full-fit claim."""
import json,hashlib
from pathlib import Path
from hardware.cad.a12.thermal.enlarged_base.verify import mesh
H=Path(__file__).resolve().parent;R=H.parents[3]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
records={}
for case in ['population','controls','sensor','ground_supports','mutual','positive']:
 p=H/'native'/(case+'-r6')/'result.json';v=json.loads(p.read_text())
 for n,h in v['source_sha256'].items():assert sha(R/n)==h,n
 assert not v['runtime_failure']
 if case=='positive':assert v['mesh']['closed_oriented_boundary'] and mesh(p.parent/'positive.stl')==v['mesh']
 else:assert v['empty'] and not list(p.parent.glob('*.stl'))
 records[case]={'evidence':str(p.relative_to(R)),'sha256':sha(p),'artifacts':{str(q.relative_to(R)):sha(q) for q in p.parent.iterdir() if q.suffix in ['.log','.stl']}}
for rev in ['r1','r2','r3','r4','r5']:
 for p in (H/'native').glob('*-'+rev+'/result.json'):
  v=json.loads(p.read_text())
  for n,s in v['source_sha256'].items():
   f=R/n
   if f.name in ['probe.scad','route-draft.scad']:f=H/('rejected-'+rev)/f.name
   assert sha(f)==s,(p,n)
a=json.loads((H/'verification.json').read_text());assert a['minimum_join_dot']>=1-1e-9
for n,s in a['source_sha256'].items():assert sha(R/n)==s
s=json.loads((H/'separation.json').read_text());assert s['passes']
for n,h in s['source_sha256'].items():assert sha(R/n)==h
r={'status':'LOCAL_CONDITIONAL_RECEIVING_STUDY','native':records,'source_sha256':{str(p.relative_to(R)):sha(p) for p in [Path(__file__),H/'separation.py',H/'separation.json',H/'verification.json',H/'parts-study.json']},'minimum_wire_surface_gap_bound_mm':s['surface_gap_lower_bound_mm'],'minimum_bend_radius_mm':13,'completed_touch_wires':0,'completed_panel_edges':0,'full_assembly_checked':False,'termination_support_tooling_qualified':False}
(H/'native-verification.json').write_text(json.dumps(r,indent=2)+'\n');print(r['status'])
