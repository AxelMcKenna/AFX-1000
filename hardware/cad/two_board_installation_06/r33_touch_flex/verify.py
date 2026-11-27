"""Verify source-bound continuous-motion diagnostics without claiming release."""
import hashlib,json,copy
from pathlib import Path
import numpy as np
from hardware.cad.two_board_installation_06.r33_touch_flex import build as b
H=Path(__file__).resolve().parent;R=H.parents[3]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
c=json.loads((H/'flex.json').read_text())
for name,digest in c['source_sha256'].items():assert sha(R/name)==digest
assert c['actual_connector_release_stroke_mm'] is None and c['completed_touch_wires']==0
# Deliberately destroy physical length and endpoint registration independently.
source,tail,_=b.make(b.original['edges'][0],1.)
mutations=[]
for kind in ['length','endpoint','bend']:
 bad=copy.deepcopy(tail)
 if kind=='length':bad.primitives[0]['end'][1]+=.2
 if kind=='endpoint':bad.points[-1][0]+=.2
 if kind=='bend':
  next(p for p in bad.primitives if p['kind']=='arc')['radius_mm']=12.9
 try:b.validate(bad,b.original['edges'][0]['segments'][1],tail.points[0],tail.p)
 except AssertionError:mutations.append(kind)
 else:raise AssertionError('Accepted invalid '+kind)
rows=[]
for case in ['positive','mutual','population','controls','sensor','ground_supports','cradle']:
 folder=H/'native'/(case+'-r1');result=json.loads((folder/'result.json').read_text())
 assert not result['runtime_failure']
 for name,digest in result['source_sha256'].items():assert sha(R/name)==digest,(case,name)
 if case=='positive':assert result['mesh']['closed_oriented_boundary'] and result['mesh']['volume_mm3']>0
 rows.append({'case':case,'empty':result['empty'],'mesh':result['mesh'],'artifact_sha256':{str(p.relative_to(R)):sha(p) for p in sorted(folder.iterdir()) if p.is_file()}})
passed=all(row['empty'] for row in rows if row['case']!='positive')
out={'status':'LOCAL_MOTION_ENVELOPES_CLEAR' if passed else 'LOCAL_MOTION_ENVELOPE_INTERFERENCE','local_motion_clearance_passed':passed,'mutation_tests_rejected':mutations,'actual_connector_release_qualified':False,'completed_touch_wires':0,'cases':rows,'source_sha256':{str(p.relative_to(R)):sha(p) for p in [Path(__file__),H/'flex.json',H/'flex.scad']}}
(H/'verification.json').write_text(json.dumps(out,indent=2)+'\n');print(out['status'])
