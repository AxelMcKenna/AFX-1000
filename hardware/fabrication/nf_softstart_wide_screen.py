"""Wider bounded search around the U23 cell; electrical rules stay unchanged."""
import math
import time
import heapq
import itertools
from hardware.fabrication.nf_softstart_joint_screen import ExistingViaScreen

class WideScreen(ExistingViaScreen):
    def route(self, net, start_layer, start, end_layer, end, deadline, budget=45000):
        step = .1
        origin = (self.signal_layers.index(start_layer), *(round(v/step) for v in start))
        goal = (self.signal_layers.index(end_layer), *(round(v/step) for v in end))

        def xy(key):
            return tuple(round(v*step, 6) for v in key[1:])

        for layer, point, key in ((start_layer, start, origin), (end_layer, end, goal)):
            if math.dist(point, xy(key)) > 1e-6 and not self.legal(net, layer, [point, xy(key)]):
                return None
        lower = tuple(min(u, v)-100 for u, v in zip(origin[1:], goal[1:]))
        upper = tuple(max(u, v)+100 for u, v in zip(origin[1:], goal[1:]))

        def heuristic(key):
            return math.dist(key[1:], goal[1:])+(25 if key[0] != goal[0] else 0)

        queue = [(heuristic(origin), 0., origin)]
        cost, parent, valid, via_valid = {origin: 0.}, {}, {}, {}
        visits = 0
        while queue and visits < budget:
            if visits % 128 == 0 and time.monotonic() >= deadline:
                return None
            _, distance, key = heapq.heappop(queue)
            if distance > cost[key]+1e-9:
                continue
            visits += 1
            if key == goal:
                keys = [key]
                while key in parent:
                    key = parent[key]
                    keys.append(key)
                keys.reverse()
                path = [(self.signal_layers[origin[0]], tuple(start))]
                path += [(self.signal_layers[k[0]], xy(k)) for k in keys]
                path.append((end_layer, tuple(end)))
                return [p for i, p in enumerate(path) if i == 0 or p != path[i-1]]
            neighbors = [(key[0], key[1]+dx, key[2]+dy) for dx, dy in itertools.product((-1, 0, 1), repeat=2) if dx or dy]
            position = key[1:]
            if position not in via_valid:
                via_valid[position] = self.via_legal(net, xy(key))
            if via_valid[position]:
                neighbors += [(i, *position) for i in range(len(self.signal_layers)) if i != key[0]]
            for neighbor in neighbors:
                if not all(lo <= v <= hi for lo, v, hi in zip(lower, neighbor[1:], upper)):
                    continue
                hop = neighbor[0] != key[0]
                candidate = distance+(25 if hop else math.dist(key[1:], neighbor[1:]))
                if candidate >= cost.get(neighbor, math.inf)-1e-9:
                    continue
                if not hop:
                    edge = tuple(sorted((key, neighbor)))
                    if edge not in valid:
                        valid[edge] = self.legal(net, self.signal_layers[key[0]], [xy(key), xy(neighbor)])
                    if not valid[edge]:
                        continue
                cost[neighbor], parent[neighbor] = candidate, key
                heapq.heappush(queue, (candidate+heuristic(neighbor), candidate, neighbor))
        return None

