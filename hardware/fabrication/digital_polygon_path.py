"""Route through a triangulated free-space polygon without a raster grid.

Triangle adjacency supplies a continuous corridor. Every simplified segment
still needs the caller's independent copper-clearance screen.
"""
import heapq
import math
import time

from shapely import constrained_delaunay_triangles
from shapely.geometry import Point
from shapely.strtree import STRtree
from hardware.fabrication.digital_region_reachability import polygon_parts


def route(screen, net, face, start, end, free, deadline):
    start, end = tuple(start), tuple(end)
    component = next((p for p in polygon_parts(free) if p.covers(Point(start)) and p.covers(Point(end))), None)
    if component is None:
        return None
    if screen.legal(net, face, [start, end]):
        return [start, end]
    triangles = list(constrained_delaunay_triangles(component).geoms)
    if not triangles or time.monotonic() > deadline:
        return None
    tree = STRtree(triangles)
    sources = {int(i) for i in tree.query(Point(start)) if triangles[int(i)].covers(Point(start))}
    targets = {int(i) for i in tree.query(Point(end)) if triangles[int(i)].covers(Point(end))}
    assert sources and targets
    centres = [(t.centroid.x, t.centroid.y) for t in triangles]
    owners = {}
    adjacency = {}
    for i, triangle in enumerate(triangles):
        points = list(triangle.exterior.coords)
        assert len(points) == 4
        for p, q in zip(points, points[1:]):
            key = tuple(sorted((p, q)))
            if key in owners:
                j = owners[key]
                midpoint = tuple((x+y)/2 for x, y in zip(p, q))
                adjacency.setdefault(i, []).append((j, midpoint))
                adjacency.setdefault(j, []).append((i, midpoint))
            else:
                owners[key] = i
    costs = {i: math.dist(start, centres[i]) for i in sources}
    queue = [(g+math.dist(centres[i], end), g, i) for i, g in costs.items()]
    heapq.heapify(queue)
    parents = {}
    found = None
    while queue and time.monotonic() < deadline:
        _, cost, i = heapq.heappop(queue)
        if cost > costs[i] + 1e-9:
            continue
        if i in targets:
            found = i
            break
        for j, midpoint in adjacency.get(i, []):
            candidate = cost + math.dist(centres[i], centres[j])
            if candidate >= costs.get(j, math.inf):
                continue
            costs[j] = candidate
            parents[j] = (i, midpoint)
            heapq.heappush(queue, (candidate+math.dist(centres[j], end), candidate, j))
    if found is None:
        return None
    points = [end]
    while found in parents:
        found, midpoint = parents[found]
        points.append(midpoint)
    points.append(start)
    points.reverse()
    points = [p for i, p in enumerate(points) if i == 0 or p != points[i-1]]
    if not screen.legal(net, face, points):
        return None
    simple = [start]
    i = 0
    while i < len(points)-1:
        if time.monotonic() > deadline:
            return None
        target = i+1
        for j in range(min(len(points)-1, i+100), i+1, -1):
            if screen.legal(net, face, [points[i], points[j]]):
                target = j
                break
        simple.append(points[target])
        i = target
    assert screen.legal(net, face, simple)
    return simple
