"""Bounded one-via connections between already escaped signal groups."""
import math
from shapely.geometry import Point,LineString

def find_hop(screen,a,targets,layers,inner_free,quiet_fields,maxlen):
 net=a['net'];start=a['position_mm'];ranked=[];seen=set();cache={}
 def simple(layer,p,q,limit):
  key=(layer,tuple(p),tuple(q))
  if key not in cache:cache[key]=screen.simple(net,layer,p,q,limit)
  return cache[key]
 for t in sorted(targets,key=lambda t:math.dist(start,t['position_mm'])):
  if t['net']!=net:continue
  end=t['position_mm'];key=tuple(end)
  if key in seen:continue
  seen.add(key)
  if len(seen)>5:break
  distance=math.dist(start,end);limit=min(maxlen,1.7*distance+10)
  ls=[l for l in layers if inner_free(a,l)]
  lt=[l for l in layers if inner_free(t,l) and (t.get('kind')=='PCB_VIA' or t.get('size_mm') or t.get('layers',{}).get(l))]
  sites=set()
  for fraction in [.25,.5,.75]:
   center=[start[i]+fraction*(end[i]-start[i]) for i in [0,1]]
   for dx in [-9,-6,-3,0,3,6,9]:
    for dy in [-9,-6,-3,0,3,6,9]:sites.add((round(center[0]+dx,1),round(center[1]+dy,1)))
  trials=0
  for xy in sorted(sites,key=lambda p:math.dist(start,p)+math.dist(p,end)):
   lower=math.dist(start,xy)+math.dist(xy,end)
   if lower>limit or min(math.dist(start,xy),math.dist(end,xy))<1:continue
   if not screen.via_legal(net,xy) or any(Point(xy).distance(q)<.6 for q in quiet_fields):continue
   v=dict(ref=a.get('ref'),pin=a.get('pin'),net=net,position_mm=list(xy),size_mm=.6,drill_mm=.3)
   free=[l for l in layers if inner_free(v,l)]
   trials+=1
   for left in ls:
    for right in lt:
     if left==right or left not in free or right not in free:continue
     p=simple(left,start,xy,limit);q=simple(right,xy,end,limit)
     if p and q and p[0]+q[0]<=limit:return t,v,[(left,p[1]),(right,q[1])]
     if bool(p)!=bool(q):ranked.append((lower,t,v,left,right,p,q,limit))
   if trials>=24:break
 for lower,t,v,left,right,p,q,limit in sorted(ranked,key=lambda x:x[0])[:6]:
  if not p:
   points=screen.grid_path(net,left,start,v['position_mm'],budget=30000)
   if points:p=(LineString(points).length,points)
  else:
   points=screen.grid_path(net,right,v['position_mm'],t['position_mm'],budget=30000)
   if points:q=(LineString(points).length,points)
  if p and q and p[0]+q[0]<=limit:return t,v,[(left,p[1]),(right,q[1])]
 return None
