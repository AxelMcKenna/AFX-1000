"""Bounded multilayer A* with exact final copper and through-via screens."""
import math,heapq,itertools
import numpy as np
from shapely import contains_xy,points,distance
from shapely.geometry import Point,LineString,box
from shapely.ops import unary_union,nearest_points
from shapely.prepared import prep

def search(screen,net,start,targets,quiet,layers=('In2.Cu','In3.Cu','In4.Cu','In6.Cu')):
 step=.4;region=box(78,123,158,168);x0,y0,x1,y1=region.bounds
 xs=np.arange(x0,x1+step/2,step);ys=np.arange(y0,y1+step/2,step);nx,ny=len(xs),len(ys)
 xy=lambda k:(round(float(xs[k[0]]),6),round(float(ys[k[1]]),6))
 allowed=[];free=[];prepared=[]
 for layer in layers:
  obs=[g.buffer(d+.000001) for other,g,d in screen.geometry[layer] if other!=net and g.intersects(region.buffer(d))]
  obs.extend(g.buffer(.410001) for other,l,g in screen.added if other!=net and l==layer and g.intersects(region.buffer(.411)))
  obs.extend(p.buffer(r+.110001) for ref,p,r in screen.mounts)
  a=screen.outline.intersection(region).difference(unary_union(obs));allowed.append(a);prepared.append(prep(a));free.append(contains_xy(a,xs[None,:],ys[:,None]))
 obs=[g.buffer(.510001) for other,g in screen.copper if other!=net and g.intersects(region.buffer(.52))]
 obs.extend(g.buffer(.310001) for g in screen.smd if g.intersects(region.buffer(.32)))
 obs.extend(Point(p).buffer(.15+r+.260001) for p,r in screen.holes if region.buffer(1).covers(Point(p)))
 obs.extend(Point(p).buffer(.560001 if other==net else .810001) for other,p in screen.vias)
 obs.extend(g.buffer(.610001) for other,l,g in screen.added if other!=net and g.intersects(region.buffer(.62)))
 obs.extend(p.buffer(r+.310001) for ref,p,r in screen.mounts)
 obs.extend(q.buffer(.600001) for q in quiet)
 va=screen.via_outline.intersection(region).difference(unary_union(obs));vf=contains_xy(va,xs[None,:],ys[:,None])
 goals={};starts={}
 def nearby(pt):
  ix,iy=round((pt[0]-x0)/step),round((pt[1]-y0)/step)
  return [(ix+dx,iy+dy) for dx,dy in itertools.product(range(-2,3),repeat=2) if 0<=ix+dx<nx and 0<=iy+dy<ny]
 for li,layer in enumerate(layers):
  for k in nearby(start):
   if free[li][k[1],k[0]] and (math.dist(start,xy(k))<1e-7 or screen.legal(net,layer,[start,xy(k)])):starts[(*k,li)]=math.dist(start,xy(k))
  for t in targets:
   if layer not in t['layers']:continue
   pt=t['position_mm']
   for k in nearby(pt):
    if free[li][k[1],k[0]] and (math.dist(pt,xy(k))<1e-7 or screen.legal(net,layer,[xy(k),pt])):
     key=(*k,li)
     if key not in goals or math.dist(xy(k),pt)<math.dist(xy(k),goals[key]):goals[key]=pt
 assert starts and goals,(len(starts),len(goals))
 geom=unary_union([Point(pt) for pt in goals.values()]);xx,yy=np.meshgrid(xs,ys);heur=distance(points(xx,yy),geom)
 queue=[(cost+heur[k[1],k[0]],cost,k) for k,cost in starts.items()];heapq.heapify(queue);costs=dict(starts);parent={};edgecache={};viacache={};visits=0;found=None
 while queue and visits<220000:
  _,cost,k=heapq.heappop(queue)
  if cost>costs[k]+1e-9:continue
  visits+=1
  if k in goals:found=k;break
  ix,iy,li=k
  neighbors=[]
  for dx,dy in itertools.product([-1,0,1],repeat=2):
   if not(dx or dy):continue
   n=(ix+dx,iy+dy,li)
   if 0<=n[0]<nx and 0<=n[1]<ny and free[li][n[1],n[0]]:neighbors.append((n,math.hypot(dx,dy)*step,False))
  if vf[iy,ix]:
   for lj in range(len(layers)):
    if li!=lj and free[lj][iy,ix]:neighbors.append(((ix,iy,lj),4.,True))
  for n,delta,via in neighbors:
   nc=cost+delta
   if nc>=costs.get(n,math.inf)-1e-9 or nc>210:continue
   if via:
    point=(ix,iy)
    if point not in viacache:viacache[point]=screen.via_legal(net,xy(k))
    if not viacache[point]:continue
   else:
    e=tuple(sorted([k,n]))
    if e not in edgecache:edgecache[e]=prepared[li].covers(LineString([xy(k),xy(n)]))
    if not edgecache[e]:continue
   costs[n]=nc;parent[n]=k;heapq.heappush(queue,(nc+heur[n[1],n[0]],nc,n))
 print('MULTILAYER',visits,'starts',len(starts),'goals',len(goals),'found',bool(found),flush=True)
 if found is None:return None
 chain=[found]
 while chain[-1] in parent:chain.append(parent[chain[-1]])
 chain.reverse();legs=[];vias=[];layer=layers[chain[0][2]];path=[start,xy(chain[0])]
 for a,b in zip(chain,chain[1:]):
  if a[2]!=b[2]:legs.append((layer,path));vias.append(xy(a));layer=layers[b[2]];path=[xy(b)]
  else:path.append(xy(b))
 path.append(goals[found]);legs.append((layer,path));result=[]
 for layer,path in legs:
  path=[p for i,p in enumerate(path) if not i or math.dist(p,path[i-1])>1e-7];assert len(path)>1
  out=[path[0]];i=0
  while i<len(path)-1:
   for j in range(len(path)-1,i,-1):
    if screen.legal(net,layer,[path[i],path[j]]):break
   else:raise AssertionError('Final path failed exact geometry')
   out.append(path[j]);i=j
  assert screen.legal(net,layer,out);result.append((layer,out))
 assert all(math.dist(a,b)>.56 for i,a in enumerate(vias) for b in vias[:i])
 return result,vias
