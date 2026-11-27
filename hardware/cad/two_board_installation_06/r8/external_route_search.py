"""Search within exact retained lead-bay boxes; failure is not an impossibility proof."""
import sys,json
from pathlib import Path
import numpy as np
from scipy.optimize import differential_evolution
R=Path(__file__).resolve().parent;sys.path.insert(0,str(R.parent/'r7'));from optimize_fans_swapped import bern
T=np.linspace(0,1,201);B=bern(5,T);V=bern(4,T);A=bern(3,T)
boxes=np.array([[-13,20.75,10,-2,33.5,42.5],[-15.1,20.2,28,-2.8,23.2,40],[-15.1,23,14,-12.9,33.5,38]])
ob=np.array([[-10,25,18,-1.9,35.5,22],[-13,30,7.5,-6,35.5,12.5],[-13,30,39.5,-6,35.5,44.5]])
start=np.array([-9.,22.,34.]);end=np.array([-4.,30.25,15.])
def evaluate(x,report=False):
 p=np.array([start,start+[0,x[0],0],x[1:4],x[4:7],end-[x[7],0,0],end]);pts=B@p;v=V@(5*np.diff(p,axis=0));a=A@(20*np.diff(p,n=2,axis=0));rad=np.min(np.linalg.norm(v,axis=1)**3/np.maximum(np.linalg.norm(np.cross(v,a),axis=1),1e-12))
 inside=np.minimum(pts[:,None,:]-boxes[None,:,:3],boxes[None,:,3:]-pts[:,None,:]).min(axis=2).max(axis=1).min()-1
 dist=np.linalg.norm(np.maximum(np.maximum(ob[None,:,:3]-pts[:,None,:],pts[:,None,:]-ob[None,:,3:]),0),axis=2).min()-1;cl=min(inside,dist)
 score=100*max(0,.1-cl)+10*max(0,9.7-rad)
 return (float(cl),float(rad),p.tolist()) if report else score
res=differential_evolution(evaluate,[(1,20),(-25,5),(15,45),(0,55),(-25,5),(15,45),(0,55),(1,20)],popsize=15,maxiter=500,seed=44,polish=False);cl,rad,p=evaluate(res.x,True);out=dict(clearance=cl,radius=rad,control_points=p,accepted=cl>=.05 and rad>=9.5,scope='Single lead only, route entry is a project datum not a claimed factory emergence dimension; mutual leads, full CAD and receiving transition not yet checked.')
(R/'external-route-search.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out),flush=True)
