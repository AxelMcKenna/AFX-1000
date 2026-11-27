"""Local two-route search: does not imply installed harness release."""
import json
from pathlib import Path
import numpy as np
from scipy.optimize import minimize
from scipy.spatial.distance import cdist
from optimize_fans_swapped import properties,obs
R=Path(__file__).resolve().parent
refs=['F_J202','F_J203'];base=[np.array(json.loads((R/(r+'-route-swapped.json')).read_text())['control_points']) for r in refs]
arrs=[np.array([b for r,b in obs if r!=ref]) for ref in refs]
def unpack(x):
 out=[]
 for i,p in enumerate(base):
  p=p.copy();v=x[i*8:(i+1)*8];p[1,0]=v[0];p[2:4]=v[1:7].reshape(2,3);p[4,2]=v[7];out.append(p)
 return out
x=np.concatenate([[p[1,0],*p[2],*p[3],p[4,2]] for p in base])
def assess(x):
 curves=[];limits=[];length=0
 for p,arr in zip(unpack(x),arrs):
  pts,rad,l=properties(p,301);curves.append(pts);length+=l
  dist=np.maximum(np.maximum(arr[None,:,:3]-pts[:,None,:],pts[:,None,:]-arr[None,:,3:]),0)
  limits += [np.sqrt(np.sum(dist*dist,axis=2)).min()-2.85,rad-10.2,pts[:,2].min()-12.5,39.3-pts[:,2].max(),pts[:,0].min()-3,186-pts[:,1].max()]
 limits += [cdist(*curves).min()-5.5]
 return np.array(limits),length
res=minimize(lambda x:assess(x)[1],x,method='SLSQP',constraints=[dict(type='ineq',fun=lambda x:assess(x)[0])],options=dict(maxiter=300,ftol=1e-6))
limits,length=assess(res.x)
out=dict(success=bool(res.success and limits.min()>-1e-5),message=res.message,limits=limits.tolist(),length=length,control_points={r:p.tolist() for r,p in zip(refs,unpack(res.x))})
(R/'route-pair-search.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out),flush=True)
