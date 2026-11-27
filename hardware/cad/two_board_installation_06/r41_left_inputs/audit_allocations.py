"""Analytic chord-to-box lower clearance bound for the captured component allocation boxes."""
import hashlib,json,math,re
from pathlib import Path
import numpy as np
H=Path(__file__).resolve().parent;R=H.parents[3];allocation=H.parent/'r12_ground/routes.scad'
def distance(a,b,lo,hi):
 v=b-a;cuts=[0.,1.]
 for k in range(3):
  if abs(v[k])>1e-12:cuts += [float(np.clip((face-a[k])/v[k],0,1)) for face in [lo[k],hi[k]]]
 cuts=sorted(set(cuts));values=cuts.copy()
 for left,right in zip(cuts,cuts[1:]):
  mid=a+(left+right)/2*v;mask=(mid<lo)|(mid>hi)
  if not mask.any():return 0.
  face=np.where(mid<lo,lo,hi);u=(a-face)[mask];w=v[mask]
  if w@w>1e-20:values.append(float(np.clip(-(u@w)/(w@w),left,right)))
 return min(float(np.linalg.norm(np.maximum(0,np.maximum(lo-a-t*v,a+t*v-hi)))) for t in values)
edges=json.loads((H/'routes.json').read_text())['edges'];rows=[]
for m in re.finditer(r'translate\((\[[^]]+\])\)cube\((\[[^]]+\])\); // (\S+)',allocation.read_text()):
 lo=np.array(json.loads(m[1]));hi=lo+np.array(json.loads(m[2]));best=999;who=None
 for edge in edges:
  points=np.array(edge['points_mm'])
  for a,b in zip(points,points[1:]):
   if np.linalg.norm(np.maximum(0,np.maximum(np.minimum(a,b),lo)-np.minimum(np.maximum(a,b),hi)))>=best:continue
   d=distance(a,b,lo,hi)
   if d<best:best=d;who=edge['id']
 gap=best-.6-12*(1-math.cos(math.radians(1.5)))
 assert gap>=.25,(m[3],gap)
 rows.append({'reference':m[3],'minimum_wire':who,'box_min_mm':lo.tolist(),'box_max_mm':hi.tolist(),'minimum_surface_gap_lower_bound_mm':gap})
assert {'A_C513','E_J1','high_pot'} <= {r['reference'] for r in rows}
report={'captured_allocation_boxes':rows,'source_sha256':{str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),allocation,H/'routes.json']}}
(H/'allocation-clearance.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'boxes':len(rows),'minimum_gap_mm':min(r['minimum_surface_gap_lower_bound_mm'] for r in rows)}))
