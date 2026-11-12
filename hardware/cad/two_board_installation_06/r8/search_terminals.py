import json,sys,math
from pathlib import Path
import numpy as np
from scipy.optimize import differential_evolution
from scipy.spatial import cKDTree
R=Path(__file__).resolve().parent;sys.path.insert(0,str(R.parent/'r7'));from optimize_fans_swapped import bern
D=json.loads((R.parent/'r7/route-pair-search.json').read_text());samples=np.linspace(0,1,6);inv=np.linalg.inv(bern(5,samples));t=np.linspace(0,1,501);B=bern(5,t);V=bern(4,t);A=bern(3,t);f=6*samples**5-15*samples**4+10*samples**3
out={}
for ref,base in D['control_points'].items():
 base=np.array(base)
 def check(x,report=False):
  start,angle,bulge=x;tan=(bern(4,np.array([start]))@(5*np.diff(base,axis=0)))[0];tan/=np.linalg.norm(tan);u=np.array([1.,0,0])-tan*tan[0];u/=np.linalg.norm(u);w=np.cross(tan,u);uu=u*math.cos(angle)+w*math.sin(angle);ww=-u*math.sin(angle)+w*math.cos(angle)
  curves=[];rad=1000;cps=[]
  for dx,px,pw in [(-2.5,-1.3,-1.3/math.sqrt(3)),(0,0,2.6/math.sqrt(3)),(2.5,1.3,-1.3/math.sqrt(3))]:
   pack=px*uu+pw*ww;xyz=bern(5,start+(1-start)*samples)@base+(1-f[:,None])*pack+f[:,None]*np.array([dx,0,0]);xyz+= (16*samples**2*(1-samples)**2)[:,None]*ww*bulge*(dx==0);cp=inv@xyz;pts=B@cp;v=V@(5*np.diff(cp,axis=0));a=A@(20*np.diff(cp,n=2,axis=0));rad=min(rad,np.min(np.linalg.norm(v,axis=1)**3/np.maximum(np.linalg.norm(np.cross(v,a),axis=1),1e-12)));curves.append(pts);cps.append(cp)
  sep=min(cKDTree(curves[j]).query(curves[i])[0].min()-1.9 for i in range(3) for j in range(i))
  return (float(rad),float(sep),cps) if report else max(0,9.6-rad)*20+max(0,.07-sep)*100-start*.01
 res=differential_evolution(check,[(.55,.8),(-math.pi/2,math.pi/2),(-3,3)],seed=12,popsize=10,maxiter=80,polish=False);rad,sep,cps=check(res.x,True);out[ref]=dict(start=float(res.x[0]),angle=float(res.x[1]),bulge=float(res.x[2]),sampled_radius=rad,sampled_clearance=sep);print(ref,out[ref],flush=True)
(R/'terminal-search.json').write_text(json.dumps(out,indent=2)+'\n')
