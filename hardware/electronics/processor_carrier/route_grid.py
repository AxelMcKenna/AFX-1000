"""E19 variable-width geometric routing aid adapted from E18; actual KiCad DRC is required."""

import heapq
import itertools
import math

import numpy as np

STEP = 0.25
LAYERS = ("In2.Cu", "B.Cu", "F.Cu")


def connect(router, tasks, size):
    nx, ny = int(size[0] / STEP) + 1, int(size[1] / STEP) + 1

    def point(xy):
        return (round(xy[0] / STEP), round(xy[1] / STEP))

    def xy(node):
        return (node[0] * STEP, node[1] * STEP)

    def masks(net, extra, layers):
        blocks = np.zeros((len(layers), nx, ny), dtype=bool)
        blocks[:, :4, :] = True
        blocks[:, -4:, :] = True
        blocks[:, :, :4] = True
        blocks[:, :, -4:] = True
        margin = 0.25 + extra + 0.015
        for shape in router.geometry:
            if shape["net"] == net:
                continue
            active = [i for i, l in enumerate(layers) if l in shape["layers"]]
            if not active:
                continue
            if shape["kind"] == "line":
                start, end = shape["start"], shape["end"]
                radius = shape["w"] / 2 + margin
                x0, x1 = min(start[0], end[0]) - radius, max(start[0], end[0]) + radius
                y0, y1 = min(start[1], end[1]) - radius, max(start[1], end[1]) + radius
            else:
                wx = shape["w"] / 2 if shape["kind"] == "rect" else shape["r"]
                wy = shape["h"] / 2 if shape["kind"] == "rect" else shape["r"]
                x0, x1 = shape["x"] - wx - margin, shape["x"] + wx + margin
                y0, y1 = shape["y"] - wy - margin, shape["y"] + wy + margin
            ix0, ix1 = max(0, math.floor(x0 / STEP)), min(nx, math.ceil(x1 / STEP) + 1)
            iy0, iy1 = max(0, math.floor(y0 / STEP)), min(ny, math.ceil(y1 / STEP) + 1)
            x = np.arange(ix0, ix1)[:, None] * STEP
            y = np.arange(iy0, iy1)[None, :] * STEP
            if shape["kind"] == "line":
                dx, dy = end[0] - start[0], end[1] - start[1]
                t = np.clip(((x - start[0]) * dx + (y - start[1]) * dy) / (dx * dx + dy * dy), 0, 1)
                hit = (x - start[0] - t * dx) ** 2 + (y - start[1] - t * dy) ** 2 <= radius * radius
            elif shape["kind"] == "circle":
                hit = (x - shape["x"]) ** 2 + (y - shape["y"]) ** 2 <= (shape["r"] + margin) ** 2
            else:
                hit = (x >= x0) & (x <= x1) & (y >= y0) & (y <= y1)
            for layer in active:
                blocks[layer, ix0:ix1, iy0:iy1] |= hit
        return blocks

    for net, targets in tasks.items():
        width = {"5V_DIG": 0.8, "SEED_VIN": 0.75, "V3V3_IO": 0.5, "V3V3_ANALOG": 0.4}.get(net, 0.25)
        connected = [targets[0]]
        for target in targets[1:]:
            start = min(connected, key=lambda p: math.dist(p, target))
            blocked = masks(net, width / 2, LAYERS)
            via_block = np.any(masks(net, 0.3, ("F.Cu", "In2.Cu", "B.Cu")), axis=0)
            start2, end2 = point(start), point(target)
            starts = [(*start2, layer) for layer in range(len(LAYERS)) if not blocked[layer, *start2]]
            goals = {(*end2, layer) for layer in range(len(LAYERS)) if not blocked[layer, *end2]}
            assert starts and goals, (net, "blocked endpoint", start, target)
            serial = itertools.count()
            queue = []
            cost = {s: 0 for s in starts}
            prev = {}

            def h(n):
                return abs(n[0] - end2[0]) + abs(n[1] - end2[1])

            for node in starts:
                heapq.heappush(queue, (h(node), next(serial), node))
            visited = set()
            found = None
            while queue:
                _, _, node = heapq.heappop(queue)
                if node in visited:
                    continue
                visited.add(node)
                if node in goals:
                    found = node
                    break
                x, y, z = node
                neighbors = [
                    (x + dx, y + dy, z, 1)
                    for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1))
                    if 0 <= x + dx < nx and 0 <= y + dy < ny and not blocked[z, x + dx, y + dy]
                ]
                if not via_block[x, y]:
                    neighbors.extend((x, y, layer, 16) for layer in range(len(LAYERS)) if layer != z)
                for u, v, w, increment in neighbors:
                    other = (u, v, w)
                    candidate = cost[node] + increment
                    if candidate < cost.get(other, float("inf")):
                        cost[other] = candidate
                        prev[other] = node
                        heapq.heappush(queue, (candidate + h(other), next(serial), other))
            assert found is not None, (net, "unroutable", target)
            path = [found]
            while path[-1] in prev:
                path.append(prev[path[-1]])
            path.reverse()
            router.path(net, LAYERS[path[0][2]].split(".")[0], start, xy(path[0]), width=width)
            anchor = path[0]
            last_direction = None
            for before, after in zip(path, path[1:]):
                direction = (after[0] - before[0], after[1] - before[1], after[2] - before[2])
                if direction[2]:
                    router.path(net, LAYERS[before[2]].split(".")[0], xy(anchor), xy(before), width=width)
                    router.via(net, xy(before))
                    anchor = after
                    last_direction = None
                elif direction != last_direction:
                    router.path(net, LAYERS[before[2]].split(".")[0], xy(anchor), xy(before), width=width)
                    anchor = before
                    last_direction = direction
            router.path(net, LAYERS[path[-1][2]].split(".")[0], xy(anchor), xy(path[-1]), target, width=width)
            connected.append(target)
        print(f"E19 routed {net}", flush=True)
