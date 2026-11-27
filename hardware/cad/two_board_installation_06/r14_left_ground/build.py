"""Formed19-button left ground chain with manufacturer-radius curves."""
from pathlib import Path
import json,math,hashlib
import numpy as np
HERE=Path(__file__).resolve().parent;REPO=HERE.parents[3];BASE=HERE.parent
old=json.loads((BASE/'r12_ground/ground-routes.json').read_text())
endpoints=old['endpoints_mm'];paths=[]

def unit(v):return np.array(v,dtype=float)/np.linalg.norm(v)
def smooth(t):return 10*t**3-15*t**4+6*t**5
class Wire:
 def __init__(self,start):self.points=[np.array(start,dtype=float)];self.primitives=[]
 @property
 def p(self):return self.points[-1]
 def line(self,end):
  end=np.array(end,dtype=float)
  if np.linalg.norm(end-self.p)<1e-8:return
  self.primitives.append({'kind':'line','start':self.p.tolist(),'end':end.tolist()});self.points.append(end)
 def arc(self,T,N,R,degrees):
  start=self.p.copy();T,N=unit(T),unit(N);theta=math.radians(degrees)
  assert abs(T@N)<1e-8 and R>=12
  for a in np.linspace(0,theta,math.ceil(degrees/3)+1)[1:]:self.points.append(start+R*math.sin(a)*T+R*(1-math.cos(a))*N)
  self.primitives.append({'kind':'arc','start':start.tolist(),'tangent':T.tolist(),'normal':N.tolist(),'radius_mm':R,'angle_degrees':degrees})
  return math.cos(theta)*T+math.sin(theta)*N,-math.sin(theta)*T+math.cos(theta)*N
 def s_curve(self,T,N,R,offset):
  theta=math.acos(1-offset/(2*R));T2,N2=self.arc(T,N,R,math.degrees(theta));self.arc(T2,-N2,R,math.degrees(theta))
 def change_height(self,first,last,delta):
  # Only planar curved subsequences use this smooth height transition.
  lengths=[0]
  for a,b in zip(self.points[first:last],self.points[first+1:last+1]):lengths.append(lengths[-1]+np.linalg.norm((b-a)[:2]))
  for index,L in enumerate(lengths):self.points[first+index][2]+=delta*smooth(L/lengths[-1])
  self.primitives.append({'kind':'smooth_height_overlay','first_point':first,'last_point':last,'delta_mm':delta,'planar_sample_length_mm':lengths[-1],'profile':'10t^3-15t^4+6t^5'})

def add(a,b,wire):
 assert np.linalg.norm(wire.points[0]-endpoints[a])<1e-7,(a,wire.points[0],endpoints[a])
 assert np.linalg.norm(wire.p-endpoints[b])<1e-7,(b,wire.p,endpoints[b])
 paths.append({'id':'L'+str(len(paths)+1).zfill(2),'from':a,'to':b,'wire':'Alpha5853 26AWG7/34','points_mm':[p.tolist() for p in wire.points],'primitives':wire.primitives})

