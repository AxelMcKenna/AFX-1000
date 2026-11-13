"""Bind final and rejected native artifacts; no positive-volume intersection waiver."""
import hashlib,json
from pathlib import Path
from hardware.cad.a12.thermal.enlarged_base.verify import mesh
H=Path(__file__).resolve().parent;R=H.parents[3]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
full=['positive_clearance','positive','positive_S12','positive_S13','controls_clearance','receiving','wires','structure','future_touch','original_controls','lid_guide']
parts={'r1':['positive','positive_clearance'],'r2':['positive_clearance'],'r3':['positive_clearance'],'r4':full,'r5':['positive_clearance'],'r6':['positive_clearance'],'r7':full,'r8':['positive_clearance','positive'],'r9':[x for x in full if x!='positive_clearance']}
rows=[]
for revision,jobs in parts.items():
 for part in jobs:
  folder=H/'native'/(part+'-'+revision);v=json.loads((folder/'result.json').read_text());stl=folder/(part+'.stl')
  assert not v['runtime_failure']
  if v['empty']:assert not stl.exists() and v['mesh'] is None
  else:assert mesh(stl)==v['mesh'],('Mesh artifact changed',folder)
  for path,digest in v['source_sha256'].items():
   p=R/path
   if revision!='r9' and not (revision=='r8' and part=='positive_clearance') and p.parent==H and (H/('rejected-'+revision)/p.name).exists():p=H/('rejected-'+revision)/p.name
   assert sha(p)==digest,(folder,path)
  if part.startswith('positive'):
   assert not v['empty'] and v['mesh']['volume_mm3']>0
   assert v['mesh']['closed_oriented_boundary']==(not ((part=='positive_clearance' and revision in ['r1','r2','r3','r6']) or (part=='positive' and revision=='r8')))
  elif (revision=='r4' and part in ['receiving','future_touch']) or (revision=='r7' and part in ['controls_clearance','structure','original_controls']):
   assert not v['empty'] and v['mesh']['closed_oriented_boundary'] and v['mesh']['volume_mm3']>0
  else:assert v['empty'],('Intersection is not empty',folder)
  rows.append({'job':folder.name,'empty':v['empty'],'mesh':v['mesh'],'artifact_sha256':{str(p.relative_to(R)):sha(p) for p in sorted(folder.iterdir()) if p.is_file()}})
assert {r['job'] for r in rows}=={p.name for p in (H/'native').iterdir() if p.is_dir()}
for name in ['routes.json','verification.json','mutation-tests.json','allocation-clearance.json']:
 for path,digest in json.loads((H/name).read_text())['source_sha256'].items():assert sha(R/path)==digest,(name,path)
sources=[Path(__file__),R/'hardware/cad/a12/thermal/enlarged_base/verify.py',H/'routes.json',H/'routes.scad',H/'clearance.scad',H/'verification.json',H/'mutation-tests.json',H/'allocation-clearance.json']
for n in range(1,9):sources+=list((H/('rejected-r'+str(n))).iterdir())
out={'status':'LOCAL_CANDIDATE_CLEAR_ROOT_REVIEW_PENDING','selected':False,'physical_termination_qualified':False,'opening_slack_qualified':False,'accepted_revision':'r9', 'accepted_unchanged_margin_revision':'r8','cases':rows,'rejected_r5_host_wire_crossing_retained':True,'source_sha256':{str(p.relative_to(R)):sha(p) for p in sources if p.is_file()}}
(H/'native-verification.json').write_text(json.dumps(out,indent=2)+'\n');print(out['status'])
