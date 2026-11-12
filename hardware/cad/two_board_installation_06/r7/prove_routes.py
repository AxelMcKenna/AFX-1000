"""Conservative continuous bounds for candidate quintic bundle centerlines.
Uses derivative convex hull bounds, not only sampled route acceptance.
"""
import hashlib,json
from pathlib import Path
import numpy as np
from scipy.spatial import cKDTree
from optimize_fans_swapped import bern,obs,CAP
R=Path(__file__).resolve().parent
N=20000;dt=1/(2*N);t=np.linspace(0,1,N+1)
def proof(p,ref):
 v=5*np.diff(p,axis=0);a=4*np.diff(v,axis=0);j=3*np.diff(a,axis=0)
 vmax=np.linalg.norm(v,axis=1).max();amax=np.linalg.norm(a,axis=1).max();jmax=np.linalg.norm(j,axis=1).max()
 pts=bern(5,t)@p;vel=bern(4,t)@v;acc=bern(3,t)@a
 speed=np.linalg.norm(vel,axis=1);cross=np.linalg.norm(np.cross(vel,acc),axis=1)
 kbound=np.max((cross+vmax*jmax*dt)/np.maximum(speed-amax*dt,1e-20)**3)
 minimum=1e9;near=''
 for name,b in obs:
  if name==ref:continue # Intentional connector insertion separately modeled and checked.
  distance=np.linalg.norm(np.maximum(np.maximum(b[:3]-pts,pts-b[3:]),0),axis=1).min()
  if distance<minimum:minimum=distance;near=name
 out=dict(length_sampled_mm=float(np.linalg.norm(np.diff(pts,axis=0),axis=1).sum()),clearance_lower_bound_mm=float(minimum-2.5-vmax*dt),nearest_obstacle=near,curvature_radius_lower_bound_mm=float(1/kbound),centerline_min=pts.min(axis=0).tolist(),centerline_max=pts.max(axis=0).tolist(),sample_motion_bound_mm=float(vmax*dt),polyline_deviation_bound_mm=float(amax/(8*N*N)))
 return out,pts
source=R/'route-pair-search.json';data=json.loads(source.read_text());result={};curves=[]
for ref,p in data['control_points'].items():
 result[ref],pts=proof(np.array(p),ref);curves.append(pts)
mutual=float(cKDTree(curves[0]).query(curves[1])[0].min()-5-sum(r['sample_motion_bound_mm'] for r in result.values()))
out=dict(routes=result,mutual_bundle_clearance_lower_bound_mm=mutual,accepted_continuous_screen=all(r['clearance_lower_bound_mm']>=.2 and r['curvature_radius_lower_bound_mm']>=9.5 for r in result.values()) and mutual>=.2,scope='Captured component boxes and mutual bundle curves. Does not yet include final carriers, shell, terminal fanout, supports or physical wire specification.',source_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [source,Path(__file__),R/'optimize_fans_swapped.py',CAP]})
(R/'route-continuous-proof.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
