"""Bind rejected and accepted native pair evidence without changing frozen sources."""
import hashlib,json
from pathlib import Path
H=Path(__file__).resolve().parent;R=H.parents[3]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
parts=['positive','positive_S08','positive_S09','controls_clearance','receiving','wires','structure','future_touch','original_controls']
rows=[]
for revision in ['r1','r2','r3','r4']:
 for part in parts:
  folder=H/'native'/(part+'-'+revision);v=json.loads((folder/'result.json').read_text())
  assert not v['runtime_failure']
  for name,digest in v['source_sha256'].items():
   p=R/name
   if revision in ['r1','r2','r3'] and p.parent==H and (H/('rejected-'+revision)/p.name).exists():p=H/('rejected-'+revision)/p.name
   assert sha(p)==digest,(part,revision,name)
  if revision=='r4':
   if part.startswith('positive'):assert not v['empty'] and v['mesh']['closed_oriented_boundary'] and v['mesh']['volume_mm3']>0
   else:assert v['empty'] and v['mesh'] is None,part
  elif revision=='r1':
   if part.startswith('positive'):assert not v['mesh']['closed_oriented_boundary']
   elif part in ['wires','future_touch']:assert v['empty']
   else:assert v['mesh']['closed_oriented_boundary'] and v['mesh']['volume_mm3']>0
  else:
   if part.startswith('positive'):assert v['mesh']['closed_oriented_boundary']
   elif part=='receiving':assert v['mesh']['closed_oriented_boundary'] and v['mesh']['volume_mm3']>0
   else:assert v['empty']
  rows.append({'job':folder.name,'empty':v['empty'],'mesh':v['mesh'],'artifact_sha256':{str(p.relative_to(R)):sha(p) for p in sorted(folder.iterdir()) if p.is_file()}})
for name in ['routes.json','verification.json','mutation-tests.json','pair-planning.json','capacitor-clearance.json']:
 for path,digest in json.loads((H/name).read_text())['source_sha256'].items():assert sha(R/path)==digest,(name,path)
sources=[Path(__file__),H/'routes.json',H/'routes.scad',H/'clearance.scad',H/'source-audit.scad',H/'verification.json',H/'mutation-tests.json',H/'pair-planning.json',H/'capacitor-clearance.json']+list((H/'rejected-r1').iterdir())+list((H/'rejected-r2').iterdir())+list((H/'rejected-r3').iterdir())
out={'status':'LOCAL_CANDIDATE_CLEAR_ROOT_REVIEW_PENDING','selected':False,'physical_termination_qualified':False,'opening_slack_qualified':False,'accepted_revision':'r4','cases':rows,'source_sha256':{str(p.relative_to(R)):sha(p) for p in sources if p.is_file()}}
(H/'native-verification.json').write_text(json.dumps(out,indent=2)+'\n');print(out['status'])
