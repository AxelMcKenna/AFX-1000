from pathlib import Path
import json,math,hashlib,importlib.util,xml.etree.ElementTree as ET
import numpy as np
HERE=Path(__file__).resolve().parent;REPO=HERE.parents[3];BASE=HERE.parent
helper=BASE/'r12_ground/verify.py';spec=importlib.util.spec_from_file_location('distance',helper);distance=importlib.util.module_from_spec(spec);spec.loader.exec_module(distance)
g=json.loads((HERE/'route.json').read_text());e=g['edges'][0]
contract=json.loads((BASE/'r11_distribution/reference/panel-contract.json').read_text());signal=next(r['signal'] for r in contract['front_inputs'] if r['id']=='scene_2')
assert e['source']=='D_J2002:2' and e['target']=='button_scene_2:1' and e['net']==signal['net']
assert e['points_mm'][0]==signal['xy']+[27.04]
assert np.linalg.norm(np.array(e['points_mm'][-1])-json.loads((BASE/'r12_ground/ground-routes.json').read_text())['endpoints_mm']['button_scene_2:1'])<1e-7
leftpath=BASE/'r14_left_ground/left-routes.json';rightpath=BASE/'r15_right_ground/right-routes.json';left=json.loads(leftpath.read_text())['edges']+json.loads(rightpath.read_text())['edges']
minimum=999;collisions=[];minimum_sample_radius=999;curvature=[]
for i,a in enumerate(g['edges']):
 points=np.array(a['points_mm']);cursor=0;arcs=[]
 for primitive in a['primitives']:
  if primitive['kind']=='line':cursor+=1
  elif primitive['kind']=='arc':
   end=cursor+math.ceil(primitive['angle_degrees']/3);arcs.append((cursor,end,primitive['radius_mm']));cursor=end
   assert primitive['radius_mm']>=12
  elif primitive['kind']=='smooth_height_overlay':
   first,last=primitive['first_point'],primitive['last_point']
   included=[r for start,end,r in arcs if first<=start and end<=last]
   assert included
   R=min(included);L=primitive['planar_sample_length_mm'];dz=abs(primitive['delta_mm'])
   z1=1.875*dz/L;z2=(10/math.sqrt(3))*dz/(L*L)
   bound=1/math.sqrt((1+z1*z1)/(R*R)+z2*z2)
   assert bound>=12
   curvature.append({'wire':a['id'],'height_overlay_radius_lower_bound_mm':bound})
  else:raise AssertionError('Unknown curve type')
 assert cursor==len(points)-1
 for aa,bb,cc in zip(points,points[1:],points[2:]):
  u,v=bb-aa,cc-bb;cross=float(np.linalg.norm(np.cross(u,v)))
  if cross>1e-10:minimum_sample_radius=min(minimum_sample_radius,float(np.linalg.norm(u)*np.linalg.norm(v)*np.linalg.norm(cc-aa)/(2*cross)))
 for b in left:
  gap=min(distance.distance(aa,ab,ba,bb)for aa,ab in zip(a['points_mm'],a['points_mm'][1:])for ba,bb in zip(b['points_mm'],b['points_mm'][1:]))
  minimum=min(minimum,gap)
  if gap<1.2-1e-8:collisions.append({'wires':[a['id'],b['id']],'distance_mm':gap})
self_collisions=[]
for edge in g['edges']:
 p=np.array(edge['points_mm']);lengths=np.linalg.norm(p[1:]-p[:-1],axis=1);stations=np.concatenate(([0],np.cumsum(lengths)))
 for i,(a,b) in enumerate(zip(p,p[1:])):
  for j in range(i+2,len(p)-1):
   if stations[j]-stations[i+1]<=3:continue
   c,d=p[j],p[j+1]
   separation=np.maximum(np.minimum(a,b),np.minimum(c,d))-np.minimum(np.maximum(a,b),np.maximum(c,d))
   if np.any(separation>1.2):continue
   gap=distance.distance(a,b,c,d)
   if gap<1.2-1e-8:self_collisions.append([edge['id'],i,j,gap])
assert not self_collisions,self_collisions
assert minimum_sample_radius>=12-1e-7
assert not collisions,collisions

sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert all(sha(REPO/p)==h for p,h in g['source_sha256'].items())
out=dict(source_sha256={str(p.relative_to(REPO)):sha(p) for p in [Path(__file__),helper,HERE/'route.json',HERE/'route.scad',leftpath,rightpath]},wire='S01',minimum_sampled_radius_mm=minimum_sample_radius,height_overlay_bounds=curvature,minimum_ground_surface_gap_mm=minimum-1.2,self_collisions=self_collisions,ground_collisions=collisions,receiving_curve_geometry_pass=True,fabrication_released=False)
(HERE/'verification.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))
