"""Bounded paths through continuous copper-free polygons, with exact final screens.

A triangle portal graph avoids quantising narrow legal passages onto a grid.
The result is a checked path, not a claim of the shortest geometric path.
"""
import heapq
import itertools
import math
import time

import shapely
from shapely.geometry import LineString, Point, box
from shapely.ops import unary_union
from shapely.strtree import STRtree


def free_space(screen, net, layer, contacts):
    obstacles = [g.buffer(d+.00001) for other,g,d in screen.geometry[layer] if other != net]
    obstacles += [g.buffer(.41001) for other,face,g in screen.added if face == layer and other != net]
    for other,point in screen.vias+screen.new_vias:
        if other != net:
            obstacles.append(Point(point).buffer(.61001))
        elif all(math.dist(point,p) > 1e-7 for p in contacts):
            obstacles.append(Point(point).buffer(.40001))
    return screen.outline.difference(unary_union(obstacles)).buffer(0)


def route(screen, net, layer, start, end, bounds, seconds=20):
    deadline = time.monotonic()+seconds
    free = free_space(screen,net,layer,[start,end]).intersection(box(*bounds)).buffer(0)
    part = next((p for p in getattr(free,'geoms',[free]) if p.covers(Point(start)) and p.covers(Point(end))),None)
    if part is None or shapely.get_num_coordinates(part)>50000:
        return None
    triangles = list(shapely.constrained_delaunay_triangles(part).geoms)
    if len(triangles)>50000 or time.monotonic()>deadline:
        return None
    owners,points = {},[]
    triangle_nodes = [[] for _ in triangles]
    for i,triangle in enumerate(triangles):
        coordinates = list(triangle.exterior.coords)
        for a,b in zip(coordinates,coordinates[1:]):
            key = tuple(sorted((a,b)))
            if key not in owners:
                owners[key] = i
                continue
            other = owners.pop(key)
            node = len(points)
            points.append(tuple((x+y)/2 for x,y in zip(a,b)))
            triangle_nodes[i].append(node)
            triangle_nodes[other].append(node)
    source = len(points)
    points.extend([tuple(start),tuple(end)])
    goal = source+1
    tree = STRtree(triangles)
    for node in (source,goal):
        p = Point(points[node])
        for i in tree.query(p):
            if triangles[int(i)].covers(p):
                triangle_nodes[int(i)].append(node)
    adjacency = [{} for _ in points]
    for rows in triangle_nodes:
        for a,b in itertools.combinations(rows,2):
            adjacency[a][b] = adjacency[b][a] = math.dist(points[a],points[b])
    costs,parents,visits = {source:0},{},0
    queue = [(math.dist(start,end),0,source)]
    while queue:
        _,cost,node = heapq.heappop(queue)
        if cost>costs[node]+1e-9:
            continue
        visits += 1
        if visits%1024==0 and time.monotonic()>deadline:
            return None
        if node==goal:
            break
        for other,length in adjacency[node].items():
            candidate = cost+length
            if candidate>=costs.get(other,math.inf)-1e-9:
                continue
            costs[other],parents[other] = candidate,node
            heapq.heappush(queue,(candidate+math.dist(points[other],end),candidate,other))
    if goal not in parents:
        return None
    nodes = [goal]
    while nodes[-1]!=source:
        nodes.append(parents[nodes[-1]])
    raw = [points[i] for i in reversed(nodes)]
    result,i = [list(start)],0
    shapely.prepare(part)
    while i<len(raw)-1:
        if time.monotonic()>deadline:
            return None
        candidates = list(range(len(raw)-1,i,-1))
        lines = shapely.linestrings([[raw[i],raw[j]] for j in candidates])
        covered = shapely.covers(part,lines)
        j = next((j for j,ok in zip(candidates,covered) if ok and screen.legal(net,layer,[raw[i],raw[j]])),None)
        if j is None:
            return None
        result.append([round(v,6) for v in raw[j]])
        i = j
    if len(result)>500 or not screen.legal(net,layer,result):
        return None
    return dict(points_mm=result,length_mm=LineString(result).length,layer=layer,
                mesh_triangles=len(triangles),graph_visits=visits,continuous_geometry=True)
