"""Bounded visibility search; every emitted line uses the exact copper screen."""
import heapq,math,time
import numpy as np
from scipy.spatial import cKDTree
from shapely.geometry import Point,box


def route(screen,net,face,start,end,free_region,deadline):
    # Clipping bounds work and never expands legal copper space.
    bounds=box(min(start[0],end[0])-3,min(start[1],end[1])-3,max(start[0],end[0])+3,max(start[1],end[1])+3)
    clipped=free_region.intersection(bounds)
    regions=[clipped] if clipped.geom_type=='Polygon' else list(getattr(clipped,'geoms',[]))
    region=next((r for r in regions if r.covers(Point(start)) and r.covers(Point(end))),None)
    if region is None:return None
    points=[tuple(start),tuple(end)]
    for ring in [region.exterior,*region.interiors]:
        points.extend((float(x),float(y)) for x,y in list(ring.coords)[:-1])
    points=list(dict.fromkeys(points));assert points[:2]==[tuple(start),tuple(end)]
    if len(points)>10000:return None
    tree=cKDTree(points);cost={0:0.};parent={};queue=[(math.dist(start,end),0.,0)];edges={}
    while queue and time.monotonic()<deadline:
        _,g,i=heapq.heappop(queue)
        if g>cost[i]+1e-9:continue
        if i==1:
            path=[points[i]]
            while i in parent:i=parent[i];path.append(points[i])
            path.reverse();assert screen.legal(net,face,path)
            return path
        # Include the destination even when outside the local neighborhood.
        neighbors={1}|set(map(int,np.atleast_1d(tree.query(points[i],k=min(len(points),192))[1])))
        for j in neighbors:
            if j==i:continue
            candidate=g+math.dist(points[i],points[j])
            if candidate>=cost.get(j,math.inf)-1e-9:continue
            key=tuple(sorted((i,j)))
            if key not in edges:edges[key]=screen.legal(net,face,[points[i],points[j]])
            if not edges[key]:continue
            cost[j]=candidate;parent[j]=i;heapq.heappush(queue,(candidate+math.dist(points[j],end),candidate,j))
    return None
