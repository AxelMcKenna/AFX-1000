"""Bounded grid routing with explicit geometry bounds and auditable failure reasons."""
import heapq
import math


def bounded_path(legal, start, end, bounds, step=.1, max_nodes=100000):
    origin = tuple(round(v / step) for v in start)
    goal = tuple(round(v / step) for v in end)
    lower = (math.ceil(bounds[0] / step), math.ceil(bounds[1] / step))
    upper = (math.floor(bounds[2] / step), math.floor(bounds[3] / step))
    def xy(key):
        return tuple(round(v * step, 6) for v in key)
    def edge(a, b):
        return math.dist(a, b) < 1e-9 or legal([a, b])
    if not edge(start, xy(origin)) or not edge(xy(goal), end):
        return {'path': None, 'reason': 'endpoint_grid_bridge', 'visited': 0}
    if any(not all(lo <= v <= hi for lo, v, hi in zip(lower, point, upper)) for point in [origin, goal]):
        return {'path': None, 'reason': 'endpoint_outside_bounds', 'visited': 0}
    queue, costs, parents, cached = [(math.dist(origin, goal), 0., origin)], {origin: 0.}, {}, {}
    visited = 0
    while queue and visited < max_nodes:
        _, distance, key = heapq.heappop(queue)
        if distance != costs[key]:
            continue
        visited += 1
        if key == goal:
            keys = [key]
            while key in parents:
                key = parents[key]
                keys.append(key)
            points = [tuple(start), *[xy(k) for k in reversed(keys)], tuple(end)]
            points = [p for i, p in enumerate(points) if i == 0 or p != points[i-1]]
            route, index = [points[0]], 0
            while index < len(points)-1:
                target = index+1
                for j in range(len(points)-1, index+1, -1):
                    if edge(points[index], points[j]):
                        target = j
                        break
                route.append(points[target])
                index = target
            assert legal(route), 'simplified path failed exact segment screen'
            return {'path': route, 'reason': 'connected', 'visited': visited}
        for dx, dy in [(-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1)]:
            target = key[0]+dx, key[1]+dy
            if not all(lo <= v <= hi for lo, v, hi in zip(lower, target, upper)):
                continue
            score = distance + math.hypot(dx, dy)
            if score >= costs.get(target, math.inf):
                continue
            cache_key = tuple(sorted((key, target)))
            if cache_key not in cached:
                cached[cache_key] = edge(xy(key), xy(target))
            if not cached[cache_key]:
                continue
            costs[target], parents[target] = score, key
            heapq.heappush(queue, (score + math.dist(target, goal), score, target))
    return {'path': None, 'reason': 'node_budget' if queue else 'disconnected_grid', 'visited': visited}