# First source escape matches the separately full-assembly screened r13 source.
a='D_J2002:15';b='button_quantize:3';w=Wire(endpoints[a]);az=math.radians(250)
T,N=w.arc([0,0,1],[math.cos(az),math.sin(az),0],12,90)
w.arc(T,[T[1],-T[0],0],12,70) # heading250 ->180
w.s_curve([-1,0,0],[0,0,-1],12,39.04-30)
w.s_curve([-1,0,0],[0,-1,0],12,w.p[1]-14.8)
radius=20;offset=endpoints[b][1]-14.8;angle=math.degrees(math.acos(1-offset/radius));run=math.sqrt(2*radius*offset-offset*offset)
w.line([endpoints[b][0]+run,14.8,30]);first=len(w.points)-1;w.arc([-1,0,0],[0,1,0],radius,angle);w.change_height(first,len(w.points)-1,1.6)
add(a,b,w)
# Alternating direction keeps intermediate leads on separate physical terminals.
order=[('quantize','3','4'),('auto','3','4'),('tap','4','3'),('nudge_up','4','3'),('nudge_down','4','3'),('source_input','3','4'),('isolate_0','3','4'),('isolate_1','3','4'),('isolate_2','3','4'),('isolate_3','3','4'),('overdub','4','3'),('pad_3','4','3'),('pad_2','4','3'),('pad_1','4','3'),('pad_0','4','3'),('roll','4','3'),('bank','4','3'),('source_xpad','4','3'),('hold','3',None)]
for previous,current in zip(order,order[1:]):
 a='button_'+previous[0]+':'+previous[2];b='button_'+current[0]+':'+current[1];w=Wire(endpoints[a])
 if previous[0]=='quantize':
  offset=19.75-14.8;run=math.sqrt(4*12*offset-offset*offset)
  w.s_curve([1,0,0],[0,-1,0],12,offset);w.line([endpoints[b][0]-run,14.8,31.6]);w.s_curve([1,0,0],[0,1,0],12,offset)
 elif previous[0]=='tap':
  chord=endpoints[a][0]-endpoints[b][0];sag=12.75;R=chord*chord/(8*sag)+sag/2
  radial=np.array([chord/2,R-sag,0]);T=unit([-radial[1],radial[0],0]);N=-unit(radial)
  w.arc(T,N,R,math.degrees(2*math.asin(chord/(2*R))))
 elif previous[0]=='nudge_down':
  w.s_curve([-1,0,0],[0,1,0],14,.5);w.line([25.75,36.25,31.6]);w.arc([-1,0,0],[0,1,0],12,90);w.line(endpoints[b])
 elif previous[0]=='isolate_3':
  w.line([173,56.75,31.6]);w.arc([1,0,0],[0,1,0],12,90)
  w.line([185,95.75,31.6]);w.arc([0,1,0],[-1,0,0],12,90);w.line(endpoints[b])
 elif previous[0]=='source_xpad':
  first=len(w.points)-1;w.arc([0,-1,0],[1,0,0],13,180);w.change_height(first,len(w.points)-1,-1.6)
  w.line([39.75,105.75,30]);w.arc([0,1,0],[1,0,0],13,90)
  w.line([84,118.75,30]);first=len(w.points)-1;w.s_curve([1,0,0],[0,1,0],14,12);w.change_height(first,len(w.points)-1,1.6)
  w.line(endpoints[b])
 else:w.line(endpoints[b])
 add(a,b,w)
assert len(paths)==19
sources=[Path(__file__),BASE/'r12_ground/ground-routes.json',BASE/'r13_formed_ground/exit-contract.json',BASE/'r11_distribution/reference/panel-contract.json',BASE/'r11_distribution/reference/signal-netlist.xml']
out={'source_sha256':{str(p.relative_to(REPO)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},'root':'D_J2002:15','net':'LINK_AGND','order':[{'button':name,'incoming_terminal':i,'outgoing_terminal':o} for name,i,o in order],'edges':paths,'internal_contact_pair':[3,4],'unused_last_terminal':'button_hold:4','wire_model_radius_mm':.6,'minimum_required_centerline_radius_mm':12,'terminal_approach':'Explicit horizontal/tangential solder approach; qualified joint preparation and local support still required. Internal switch connection is not an external wire bend.','complete_harness':False,'support_retention_qualified':False,'service_slack_included':False,'fabrication_released':False}
(HERE/'left-routes.json').write_text(json.dumps(out,indent=2)+'\n')
lines=['// Formed left-ground candidate; no fabrication release.','module left_segment(a,b){hull(){translate(a)sphere(r=.6,$fn=24);translate(b)sphere(r=.6,$fn=24);}}']
for e in paths:
 lines.append('module panel_ground_'+e['id']+'(){')
 for a,b in zip(e['points_mm'],e['points_mm'][1:]):lines.append('left_segment('+json.dumps(a)+','+json.dumps(b)+');')
 lines.append('}')
lines.append('module panel_ground_left_formed(){'+''.join('panel_ground_'+e['id']+'();' for e in paths)+'}')
lines.append('module panel_ground_left_feed(){panel_ground_L01();}')
lines.append('module panel_ground_left_links(){'+''.join('panel_ground_'+e['id']+'();' for e in paths[1:])+'}')
(HERE/'left.scad').write_text('\n'.join(lines)+'\n')
print('19 left-ground wires generated, source +18 links')
