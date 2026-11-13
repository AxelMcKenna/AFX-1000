"""Bind every final/rejected native case and require closed operands and EMPTY intersections."""
import hashlib,json
from pathlib import Path
from hardware.cad.a12.thermal.enlarged_base.verify import mesh
H=Path(__file__).resolve().parent;R=H.parents[3]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
base_parts=['positive','positive_S10','positive_S11','controls_clearance','receiving','wires','structure','future_touch','original_controls']
empty_old={'r1':{'wires','future_touch'},'r2':{'receiving','wires','future_touch'},'r3':{'receiving','wires','structure','future_touch','lid_guide'},'r4':set()}
rows=[]
for revision in ['r1','r2','r3','r4','r5','r6','r7']:
 parts=(['original_controls'] if revision=='r4' else ['positive_clearance'] if revision=='r6' else base_parts+(['lid_guide'] if revision in ['r3','r5','r7'] else [])+(['positive_clearance'] if revision in ['r5','r7'] else []))
 for part in parts:
  folder=H/'native'/(part+'-'+revision);v=json.loads((folder/'result.json').read_text())
  assert not v['runtime_failure']
  stl=folder/(part+'.stl')
  if v['empty']:assert not stl.exists()
  else:assert mesh(stl)==v['mesh'],('STL differs from recorded mesh',part,revision)
  for name,digest in v['source_sha256'].items():
   p=R/name
   if revision!='r7' and p.parent==H and (H/('rejected-'+revision)/p.name).exists():p=H/('rejected-'+revision)/p.name
   assert sha(p)==digest,(part,revision,name)
  if part.startswith('positive'):
   rejected=revision=='r1' or (part=='positive_clearance' and revision in ['r5','r6'])
   assert not v['empty'] and v['mesh']['volume_mm3']>0
   assert v['mesh']['closed_oriented_boundary']==(not rejected),(part,revision)
  elif revision in ['r5','r7'] or part in empty_old[revision]:assert v['empty'] and v['mesh'] is None,(part,revision)
  else:assert not v['empty'] and v['mesh']['closed_oriented_boundary'] and v['mesh']['volume_mm3']>0
  rows.append({'job':folder.name,'empty':v['empty'],'mesh':v['mesh'],'artifact_sha256':{str(p.relative_to(R)):sha(p) for p in sorted(folder.iterdir()) if p.is_file()}})
assert {x['job'] for x in rows}=={p.name for p in (H/'native').iterdir() if p.is_dir()}
for name in ['routes.json','verification.json','mutation-tests.json']:
 for path,digest in json.loads((H/name).read_text())['source_sha256'].items():assert sha(R/path)==digest,(name,path)
assert all(sha(H/'routes.scad')==sha(H/('rejected-r'+str(n))/'routes.scad') for n in [3,4,5,6])
sources=[R/'hardware/cad/a12/thermal/enlarged_base/verify.py',Path(__file__),H/'routes.json',H/'routes.scad',H/'clearance.scad',H/'source-audit.scad',H/'lid-audit.scad',H/'clearance-positive.scad',H/'verification.json',H/'mutation-tests.json']
for n in range(1,7):sources+=list((H/('rejected-r'+str(n))).iterdir())
out={'physical_wire_scad_unchanged_since_r3':True,'status':'LOCAL_CANDIDATE_CLEAR_ROOT_REVIEW_PENDING','selected':False,'physical_termination_qualified':False,'opening_slack_qualified':False,'accepted_revision':'r7','cases':rows,'source_sha256':{str(p.relative_to(R)):sha(p) for p in sources if p.is_file()}}
(H/'native-verification.json').write_text(json.dumps(out,indent=2)+'\n');print(out['status'])
