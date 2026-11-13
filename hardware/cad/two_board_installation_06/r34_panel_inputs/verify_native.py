"""Bind accepted and rejected native S04 evidence to exact source snapshots."""
import hashlib,json
from pathlib import Path
H=Path(__file__).resolve().parent;R=H.parents[3]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
rejected={'r1':'rejected-r1-mesh','r2':'rejected-r2-receiving','r3':'rejected-r3-control-margin','r4':'rejected-r4-mesh','r5':'rejected-r5-mesh'}
rows=[]
for folder in sorted((H/'native').iterdir()):
 if not folder.is_dir():continue
 part,revision=folder.name.rsplit('-',1);v=json.loads((folder/'result.json').read_text())
 assert not v['runtime_failure']
 for name,digest in v['source_sha256'].items():
  p=R/name
  if revision in rejected and p.parent==H and p.name in ['routes.scad','clearance.scad','probe.scad']:
   p=H/rejected[revision]/p.name
  assert sha(p)==digest,(folder.name,name)
 if revision=='r6':
  if part=='positive':assert v['mesh']['closed_oriented_boundary'] and v['mesh']['volume_mm3']>0
  else:assert v['empty'] and v['mesh'] is None,folder.name
 if revision in ('r4','r5') and part=='positive':assert not v['mesh']['closed_oriented_boundary']
 if revision=='r1':assert part=='positive' and not v['mesh']['closed_oriented_boundary']
 if (revision,part) in [('r2','receiving'),('r3','controls_clearance')]:assert v['mesh']['closed_oriented_boundary'] and v['mesh']['volume_mm3']>0
 rows.append({'job':folder.name,'empty':v['empty'],'mesh':v['mesh'],'artifact_sha256':{str(p.relative_to(R)):sha(p) for p in sorted(folder.iterdir()) if p.is_file()}})
assert {r['job'] for r in rows if r['job'].endswith('-r6')}=={p+'-r6' for p in ['positive','receiving','wires','structure','controls_clearance','future_touch']}
for name in ['routes.json','verification.json','mutation-tests.json']:
 data=json.loads((H/name).read_text())
 for path,digest in data['source_sha256'].items():assert sha(R/path)==digest,(name,path)
out={'status':'LOCAL_CANDIDATE_CLEAR_ROOT_REVIEW_PENDING','selected':False,'physical_termination_qualified':False,'opening_slack_qualified':False,'rejected_witnesses_retained':list(rejected),'cases':rows,'source_sha256':{str(p.relative_to(R)):sha(p) for p in [Path(__file__),H/'routes.json',H/'routes.scad',H/'clearance.scad',H/'verification.json',H/'mutation-tests.json']}}
(H/'native-verification.json').write_text(json.dumps(out,indent=2)+'\n');print(out['status'])
