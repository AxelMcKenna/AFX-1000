"""Validate all bounded native jobs and source/artifact identities."""
import hashlib,json
from pathlib import Path
H=Path(__file__).resolve().parent;R=H.parents[3]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
parts=['positive','positive_S05','positive_S06','controls_clearance','receiving','wires','structure','future_touch']
rows=[]
for part in parts:
 folder=H/'native'/(part+'-r1');v=json.loads((folder/'result.json').read_text())
 assert not v['runtime_failure']
 for name,digest in v['source_sha256'].items():assert sha(R/name)==digest,(part,name)
 if part.startswith('positive'):assert not v['empty'] and v['mesh']['closed_oriented_boundary'] and v['mesh']['volume_mm3']>0
 else:assert v['empty'] and v['mesh'] is None,part
 rows.append({'job':folder.name,'empty':v['empty'],'mesh':v['mesh'],'artifact_sha256':{str(p.relative_to(R)):sha(p) for p in sorted(folder.iterdir()) if p.is_file()}})
for name in ['routes.json','verification.json','mutation-tests.json']:
 for path,digest in json.loads((H/name).read_text())['source_sha256'].items():assert sha(R/path)==digest,(name,path)
out={'status':'LOCAL_CANDIDATE_CLEAR_ROOT_REVIEW_PENDING','selected':False,'physical_termination_qualified':False,'holder_strength_qualified':False,'opening_slack_qualified':False,'cases':rows,'source_sha256':{str(p.relative_to(R)):sha(p) for p in [Path(__file__),H/'routes.json',H/'routes.scad',H/'control_variant.scad',H/'clearance.scad',H/'verification.json',H/'mutation-tests.json']}}
(H/'native-verification.json').write_text(json.dumps(out,indent=2)+'\n');print(out['status'])
