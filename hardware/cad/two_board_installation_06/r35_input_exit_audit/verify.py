"""A contained reachable disk rejects the fixed AUTO exit contract, not housing."""
import hashlib,json,math
from pathlib import Path
H=Path(__file__).resolve().parent;R=H.parents[3]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
c=json.loads((H/'bound.json').read_text())
for name,digest in c['source_sha256'].items():assert sha(R/name)==digest
contract=json.loads((H.parent/'r13_formed_ground/exit-contract.json').read_text())
assert c['minimum_curvature_radius_mm']==contract['selected_centerline_radius_mm']==12
assert c['source_z_mm']==27.04 and c['initial_tangent']==[0,0,1]
assert c['native_disk_guard_mm']==.01
h=c['test_slice_top_z_mm']-c['source_z_mm'];r=c['minimum_curvature_radius_mm']
assert 0<h<r and abs(c['reachable_disk_radius_mm']-(r-math.sqrt(r*r-h*h)))<1e-12
for row in c['rows']:
 assert row['target_mm'][2]<c['test_plane_z_mm']
 dz=row['target_mm'][2]-row['source_mm'][2]
 assert row['source_to_target_horizontal_mm']>r-math.sqrt(r*r-dz*dz)
rows=[]
for folder in sorted((H/'native').iterdir()):
 if not folder.is_dir():continue
 part,revision=folder.name.rsplit('-',1);v=json.loads((folder/'result.json').read_text());assert not v['runtime_failure']
 for name,digest in v['source_sha256'].items():
  p=R/name
  if p==H/'probe.scad' and revision in ('r1','r2'):p=H/('prior-union' if revision=='r1' else 'prior-owner')/'probe.scad'
  assert sha(p)==digest,(folder.name,name)
 if part.endswith('positive') or part.endswith('collision'):
  assert v['mesh']['closed_oriented_boundary'] and v['mesh']['volume_mm3']>0
 else:assert v['empty'] and v['mesh'] is None
 rows.append({'job':folder.name,'empty':v['empty'],'mesh':v['mesh'],'artifact_sha256':{str(p.relative_to(R)):sha(p) for p in sorted(folder.iterdir()) if p.is_file()}})
assert {'auto_positive-r3','auto_owner_remaining-r3'}<={x['job'] for x in rows}
out={'status':'AUTO_VERTICAL_R12_RECEIVING_EXIT_BLOCKED_BY_SCENE0_PLASTIC_HOLDER','owning_module':'switch_holder(b), b[0]==scene_0, exact button_pose(b)','not_a_global_impossibility':'Changing the holder or qualified receiving interface may resolve this; no design is changed here.','tap_general_exit_proven_blocked':False,'tap_positive_y_trial_collides':True,'completed_panel_edges':0,'cases':rows,'source_sha256':{str(p.relative_to(R)):sha(p) for p in [Path(__file__),H/'bound.json',H/'probe.scad',H/'scene0_holder.scad']}}
(H/'verification.json').write_text(json.dumps(out,indent=2)+'\n');print(out['status'])
