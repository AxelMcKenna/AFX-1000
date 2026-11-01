"""Actual 0.2mm-clear surface paths to existing physical terminals; no new drills.

Uses circular Minkowski distance at foreign rectangular land corners rather than
conservative square-expanded corner masks. Filled-force changes are NOT guarded:
this is an explicit local surface-routing trial requiring native fill/PDN review.
"""

import heapq
import itertools
import math

import numpy as np


def connect(rt, pad, targets, radius=12, step=0.025, budget=600000):
    px, py = pad["xy"]
    extent = math.ceil(radius / step)
    xs = px + (np.arange(2 * extent + 1) - extent) * step
    ys = py + (np.arange(2 * extent + 1) - extent) * step
    xx = xs[:, None]
    yy = ys[None, :]
    face = pad["layers"][0]
    net = pad["net"]
    blocked = np.zeros((len(xs), len(ys)), bool)
    margin = 0.200001 + 0.1 + 0.02
    for g in rt.geometry:
        if g["net"] == net or face not in g["layers"] or g["net"] == "BULK_BODY_NOVIA":
            continue
        if g["kind"] == "line":
            ax, ay = g["start"]
            bx, by = g["end"]
            r = g["width"] / 2 + margin
            if (
                max(ax, bx) + r < xs[0]
                or min(ax, bx) - r > xs[-1]
                or max(ay, by) + r < ys[0]
                or min(ay, by) - r > ys[-1]
            ):
                continue
            dx, dy = bx - ax, by - ay
            t = np.clip(((xx - ax) * dx + (yy - ay) * dy) / max(dx * dx + dy * dy, 1e-30), 0, 1)
            blocked |= (xx - ax - t * dx) ** 2 + (yy - ay - t * dy) ** 2 < r * r
        elif g["kind"] == "via":
            gx, gy = g["xy"]
            r = g["radius"] + margin
            if gx + r < xs[0] or gx - r > xs[-1] or gy + r < ys[0] or gy - r > ys[-1]:
                continue
            blocked |= (xx - gx) ** 2 + (yy - gy) ** 2 < r * r
        else:
            gx, gy = g["xy"]
            w, h = g["size"]
            if (
                gx + w / 2 + margin < xs[0]
                or gx - w / 2 - margin > xs[-1]
                or gy + h / 2 + margin < ys[0]
                or gy - h / 2 - margin > ys[-1]
            ):
                continue
            blocked |= (
                np.maximum(abs(xx - gx) - w / 2, 0) ** 2 + np.maximum(abs(yy - gy) - h / 2, 0) ** 2
                < margin * margin
            )
    blocked |= (
        (xx < 0.75)
        | (xx > 155.25)
        | (yy < 0.75)
        | (yy > 53.75)
        | ((xx < 5.75) & (yy > 34.25))
        | ((xx > 153.75) & (yy > 34.5))
    )
    start = (extent, extent)
    if blocked[start]:
        return None, "source centre physically trapped"
    goal = {}
    for p in targets:
        x, y = p["xy"]
        ix, iy = round((x - px) / step) + extent, round((y - py) / step) + extent
        if 0 <= ix < len(xs) and 0 <= iy < len(ys) and not blocked[ix, iy]:
            goal[ix, iy] = p
    if not goal:
        return None, "no reachable same-face physical terminal inside local extent"
    # Exact target-coordinate containment is checked again on the final short leg.
    from hardware.electronics.rail_disconnect.revision28.focused import legal_line

    goal = {
        k: v
        for k, v in goal.items()
        if math.dist((float(xs[k[0]]), float(ys[k[1]])), v["xy"]) < 1e-10
        or legal_line(rt, net, face, (float(xs[k[0]]), float(ys[k[1]])), v["xy"], 0.2)
    }
    if not goal:
        return None, "off-grid terminal final leg violates physical clearance"

    def heuristic(p):
        return min(math.hypot(p[0] - q[0], p[1] - q[1]) for q in goal)

    serial = itertools.count()
    q = [(heuristic(start), next(serial), start)]
    costs = {start: 0}
    previous = {}
    visited = set()
    found = None
    while q:
        _, _, p = heapq.heappop(q)
        if p in visited:
            continue
        visited.add(p)
        if len(visited) > budget:
            break
        if p in goal:
            found = p
            break
        for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1)):
            n = p[0] + dx, p[1] + dy
            if not (0 <= n[0] < len(xs) and 0 <= n[1] < len(ys)) or blocked[n]:
                continue
            val = costs[p] + math.hypot(dx, dy)
            if val < costs.get(n, float("inf")):
                costs[n] = val
                previous[n] = p
                heapq.heappush(q, (val + 1.5 * heuristic(n), next(serial), n))
    if found is None:
        return None, f"no physical local path; visited{len(visited)}"
    nodes = [found]
    while nodes[-1] != start:
        nodes.append(previous[nodes[-1]])
    nodes.reverse()
    points = [pad["xy"]]
    direction = None
    for p, n in zip(nodes, nodes[1:]):
        d = n[0] - p[0], n[1] - p[1]
        if d != direction:
            points.append((float(xs[p[0]]), float(ys[p[1]])))
            direction = d
    points.extend([(float(xs[found[0]]), float(ys[found[1]])), tuple(goal[found]["xy"])])
    points = [tuple(round(float(v), 6) for v in p) for p in points]
    points = [p for i, p in enumerate(points) if not i or p != points[i - 1]]
    # Raster diagonal steps may cut a corner between nodes. Native geometry is
    # checked analytically on every compressed segment before adding any Cu.
    if not all(legal_line(rt, net, face, a, b, 0.2) for a, b in zip(points, points[1:])):
        return None, "candidate raster corner fails exact full-segment clearance"
    from hardware.electronics.rail_disconnect.revision26 import router as aid

    aid.STEP = step
    rt.path(net, face, points, 0.2)
    return dict(
        path=points, target=goal[found], layer_index=face, visited=len(visited), no_drill_added=True
    ), None
