"""Three separated quintic wire transitions from packed bundle to actual XH pins."""
import sys,json,math,hashlib
from pathlib import Path
import numpy as np
from scipy.spatial import cKDTree
R=Path(__file__).resolve().parent;sys.path.insert(0,str(R.parent/'r7'))
from optimize_fans_swapped import bern,obs
D=json.loads((R.parent/'r7/route-pair-search.json').read_text());start=.7;N=20000;t=np.linspace(0,1,N+1);allcurves=[];rows=[]
for ref,base in D['control_points'].items():
 parameters=json.loads((R/'terminal-search.json').read_text())[ref];start=parameters['start'];angle=parameters['angle'];bulge=parameters['bulge'];base=np.array(base);tan=(bern(4,np.array([start]))@(5*np.diff(base,axis=0)))[0];tan/=np.linalg.norm(tan);u=np.array([1.,0,0])-tan*tan[0];u/=np.linalg.norm(u);w=np.cross(tan,u);u,w=u*math.cos(angle)+w*math.sin(angle),-u*math.sin(angle)+w*math.cos(angle)
 for pin,(dx,px,pw) in enumerate([(-2.5,-1.3,-1.3/math.sqrt(3)),(0,0,2.6/math.sqrt(3)),(2.5,1.3,-1.3/math.sqrt(3))],1):
  samples=np.linspace(0,1,6);f=6*samples**5-15*samples**4+10*samples**3;pack=px*u+pw*w
  xyz=bern(5,start+(1-start)*samples)@base+(1-f[:,None])*pack+f[:,None]*np.array([dx,0,0]);xyz+=(16*samples**2*(1-samples)**2)[:,None]*w*bulge*(dx==0);cp=np.linalg.solve(bern(5,samples),xyz)
  pts=bern(5,t)@cp;vcp=5*np.diff(cp,axis=0);acp=4*np.diff(vcp,axis=0);jcp=3*np.diff(acp,axis=0);v=bern(4,t)@vcp;a=bern(3,t)@acp
  vmax=np.linalg.norm(vcp,axis=1).max();amax=np.linalg.norm(acp,axis=1).max();jmax=np.linalg.norm(jcp,axis=1).max();dt=1/(2*N)
  k=np.max((np.linalg.norm(np.cross(v,a),axis=1)+vmax*jmax*dt)/(np.linalg.norm(v,axis=1)-amax*dt)**3)
  cl=min(np.linalg.norm(np.maximum(np.maximum(b[:3]-pts,pts-b[3:]),0),axis=1).min() for name,b in obs if name!=ref)-.95-vmax*dt
  row=dict(ref=ref,pin=pin,control_points=cp.tolist(),curvature_radius_lower_bound_mm=float(1/k),obstacle_clearance_lower_bound_mm=float(cl),length_mm=float(np.linalg.norm(np.diff(pts,axis=0),axis=1).sum()+3),motion_bound_mm=float(vmax*dt));rows.append(row)
  allcurves.append(np.concatenate([pts,np.array([pts[-1]-[0,0,z] for z in np.linspace(0,3,1001)])]))
mutual=[]
for i in range(6):
 for j in range(i):mutual.append(float(cKDTree(allcurves[j]).query(allcurves[i])[0].min()-1.9-rows[i]['motion_bound_mm']-rows[j]['motion_bound_mm']-.003))
print('pairwise',[(i,j,mutual[i*(i-1)//2+j]) for i in range(6) for j in range(i)])
out=dict(rows=rows,minimum_pairwise_wire_clearance_lower_bound_mm=min(mutual),accepted=min(mutual)>.05 and all(r['curvature_radius_lower_bound_mm']>=9.5 and r['obstacle_clearance_lower_bound_mm']>.2 for r in rows),scope='Exact polynomial fanout and straight final 3 mm insertion. Packed entry wire OD<=1.9 mm. Native/support checks pending.')
out['source_sha256']={str(q.relative_to(R.parents[3])):hashlib.sha256(q.read_bytes()).hexdigest() for q in [Path(__file__),R/'terminal-search.json',R.parent/'r7/route-pair-search.json',R.parents[3]/'hardware/cad/two_board_print_01/capture.json']}
(R/'terminal-routes.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({**{r['ref']+'_'+str(r['pin']):[r['curvature_radius_lower_bound_mm'],r['obstacle_clearance_lower_bound_mm']] for r in rows},'mutual':min(mutual),'accepted':out['accepted']},indent=2))
