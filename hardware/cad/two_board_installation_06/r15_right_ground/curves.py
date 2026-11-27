"""Curve primitives reused from the frozen left-route generator; no assembly side effects."""
import math
import numpy as np
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
