"""Nominal fan-lead route search, with source-bound obstacle and curvature evidence."""
import hashlib,json,math
from pathlib import Path
import numpy as np
from numpy.polynomial import Polynomial as P
R=Path(__file__).resolve().parent;REPO=R.parents[3]
cap_path=REPO/'hardware/cad/two_board_print_01/capture.json';cap=json.loads(cap_path.read_text())
obs=[(r,np.array([xy[0],xy[1],z[0],xy[2],xy[3],z[1]])) for r,xy,z in cap['component_envelopes']+cap['tail_envelopes']]
obs += [(r['id'],np.array([r['xy'][0],r['xy'][1],r['z'][0],r['xy'][2],r['xy'][3],r['z'][1]])) for r in cap['context']]
for x,y in cap['lid_fasteners']:obs.append(('lid_post',np.array([x-3.5,y-3.5,0,x+3.5,y+3.5,43.6])))
for m in cap['mounts']:obs.append((m[0]+'_post',np.array([m[1]-3.2,m[2]-3.2,2.8,m[1]+3.2,m[2]+3.2,m[3]+4.1])))
def bez(p,n=160):
 t=np.linspace(0,1,n)[:,None];return (1-t)**3*p[0]+3*(1-t)**2*t*p[1]+3*(1-t)*t*t*p[2]+t**3*p[3]
def check(points,omit,radius=2.5):
 arr=np.array([b for name,b in obs if name!=omit]);lo=points.min(0)-radius-1;hi=points.max(0)+radius+1;arr=arr[np.all((arr[:,:3]<hi)&(arr[:,3:]>lo),axis=1)]
 dist=np.maximum(np.maximum(arr[None,:,:3]-points[:,None,:],points[:,None,:]-arr[None,:,3:]),0)
 d=np.sqrt(np.sum(dist*dist,axis=2));step=np.max(np.linalg.norm(np.diff(points,axis=0),axis=1));return float(d.min()-radius-step/2)
def radius_min(p):
 q=[P([p[0,i],3*(p[1,i]-p[0,i]),3*(p[2,i]-2*p[1,i]+p[0,i]),p[3,i]-3*p[2,i]+3*p[1,i]-p[0,i]]) for i in range(3)]
 v=[x.deriv() for x in q];a=[x.deriv() for x in v];cross=[v[1]*a[2]-v[2]*a[1],v[2]*a[0]-v[0]*a[2],v[0]*a[1]-v[1]*a[0]];num=sum(x*x for x in cross);speed2=sum(x*x for x in v);den=speed2**3;crit=num.deriv()*den-num*den.deriv();ts=[0,1]+[float(t.real) for t in crit.roots() if abs(t.imag)<1e-6 and 0<t.real<1];k=max(float(num(t)/den(t)) for t in ts);return 1/math.sqrt(k) if k else 1e99
routes=[]
for ref,y,end in [('F_J202',75.25,[21.5,149,22.3]),('F_J203',175.25,[23.5,175,22.3])]:
 best=None;valid=[]
 for a in range(12,102,3):
  for b in range(12,42,3):
   p=np.array([[3,y,15],[3+a,y,15],[end[0],end[1],end[2]+b],end],float);pts=bez(p);clear=check(pts,ref);rad=radius_min(p);score=min(clear,.2)+min(rad-9.5,0)
   row=dict(ref=ref,control_points=p.tolist(),clearance_lower_screen_mm=clear,minimum_nominal_curvature_radius_mm=rad,length_mm=float(np.linalg.norm(np.diff(pts,axis=0),axis=1).sum()))
   if best is None or score>best[0]:best=(score,row)
   if clear>=.2 and rad>=9.5:valid.append(row)
 chosen=min(valid,key=lambda x:x['length_mm']) if valid else best[1];chosen['nominal_route_found']=bool(valid);chosen['passing_grid_count']=len(valid);routes.append(chosen);print(json.dumps(chosen))
out=dict(scope='Nominal centerline routing screen; formed-wire retention and individual terminal fanout pending',routes=routes,wire_bundle_radius_mm=2.5,clearance_allowance_mm=.2,project_minimum_bend_radius_mm=9.5,curvature_method='Stationary polynomial roots of squared cubic Bezier curvature, endpoints included; numerical roots, not interval proof',clearance_method='Point-to-AABB distance minus bundle radius and half maximum sample spacing; additional Bezier deviation not yet bounded',source_sha256={str(p.relative_to(REPO)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [cap_path,Path(__file__)]},harness_released=False)
(R/'fan-route-screen.json').write_text(json.dumps(out,indent=2)+'\n')
