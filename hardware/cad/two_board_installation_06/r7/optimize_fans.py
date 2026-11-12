"""Find smooth fan lead routes; retain failures and expose all design assumptions."""
import argparse,hashlib,json,math
from pathlib import Path
import numpy as np
from scipy.optimize import differential_evolution
R=Path(__file__).resolve().parent;REPO=R.parents[3]
CAP=REPO/'hardware/cad/two_board_print_01/capture.json';d=json.loads(CAP.read_text())
obs=[(r,np.array([xy[0],xy[1],z[0],xy[2],xy[3],z[1]])) for r,xy,z in d['component_envelopes']+d['tail_envelopes']]
obs += [(r['id'],np.array([r['xy'][0],r['xy'][1],r['z'][0],r['xy'][2],r['xy'][3],r['z'][1]])) for r in d['context']]
for x,y in d['lid_fasteners']:obs.append(('lid_post',np.array([x-3.5,y-3.5,0,x+3.5,y+3.5,43.6])))
for m in d['mounts']:obs.append((m[0]+'_post',np.array([m[1]-3.2,m[2]-3.2,2.8,m[1]+3.2,m[2]+3.2,m[3]+4.1])))
def bern(n,t):return np.array([math.comb(n,i)*t**i*(1-t)**(n-i) for i in range(n+1)]).T
t=np.linspace(0,1,121);B=bern(5,t);V=bern(4,t);A=bern(3,t)
def properties(p,n=121):
 b,v,a=(B,V,A) if n==121 else tuple(bern(k,np.linspace(0,1,n)) for k in [5,4,3]);pts=b@p;vel=v@(5*np.diff(p,axis=0));acc=a@(20*np.diff(p,n=2,axis=0));speed=np.linalg.norm(vel,axis=1);cross=np.linalg.norm(np.cross(vel,acc),axis=1);radius=np.min(speed**3/np.maximum(cross,1e-12));return pts,float(radius),float(np.linalg.norm(np.diff(pts,axis=0),axis=1).sum())
def controls(v,start,end):
 a,x2,y2,z2,x3,y3,z3,b=v
 return np.array([start,start+[a,0,0],[x2,y2,z2],[x3,y3,z3],end+[0,0,b],end])
def main():
 ap=argparse.ArgumentParser();ap.add_argument('ref',choices=['F_J202','F_J203']);args=ap.parse_args();ref=args.ref
 start=np.array([3,75.25 if ref=='F_J202' else 175.25,15.]);end=np.array([21.5,149,22.3] if ref=='F_J202' else [23.5,175,22.3]);own=next(b for r,b in obs if r==ref)
 arr=np.array([b for r,b in obs if r!=ref]);arr=arr[(arr[:,0]<110)&(arr[:,3]>0)&(arr[:,1]<190)&(arr[:,4]>50)&(arr[:,2]<42)&(arr[:,5]>10)]
 def clearance(pts):
  dist=np.maximum(np.maximum(arr[None,:,:3]-pts[:,None,:],pts[:,None,:]-arr[None,:,3:]),0);md=np.sqrt(np.sum(dist*dist,axis=2)).min()
  selfdist=np.maximum(np.maximum(own[:3]-pts[:105],pts[:105]-own[3:]),0);md=min(md,np.linalg.norm(selfdist,axis=1).min());return float(md-2.5)
 def score(v,report=False):
  p=controls(v,start,end);pts,rad,length=properties(p);clear=clearance(pts)
  wall=max(0,pts[:,2].max()-39.5,12.2-pts[:,2].min(),pts[:,1].max()-186,5-pts[:,1].min(),3-pts[:,0].min())
  cost=100*max(0,.45-clear)+20*max(0,10.5-rad)+100*wall+length/500
  return (cost,clear,rad,length,p) if report else cost
 ymin=55 if ref=='F_J202' else 130
 bounds=[(6,40),(8,100),(ymin,184),(15,38),(8,100),(ymin,184),(24,39),(12,36)]
 step=[0]
 def callback(x,convergence):
  step[0]+=1
  if step[0]%20==0:
   c,cl,rad,l,p=score(x,True);print(json.dumps(dict(ref=ref,iteration=step[0],cost=c,clearance=cl,radius=rad,length=l)),flush=True)
 result=differential_evolution(score,bounds,seed=82 if ref=='F_J202' else 83,popsize=10,maxiter=240,tol=.0001,polish=False,callback=callback,workers=1)
 c,cl,rad,l,p=score(result.x,True);pts,radfine,lfine=properties(p,2001);clearfine=clearance(pts)
 out=dict(ref=ref,control_points=p.tolist(),cost=c,sampled_clearance_mm=clearfine,minimum_sampled_curvature_radius_mm=radfine,length_mm=lfine,nominal_route_found=bool(clearfine>.3 and radfine>=10),method='Quintic Bezier numerical search; continuous clearance/radius proof and individual-wire fanout still pending',source_sha256={str(q.relative_to(REPO)):hashlib.sha256(q.read_bytes()).hexdigest() for q in [CAP,Path(__file__)]})
 (R/(ref+'-route-optimized.json')).write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out),flush=True)
if __name__=='__main__':main()
