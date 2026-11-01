"""Continuous-coordinate fine local route between existing C40 ground barrels."""

import heapq
import itertools
import math

import numpy as np


def path_between(rt, start, finish, layer, margin=4, step=0.025):
    low = [min(start[i], finish[i]) - margin for i in (0, 1)]
    high = [max(start[i], finish[i]) + margin for i in (0, 1)]
    x = np.arange(max(0.625, low[0]), high[0] + step / 2, step)
    y = np.arange(max(0.625, low[1]), high[1] + step / 2, step)
    xx, yy = x[:, None], y[None, :]
    blocked = np.zeros((len(x), len(y)), bool)
    for g in rt.geometry:
        if g["net"] == "AGND" or layer not in g["layers"]:
            continue
        extra = 0.321
        if g["kind"] == "line":
            ax, ay = g["start"]
            bx, by = g["end"]
            dx, dy = bx - ax, by - ay
            t = np.clip(((xx - ax) * dx + (yy - ay) * dy) / max(dx * dx + dy * dy, 1e-30), 0, 1)
            blocked |= (xx - ax - t * dx) ** 2 + (yy - ay - t * dy) ** 2 < (g["width"] / 2 + extra) ** 2
        elif g["kind"] == "via":
            gx, gy = g["xy"]
            blocked |= (xx - gx) ** 2 + (yy - gy) ** 2 < (g["radius"] + extra) ** 2
        else:
            gx, gy = g["xy"]
            w, h = g["size"]
            blocked |= (
                np.maximum(abs(xx - gx) - w / 2, 0) ** 2 + np.maximum(abs(yy - gy) - h / 2, 0) ** 2 < extra**2
            )

    def cell(p):
        return tuple(int(np.argmin(abs(axis - value))) for axis, value in zip((x, y), p))

    source, target = cell(start), cell(finish)
    assert not blocked[source] and not blocked[target]
    serial = itertools.count()
    queue = [(0, next(serial), source)]
    cost = {source: 0}
    previous = {}
    visited = set()
    while queue:
        _, _, p = heapq.heappop(queue)
        if p in visited:
            continue
        visited.add(p)
        if p == target:
            break
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)):
            q = (p[0] + dx, p[1] + dy)
            if not (0 <= q[0] < len(x) and 0 <= q[1] < len(y)) or blocked[q]:
                continue
            value = cost[p] + math.hypot(dx, dy)
            if value < cost.get(q, float("inf")):
                cost[q] = value
                previous[q] = p
                heapq.heappush(queue, (value + math.dist(q, target), next(serial), q))
    assert target in visited, ("No actual local clearance path between existing barrels",
        len(visited), ((float(x[min(p[0] for p in visited)]),float(y[min(p[1] for p in visited)])),
        (float(x[max(p[0] for p in visited)]),float(y[max(p[1] for p in visited)]))))
    nodes = [target]
    while nodes[-1] != source:
        nodes.append(previous[nodes[-1]])
    nodes.reverse()
    points = [start]
    direction = None
    for p, q in zip(nodes, nodes[1:]):
        delta = (q[0] - p[0], q[1] - p[1])
        if delta != direction:
            points.append((float(x[p[0]]), float(y[p[1]])))
            direction = delta
    points.append(finish)
    return points, len(visited)
