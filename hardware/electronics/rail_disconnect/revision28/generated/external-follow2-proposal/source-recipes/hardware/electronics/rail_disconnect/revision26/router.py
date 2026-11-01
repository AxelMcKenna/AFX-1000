"""Six-layer conservative routing aid. Native KiCad checks remain authoritative."""

import heapq
import itertools
import math
from collections import defaultdict

import numpy as np

from ...common.sexpr import children, first, read_sexpr
from ...output_stage.check_placement import transform

LAYERS = ("F.Cu", "In1.Cu", "In2.Cu", "In3.Cu", "In4.Cu", "B.Cu")
STEP = 0.25
CLEARANCE = 0.22


class Router:
    def __init__(self, board):
        self.board = board
        self.nets = {str(n[2]).lstrip("/"): int(n[1]) for n in children(board, "net")}
        self.pads = []
        self.geometry = []
        self.by_ref = defaultdict(list)
        self.routes = []
        self.failed = []
        for fp in children(board, "footprint"):
            ref = next(p[2] for p in children(fp, "property") if p[1] == "Reference")
            angle = float(first(fp, "at")[3]) if len(first(fp, "at")) > 3 else 0
            for pad in children(fp, "pad"):
                if not children(pad, "size"):
                    continue
                point = tuple(round(v - 100, 6) for v in transform(fp, first(pad, "at")[1:3]))
                size = tuple(map(float, first(pad, "size")[1:3]))
                if int(angle) % 180:
                    size = size[::-1]
                raw_layers = list(map(str, first(pad, "layers")[1:]))
                layers = (
                    tuple(range(6))
                    if "*.Cu" in raw_layers
                    else tuple(i for i, l in enumerate(LAYERS) if l in raw_layers)
                )
                net = str(first(pad, "net")[-1]).lstrip("/") if children(pad, "net") else "HOLE_" + ref
                item = dict(
                    kind="rect",
                    xy=point,
                    size=size,
                    net=net,
                    layers=layers,
                    ref=ref,
                    pin=str(pad[1]),
                    through=pad[2] == "thru_hole",
                )
                self.geometry.append(item)
                self.by_ref[ref].append(item)
                if children(pad, "net"):
                    self.pads.append(item)
        self.nx, self.ny = round(156 / STEP) + 1, math.floor(45.25 / STEP) + 1
        self.xx = np.arange(self.nx)[:, None] * STEP
        self.yy = np.arange(self.ny)[None, :] * STEP

    def load_existing_copper(self):
        names = {str(n[1]): str(n[2]).lstrip("/") for n in children(self.board, "net")}
        for segment in children(self.board, "segment"):
            self.geometry.append(
                dict(
                    kind="line",
                    net=names[str(first(segment, "net")[1])],
                    layers=(LAYERS.index(str(first(segment, "layer")[1])),),
                    start=tuple(float(v) - 100 for v in first(segment, "start")[1:3]),
                    end=tuple(float(v) - 100 for v in first(segment, "end")[1:3]),
                    width=float(first(segment, "width")[1]),
                )
            )
        for via in children(self.board, "via"):
            self.geometry.append(
                dict(
                    kind="via",
                    net=names[str(first(via, "net")[1])],
                    layers=tuple(range(6)),
                    radius=float(first(via, "size")[1]) / 2,
                    xy=tuple(float(v) - 100 for v in first(via, "at")[1:3]),
                )
            )

    def path(self, net, layer, points, width):
        points = [tuple(round(float(v), 6) for v in point) for point in points]
        self.routes.append(dict(net=net, layer=LAYERS[layer], width_mm=width, points_relative_mm=points))
        for start, end in zip(points, points[1:]):
            if start == end:
                continue
            self.board.append(
                read_sexpr(
                    f'(segment (start {100 + start[0]} {100 + start[1]}) (end {100 + end[0]} {100 + end[1]}) (width {width}) (layer "{LAYERS[layer]}") (net {self.nets[net]}))'
                )
            )
            self.geometry.append(
                dict(kind="line", start=start, end=end, width=width, net=net, layers=(layer,))
            )

    def via(self, net, point):
        if any(
            g.get("through")
            and g["net"] == net
            and all(abs(point[i] - g["xy"][i]) <= g["size"][i] / 2 for i in (0, 1))
            for g in self.geometry
        ):
            # The existing plated through-hole already joins all copper layers;
            # a coincident extra drill is both unnecessary and invalid.
            return
        if any(
            g["kind"] == "via" and g["net"] == net and math.dist(g["xy"], point) < 1e-6 for g in self.geometry
        ):
            return
        self.board.append(
            read_sexpr(
                f'(via (at {100 + point[0]} {100 + point[1]}) (size .6) (drill .3) (layers "F.Cu" "B.Cu") (net {self.nets[net]}))'
            )
        )
        self.geometry.append(dict(kind="via", xy=point, radius=0.3, net=net, layers=tuple(range(6))))

    def masks(self, net, width):
        blocked = np.zeros((6, self.nx, self.ny), dtype=bool)
        border = (self.xx < 0.75) | (self.xx > 155.25) | (self.yy < 0.75) | (self.yy > 44.5)
        border |= (self.xx < 5.75) & (self.yy > 34.25)
        border |= (self.xx > 153.75) & (self.yy > 34.5)
        blocked[:] = border
        via_block = np.array(border, copy=True)
        for shape in self.geometry:
            same = shape["net"] == net
            # Conventional vias stay clear of SMD lands of their own net too;
            # no via-in-pad/capped process is assumed.
            for extra, destination in (
                (CLEARANCE + width / 2 + 0.02, blocked),
                (CLEARANCE + 0.3 + 0.02, via_block),
            ):
                if same and (destination is blocked or shape["kind"] == "line" or shape.get("through")):
                    continue
                if same and destination is via_block:
                    # A conventional 0.3mm drill stays >=0.26mm from its own
                    # SMD land and other same-net drill edges. Same-net copper
                    # needs no electrical-clearance separation.
                    extra = 0.41 if shape["kind"] == "rect" else 0.26
                if shape["kind"] == "line":
                    a, b = shape["start"], shape["end"]
                    radius = shape["width"] / 2 + extra
                    x0, x1 = min(a[0], b[0]) - radius, max(a[0], b[0]) + radius
                    y0, y1 = min(a[1], b[1]) - radius, max(a[1], b[1]) + radius
                else:
                    wx, wy = (
                        (v / 2 for v in shape["size"])
                        if shape["kind"] == "rect"
                        else (shape["radius"], shape["radius"])
                    )
                    x0, x1 = shape["xy"][0] - wx - extra, shape["xy"][0] + wx + extra
                    y0, y1 = shape["xy"][1] - wy - extra, shape["xy"][1] + wy + extra
                ix0, ix1 = max(0, math.floor(x0 / STEP)), min(self.nx, math.ceil(x1 / STEP) + 1)
                iy0, iy1 = max(0, math.floor(y0 / STEP)), min(self.ny, math.ceil(y1 / STEP) + 1)
                x, y = self.xx[ix0:ix1], self.yy[:, iy0:iy1]
                if shape["kind"] == "line":
                    dx, dy = b[0] - a[0], b[1] - a[1]
                    t = np.clip(((x - a[0]) * dx + (y - a[1]) * dy) / (dx * dx + dy * dy), 0, 1)
                    hit = (x - a[0] - t * dx) ** 2 + (y - a[1] - t * dy) ** 2 <= radius * radius
                elif shape["kind"] == "via":
                    hit = (x - shape["xy"][0]) ** 2 + (y - shape["xy"][1]) ** 2 <= (
                        shape["radius"] + extra
                    ) ** 2
                else:
                    hit = (x >= x0) & (x <= x1) & (y >= y0) & (y <= y1)
                if destination is blocked:
                    for layer in shape["layers"]:
                        blocked[layer, ix0:ix1, iy0:iy1] |= hit
                else:
                    via_block[ix0:ix1, iy0:iy1] |= hit
        for shape in self.geometry:
            if shape["kind"] == "via" and shape["net"] == net:
                ix, iy = (round(v / STEP) for v in shape["xy"])
                if math.dist((ix * STEP, iy * STEP), shape["xy"]) < 1e-7:
                    via_block[ix, iy] = False
        return blocked, via_block

    def connect(self, source, target, width):
        net = source["net"]
        blocked, via_block = self.masks(net, width)
        start_xy = tuple(round(v / STEP) for v in source["xy"])
        end_xy = tuple(round(v / STEP) for v in target["xy"])
        starts = [(*start_xy, z) for z in source["layers"] if not blocked[z, start_xy[0], start_xy[1]]]
        goals = {(*end_xy, z) for z in target["layers"] if not blocked[z, end_xy[0], end_xy[1]]}
        if not starts or not goals:
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
                return False
            if point in goals:
                found = point
                break
            x, y, z = point
            neighbors = [
                (x + dx, y + dy, z, 1)
                for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1))
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
            return False
        nodes = [found]
        while nodes[-1] in previous:
            nodes.append(previous[nodes[-1]])
        nodes.reverse()
        anchor = nodes[0]
        points = [source["xy"], (anchor[0] * STEP, anchor[1] * STEP)]
        direction = None
        for before, after in zip(nodes, nodes[1:]):
            delta = (after[0] - before[0], after[1] - before[1], after[2] - before[2])
            if delta[2]:
                point = (before[0] * STEP, before[1] * STEP)
                points.append(point)
                self.path(net, before[2], points, width)
                self.via(net, point)
                points = [point]
                direction = None
            elif direction != delta:
                points.append((before[0] * STEP, before[1] * STEP))
                direction = delta
        points.extend([(nodes[-1][0] * STEP, nodes[-1][1] * STEP), target["xy"]])
        self.path(net, nodes[-1][2], points, width)
        return True

    def route_all(self):
        groups = defaultdict(list)
        for pad in self.pads:
            if not pad["net"].startswith("unconnected-"):
                groups[pad["net"]].append(pad)
        ordered = sorted(
            groups, key=lambda n: (n in ("AGND", "V2V5_AUX", "ALL_RAILS_ALLOW"), -n.endswith("_COMMON"), n)
        )
        for net in ordered:
            pads = groups[net]
            if len(pads) < 2:
                continue
            # The first local power bars are retained; explicit pad-to-pad tasks
            # still cover every duplicate physical VSON source/drain land.
            connected = [pads[0]]
            remaining = pads[1:]
            failed = 0
            while remaining:
                distance, i, j = min(
                    (math.dist(a["xy"], b["xy"]), i, j)
                    for i, a in enumerate(connected)
                    for j, b in enumerate(remaining)
                )
                source, target = connected[i], remaining.pop(j)
                width = 0.25
                if net in ("5V_DIG", "5V_DIG_SRC"):
                    width = 1.0
                elif net in (
                    "P19",
                    "P19_SRC",
                    "N19",
                    "N19_SRC",
                    "P12",
                    "P12_SRC",
                    "N12",
                    "N12_SRC",
                    "V5_REG",
                    "V5_REG_SRC",
                    "AGND",
                ):
                    width = 0.5
                if not self.connect(source, target, width):
                    self.failed.append(
                        dict(
                            net=net,
                            source=[source["ref"], source["pin"], source["xy"]],
                            target=[target["ref"], target["pin"], target["xy"]],
                            width_mm=width,
                        )
                    )
                    failed += 1
                connected.append(target)
            print(f"E25 route {net}: {len(pads)} lands, {failed} unresolved tasks", flush=True)
