"""E23 input-board grid routing aid; native KiCad DRC remains authoritative."""

import heapq
import itertools
import math

import numpy as np

STEP = 0.125
LAYERS = ("In2.Cu", "B.Cu", "F.Cu")


def connect(router, tasks, size, escape=False):
    nx, ny = int(size[0] / STEP) + 1, int(size[1] / STEP) + 1

    def point(xy):
        return (round(xy[0] / STEP), round(xy[1] / STEP))

    def xy(node):
        return (node[0] * STEP, node[1] * STEP)

    def masks(net, extra, layers):
        blocks = np.zeros((len(layers), nx, ny), dtype=bool)
        edge_cells = math.ceil((0.5 + extra + 0.01) / STEP)
        blocks[:, :edge_cells, :] = True
        blocks[:, -edge_cells:, :] = True
        blocks[:, :, :edge_cells] = True
        blocks[:, :, -edge_cells:] = True
        margin = 0.15 + extra + 0.01
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
        preferred = "In2.Cu"
        roots = getattr(router, "connected_points", {}).get(net) or getattr(
            router, "initially_connected", {}
        ).get(net)
        connected = list(roots) if roots else [targets[0]]
        for target in targets if roots or escape else targets[1:]:
            if escape:
                connected = [target]
            width = getattr(router, "route_width", {}).get(net, 0.15)
            blocked = masks(net, width / 2, LAYERS)
            via_block = np.any(masks(net, 0.3, LAYERS), axis=0)
            # Same-net copper may overlap, but drills need .25mm spacing.
            # Foreign vias retain a routing lane between them. Without this
            # reserve, a legal but dense via fence can trap another endpoint
            # on every signal layer before its global branch is reached.
            for other, at in router.vias:
                gap = 0.56 if other == net else (1.1 if escape else 0.8)
                ix0, ix1 = (
                    max(0, math.floor((at[0] - gap) / STEP)),
                    min(nx, math.ceil((at[0] + gap) / STEP) + 1),
                )
                iy0, iy1 = (
                    max(0, math.floor((at[1] - gap) / STEP)),
                    min(ny, math.ceil((at[1] + gap) / STEP) + 1),
                )
                vx = np.arange(ix0, ix1)[:, None] * STEP
                vy = np.arange(iy0, iy1)[None, :] * STEP
                via_block[ix0:ix1, iy0:iy1] |= (vx - at[0]) ** 2 + (vy - at[1]) ** 2 < gap**2
            if escape:
                # Keep drill holes out of the original solder lands, including
                # same-net lands. These are conventional tented escape vias,
                # not a filled/capped via-in-pad manufacturing assumption.
                for shape in router.geometry:
                    if shape["net"] != net or not shape.get("is_pad"):
                        continue
                    rx, ry = shape["w"] / 2 + 0.35, shape["h"] / 2 + 0.35
                    ix0, ix1 = (
                        max(0, math.floor((shape["x"] - rx) / STEP)),
                        min(nx, math.ceil((shape["x"] + rx) / STEP) + 1),
                    )
                    iy0, iy1 = (
                        max(0, math.floor((shape["y"] - ry) / STEP)),
                        min(ny, math.ceil((shape["y"] + ry) / STEP) + 1),
                    )
                    via_block[ix0:ix1, iy0:iy1] = True
            end2 = point(target)
            allowed_end = getattr(router, "endpoint_layers", {}).get((net, target), LAYERS)
            starts = {}
            for start in connected:
                start2 = point(start)
                allowed_start = getattr(router, "endpoint_layers", {}).get((net, start), LAYERS)
                for layer in range(len(LAYERS)):
                    if LAYERS[layer] in allowed_start and not blocked[layer, *start2]:
                        starts[(*start2, layer)] = start
            goals = {
                (*end2, layer)
                for layer in range(len(LAYERS))
                if LAYERS[layer] in allowed_end and not blocked[layer, *end2]
            }
            assert starts and goals, (net, "blocked endpoint", target)
            serial = itertools.count()
            queue = []
            cost = {s: 0 for s in starts}
            prev = {}

            def h(n):
                return 0 if escape else abs(n[0] - end2[0]) + abs(n[1] - end2[1])

            for node in starts:
                heapq.heappush(queue, (h(node), next(serial), node))
            visited = set()
            found = None
            while queue:
                _, _, node = heapq.heappop(queue)
                if node in visited:
                    continue
                visited.add(node)
                if (escape and not via_block[node[0], node[1]]) or (not escape and node in goals):
                    found = node
                    break
                x, y, z = node
                neighbors = [
                    (x + dx, y + dy, z, 1 if escape or LAYERS[z] == preferred else 1.3)
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
            if escape:
                source = target
                target = xy(found)
            router.path(net, LAYERS[path[0][2]].split(".")[0], starts[path[0]], xy(path[0]), width=width)
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
            if escape:
                router.via(net, target)
                if not hasattr(router, "escape_points"):
                    router.escape_points = {}
                router.escape_points[(net, source)] = target
        if not escape:
            if not hasattr(router, "connected_points"):
                router.connected_points = {}
            router.connected_points[net] = connected
            print(f"E23 routed {net}", flush=True)
