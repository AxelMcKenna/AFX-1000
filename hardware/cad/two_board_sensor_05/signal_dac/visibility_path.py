"""Bounded polygon visibility search; every returned segment stays in the supplied domain."""
import heapq
import math
from shapely.geometry import Point, LineString
from shapely.prepared import prep


def visibility_path(area, start, end, max_nodes=1024):
    inset = area.buffer(-.00001)
    parts = list(inset.geoms) if hasattr(inset, 'geoms') else [inset]
    domain = next((p for p in parts if p.covers(Point(start)) and p.covers(Point(end))), None)
    if domain is None:
        return None
    outline = domain.simplify(.0001, preserve_topology=True)
    points = [list(start), list(end)]
    points.extend(list(p) for ring in [outline.exterior, *outline.interiors]
                  for p in list(ring.coords)[:-1] if domain.covers(Point(p)))
    assert len(points) <= max_nodes, ('visibility node budget', len(points))
    field = prep(domain.buffer(1e-9))
    queue, cost, previous = [(0., 0)], {0: 0.}, {}
    while queue:
        distance, index = heapq.heappop(queue)
        if distance != cost[index]:
            continue
        if index == 1:
            path = [points[index]]
            while index:
                index = previous[index]
                path.append(points[index])
            result = [[round(v, 6) for v in p] for p in reversed(path)]
            assert area.covers(LineString(result)), 'rounded path leaves exact input domain'
            return result
        for target, point in enumerate(points):
            if target == index:
                continue
            score = distance + math.dist(points[index], point)
            if score >= cost.get(target, math.inf):
                continue
            if field.covers(LineString([points[index], point])):
                cost[target], previous[target] = score, index
                heapq.heappush(queue, (score, target))
    return None
