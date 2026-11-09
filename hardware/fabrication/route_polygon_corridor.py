"""Geometric fallback for narrow corridors missed by a regular routing grid.

Triangulation only proposes paths. Every returned segment must pass the
caller's exact copper/reference screen before it can be used in a candidate.
"""
import heapq
import math
from collections import defaultdict
from shapely import constrained_delaunay_triangles
from shapely.geometry import Point, LineString
from shapely.strtree import STRtree


def corridor_path(free, start, end, legal):
    region=next((g for g in getattr(free,'geoms',[free]) if g.covers(Point(start)) and g.covers(Point(end))),None)
    if region is None:return None
    triangles=list(constrained_delaunay_triangles(region).geoms)
    if not triangles:return None
    tree=STRtree(triangles)
    starts=[int(i) for i in tree.query(Point(start)) if triangles[int(i)].covers(Point(start))]
    ends={int(i) for i in tree.query(Point(end)) if triangles[int(i)].covers(Point(end))}
    if not starts or not ends:return None
    centers=[tuple(g.centroid.coords[0]) for g in triangles]
    edges=defaultdict(list);adj=defaultdict(list)
    for i,t in enumerate(triangles):
        coords=list(t.exterior.coords)
        for a,b in zip(coords,coords[1:]):edges[tuple(sorted((a,b)))].append(i)
    for edge,ids in edges.items():
        if len(ids)!=2:continue
        a,b=ids;mid=tuple((x+y)/2 for x,y in zip(*edge))
        weight=math.dist(centers[a],mid)+math.dist(mid,centers[b])
        adj[a].append((b,mid,weight));adj[b].append((a,mid,weight))
    distance={i:math.dist(start,centers[i]) for i in starts};parent={};queue=[(v,i) for i,v in distance.items()];heapq.heapify(queue)
    target=None
    while queue:
        d,i=heapq.heappop(queue)
        if d>distance[i]+1e-9:continue
        if i in ends:target=i;break
        for j,mid,w in adj[i]:
            if d+w>=distance.get(j,math.inf):continue
            distance[j]=d+w;parent[j]=(i,mid);heapq.heappush(queue,(d+w,j))
    if target is None:return None
    points=[tuple(end),centers[target]]
    while target in parent:
        target,mid=parent[target];points.extend([mid,centers[target]])
    points.append(tuple(start));points.reverse()
    simplified=[points[0]];index=0
    while index<len(points)-1:
        reachable=[j for j in range(index+1,len(points)) if math.dist(points[index],points[j])>1e-7 and legal([points[index],points[j]])]
        if not reachable:return None
        index=max(reachable);simplified.append(points[index])
    if not legal(simplified):return None
    return simplified
