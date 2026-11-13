"""Analytic chord-to-box lower clearance bound for the four rejected capacitor owners."""
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
 if m[3] not in ['A_C501','A_C502','A_C513','A_C514']:continue
 lo=np.array(json.loads(m[1]));hi=lo+np.array(json.loads(m[2]));best=999;who=None
 for edge in edges:
  points=np.array(edge['points_mm'])
  for a,b in zip(points,points[1:]):
   d=distance(a,b,lo,hi)
   if d<best:best=d;who=edge['id']
 gap=best-.6-12*(1-math.cos(math.radians(1.5)))
 assert gap>=.25,(m[3],gap)
 rows.append({'reference':m[3],'minimum_wire':who,'box_min_mm':lo.tolist(),'box_max_mm':hi.tolist(),'minimum_surface_gap_lower_bound_mm':gap})
assert {r['reference'] for r in rows}=={'A_C501','A_C502','A_C513','A_C514'}
report={'capacitors':rows,'source_sha256':{str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),allocation,H/'routes.json']}}
(H/'capacitor-clearance.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(rows))
