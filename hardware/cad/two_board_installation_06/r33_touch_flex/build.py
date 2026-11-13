"""One-mm receiving-motion construction; no manufacturer release claim."""
import hashlib,json,math,shutil
from pathlib import Path
import numpy as np
from scipy.optimize import brentq
from hardware.cad.two_board_installation_06.r15_right_ground.curves import Wire
H=Path(__file__).resolve().parent
R=H.parents[3]
original=json.loads((H.parent/'r29_touch_inline/route-draft.json').read_text())
TRAVEL=1.;BEND=13.;k=2-math.pi/2
angle=brentq(lambda a:4*BEND*(a-math.sin(a))-TRAVEL,0,1)
span=4*BEND*math.sin(angle);height=2*BEND*(1-math.cos(angle))

def replay(w,p):
 if p['kind']=='line':w.line(p['end'])
 else:w.arc(p['tangent'],p['normal'],p['radius_mm'],p['angle_degrees'])

def make(row,t):
 source=Wire(row['segments'][0]['points_mm'][0]);p=row['segments'][0]['primitives']
 for primitive in p[:-3]:replay(source,primitive)
 radius=BEND+t/k;x=p[-1]['end'][0];y=source.p[1]
 source.line([x+radius,y,27]);source.arc([-1,0,0],[0,1,0],radius,90);source.line([x,113.5+t,27])
 out=row['segments'][1];a=np.array(out['points_mm'][0]);a[1]+=t;tail=Wire(a)
 bump=None
 for primitive in out['primitives']:
  if primitive['kind']=='line' and abs(primitive['end'][0]-137)<1e-8 and primitive['start'][0]>137:
   bump=[primitive['start'],primitive['end']]
   if t>0:
    theta=brentq(lambda aa:4*BEND*(aa-math.sin(aa))-t,0,1);degrees=math.degrees(theta)
    T=np.array([-1.,0,0]);N=np.array([0.,0,1.])
    t2,n2=tail.arc(T,N,BEND,degrees);tail.arc(t2,-n2,BEND,degrees)
    t2,n2=tail.arc(T,-N,BEND,degrees);tail.arc(t2,-n2,BEND,degrees)
  replay(tail,primitive)
 return source,tail,bump

def length(primitives):
 return sum(math.dist(p['start'],p['end']) if p['kind']=='line' else p['radius_mm']*math.radians(p['angle_degrees']) for p in primitives)

def validate(w,old,start,end):
 assert np.linalg.norm(w.points[0]-start)<1e-8 and np.linalg.norm(w.p-end)<1e-8
 assert abs(length(w.primitives)-length(old['primitives']))<1e-8
 tangents=[]
 for p in w.primitives:
  if p['kind']=='line':
   v=np.array(p['end'])-p['start'];assert np.linalg.norm(v)>1e-8;u=v/np.linalg.norm(v);tangents.append((u,u))
  else:
   assert p['radius_mm']>=13
   T=np.array(p['tangent']);N=np.array(p['normal']);a=math.radians(p['angle_degrees']);tangents.append((T,T*math.cos(a)+N*math.sin(a)))
 for a,b in zip(tangents,tangents[1:]):assert np.linalg.norm(a[1]-b[0])<1e-7

scad=['// Entire-motion receiving supersets, not a nominal static harness.','module flex_ball(p,r){translate(p)rotate([11,7,3])sphere(r=r,$fn=32);}','module flex_hull(points,r){hull(){for(p=points)flex_ball(p,r);}}']
records=[]
for row in original['edges']:
 zero,tail0,bump=make(row,0);last,tail1,_=make(row,TRAVEL)
 for t in np.linspace(0,TRAVEL,101):
  source,tail,_=make(row,float(t))
  validate(source,row['segments'][0],row['segments'][0]['points_mm'][0],[last.p[0],113.5+t,27])
  validate(tail,row['segments'][1],[tail0.points[0][0],136.5+t,27],row['segments'][1]['points_mm'][-1])
 assert len(zero.points)==len(last.points)
 assert span<=bump[0][0]-bump[1][0]
 scad.append('module touch_flex_'+row['id']+'(r=.665){')
 for i in range(len(zero.points)-1):
  points=[zero.points[i].tolist(),zero.points[i+1].tolist(),last.points[i].tolist(),last.points[i+1].tolist()]
  scad.append('flex_hull('+json.dumps(points)+',r);')
 # Every unchanged outgoing segment is inside its original receiving tube;
 # shortening its initial straight leaves a subset. Every bump point lies in
 # the closed rectangle bounded by its original west straight and peak height.
 for a,b in zip(tail0.points,tail0.points[1:]):scad.append('flex_hull('+json.dumps([a.tolist(),b.tolist()])+',r);')
 a,b=bump;scad.append('flex_hull('+json.dumps([a,b,[a[0],a[1],a[2]+height],[b[0],b[1],b[2]+height]])+',r);')
 scad.append('}')
 records.append({'id':row['id'],'host':row['host'],'trill_pin':row['trill_pin'],'bump_base_mm':bump,'source_final_radius_mm':BEND+TRAVEL/k,'halves':[{'points_mm':[p.tolist() for p in w.points],'primitives':w.primitives} for w in [last,tail1]]})
scad.append('module touch_flex_wires(r=.665){'+''.join('touch_flex_'+r['id']+'(r);' for r in records)+'}')
(H/'flex.scad').write_text('\n'.join(scad)+'\n')
max_sag=(BEND+TRAVEL/k)*(1-math.cos(math.radians(1.5)))
assert .665*math.cos(math.pi/32)**2-max_sag>.65
assert .795*math.cos(math.pi/32)**2-max_sag>.775
report={'status':'UNVERIFIED_RECEIVING_MOTION','available_translation_mm':[0,TRAVEL,0],'actual_connector_release_stroke_mm':None,'maximum_bump_angle_degrees':math.degrees(angle),'maximum_bump_span_mm':span,'maximum_bump_height_mm':height,'minimum_bend_radius_mm':13,'length_and_tangent_checks_per_wire':101,'wire_radius_mm':.65,'sweep_sphere_radius_mm':.665,'clearance_sphere_radius_mm':.795,'chord_sag_bound_mm':max_sag,'continuous_sweep_basis':'Source matched arc stations are affine in radius, so endpoint-pose convex hulls cover all intermediate positions plus chord error. Outgoing initial straight shrinks; other parts stay fixed except the R13 four-arc bump, entirely contained in its base-to-peak rectangle. Independent-pose swept supersets are stronger than synchronized pose checks.','completed_touch_wires':0,'edges':records,'source_sha256':{str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),H.parent/'r29_touch_inline/route-draft.json',H.parent/'r15_right_ground/curves.py']}}
(H/'flex.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:report[k] for k in ['maximum_bump_angle_degrees','maximum_bump_span_mm','maximum_bump_height_mm','chord_sag_bound_mm']}))
