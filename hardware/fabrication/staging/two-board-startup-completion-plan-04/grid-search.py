"""Coarse-to-fine path search using a net-specific polygon free-space mask.

Every emitted path is independently checked by the original exact screen.
This is a planning accelerator, not a replacement for native DRC.
"""
import heapq,itertools,math
import numpy as np
from shapely import contains_xy
from shapely.geometry import Point,LineString,box
from shapely.ops import unary_union
from shapely.prepared import prep

def fast_grid_path(self,net,layer,start,end,budget=45000):
 for step in [.2,.1]:
  margin=25
  bounds=[min(start[0],end[0])-margin,min(start[1],end[1])-margin,max(start[0],end[0])+margin,max(start[1],end[1])+margin]
  region=box(*bounds);obstacles=[]
  for other,g,d in self.geometry[layer]:
   if other!=net and g.intersects(region.buffer(d)):obstacles.append(g.buffer(d+.000001))
  for other,l,g in self.added:
   if other!=net and l==layer and g.intersects(region.buffer(.411)):obstacles.append(g.buffer(.410001))
  obstacles.extend(center.buffer(radius+.110001) for ref,center,radius in self.mounts)
  allowed=self.outline.intersection(region).difference(unary_union(obstacles));prepared=prep(allowed)
  x0,y0=[math.floor(bounds[i]/step)*step for i in [0,1]];nx=math.ceil((bounds[2]-x0)/step)+1;ny=math.ceil((bounds[3]-y0)/step)+1
  xs=x0+np.arange(nx)*step;ys=y0+np.arange(ny)*step;free=contains_xy(allowed,xs[None,:],ys[:,None])
  xy=lambda k:(round(xs[k[0]],6),round(ys[k[1]],6))
  def nearby(point):
   ix,iy=round((point[0]-x0)/step),round((point[1]-y0)/step);out=[]
   for dx,dy in itertools.product(range(-2,3),repeat=2):
    k=(ix+dx,iy+dy)
    if 0<=k[0]<nx and 0<=k[1]<ny and free[k[1],k[0]]:
     q=xy(k)
     if math.dist(point,q)<1e-6 or self.legal(net,layer,[point,q]):out.append(k)
   return out
  starts,ends=nearby(start),set(nearby(end))
  if not starts or not ends:continue
  costs={k:math.dist(start,xy(k)) for k in starts};parents={};queue=[(costs[k]+math.dist(xy(k),end),costs[k],k) for k in starts];heapq.heapify(queue);edges={};visits=0;goal=None
  while queue and visits<max(budget,90000):
   _,distance,k=heapq.heappop(queue)
   if distance>costs[k]+1e-9:continue
   visits+=1
   if k in ends:goal=k;break
   for dx,dy in itertools.product([-1,0,1],repeat=2):
    if not(dx or dy):continue
    n=(k[0]+dx,k[1]+dy)
    if not(0<=n[0]<nx and 0<=n[1]<ny and free[n[1],n[0]]):continue
    new=distance+math.hypot(dx,dy)*step
    if new>=costs.get(n,math.inf)-1e-9:continue
    edge=tuple(sorted([k,n]))
    if edge not in edges:edges[edge]=prepared.covers(LineString([xy(k),xy(n)]))
    if not edges[edge]:continue
    costs[n]=new;parents[n]=k;heapq.heappush(queue,(new+math.dist(xy(n),end),new,n))
  if goal is None:continue
  keys=[goal]
  while keys[-1] in parents:keys.append(parents[keys[-1]])
  points=[list(start)]+[list(xy(k)) for k in reversed(keys)]+[list(end)];points=[p for i,p in enumerate(points) if not i or p!=points[i-1]]
  reduced=[points[0]];i=0
  while i<len(points)-1:
   for j in range(len(points)-1,i,-1):
    if self.legal(net,layer,[points[i],points[j]]):break
   else:raise AssertionError('Free-space path failed original exact screen')
   reduced.append(points[j]);i=j
  assert self.legal(net,layer,reduced)
  print('FAST GRID',layer,'step',step,'visits',visits,'length',round(LineString(reduced).length,3),flush=True)
  return reduced
 return None
