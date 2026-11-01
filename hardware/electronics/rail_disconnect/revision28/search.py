"""Bounded 45-degree grid search; native DRC validates actual segments."""

import heapq
import itertools
import math

from ..revision26 import router as aid


def diagonal_connect(self, source, target, width):
    net = source["net"]
    self.last_search = {"net": net, "source": source["xy"], "target": target["xy"]}
    blocked, via_block = self.masks(net, width)
    start_xy = tuple(round(v / aid.STEP) for v in source["xy"])
    end_xy = tuple(round(v / aid.STEP) for v in target["xy"])
    starts = [(*start_xy, z) for z in source["layers"] if not blocked[z, start_xy[0], start_xy[1]]]
    goals = {(*end_xy, z) for z in target["layers"] if not blocked[z, end_xy[0], end_xy[1]]}
    if not starts or not goals:
        self.last_search.update(reason="no_start_or_goal", starts=len(starts), goals=len(goals))
        return False
    queue, serial, costs, previous = [], itertools.count(), {s: 0 for s in starts}, {}

    def h(p):
        return abs(p[0] - end_xy[0]) + abs(p[1] - end_xy[1])

    for start in starts:
        heapq.heappush(queue, (h(start), next(serial), start))
    visited = set()
    found = None
    while queue:
        _, _, point = heapq.heappop(queue)
        if point in visited:
            continue
        visited.add(point)
        if len(visited) > getattr(self, "max_search_nodes", 200000):
            self.last_search.update(reason="search_node_budget", visited=len(visited))
            return False
        if point in goals:
            found = point
            break
        x, y, z = point
        neighbors = [
            (x + dx, y + dy, z, math.hypot(dx, dy))
            for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1))
            if 0 <= x + dx < self.nx and 0 <= y + dy < self.ny and not blocked[z, x + dx, y + dy]
        ]
        if not via_block[x, y]:
            neighbors.extend(
                (x, y, other, 12) for other in range(6) if other != z and not blocked[other, x, y]
            )
        for u, v, w, increment in neighbors:
            other = (u, v, w)
            cost = costs[point] + increment
            if cost < costs.get(other, float("inf")):
                costs[other] = cost
                previous[other] = point
                heapq.heappush(
                    queue, (cost + getattr(self, "search_bias", 1) * h(other), next(serial), other)
                )
    if found is None:
        self.last_search.update(reason="no_clearance_path_in_actual_grid", visited=len(visited))
        return False
    nodes = [found]
    while nodes[-1] in previous:
        nodes.append(previous[nodes[-1]])
    nodes.reverse()
    anchor = nodes[0]
    points = [source["xy"], (anchor[0] * aid.STEP, anchor[1] * aid.STEP)]
    direction = None
    for before, after in zip(nodes, nodes[1:]):
        delta = (after[0] - before[0], after[1] - before[1], after[2] - before[2])
        if delta[2]:
            point = (before[0] * aid.STEP, before[1] * aid.STEP)
            points.append(point)
            self.path(net, before[2], points, width)
            self.via(net, point)
            points = [point]
            direction = None
        elif direction != delta:
            points.append((before[0] * aid.STEP, before[1] * aid.STEP))
            direction = delta
    points.extend([(nodes[-1][0] * aid.STEP, nodes[-1][1] * aid.STEP), target["xy"]])
    self.path(net, nodes[-1][2], points, width)
    self.last_search.update(reason="connected", visited=len(visited))
    return True
