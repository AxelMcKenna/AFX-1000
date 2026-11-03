"""Enumerate bounded pin exits densely while retaining exact copper and drill screens."""

import math

from shapely.geometry import LineString

from hardware.fabrication.audio_main_global_controls import LAYERS
from hardware.fabrication.route_nf_surface import candidate_paths


def choices(screen, pad, group, limit=128):
    start = pad["position_mm"]
    net = pad["net"]
    face = next(layer for layer in ("F.Cu", "B.Cu") if pad["layers"].get(layer))
    x, y = start
    points = [(i/10, j/10) for i in range(math.floor((x-3.5)*10), math.ceil((x+3.5)*10)+1)
              for j in range(math.floor((y-3.5)*10), math.ceil((y+3.5)*10)+1)
              if math.dist(start, (i/10, j/10)) <= 3.5]
    result = []
    for point in sorted(points, key=lambda p: (math.dist(start, p), p)):
        if not screen.via_legal(net, point):
            continue
        best = None
        for path in candidate_paths(start, point):
            path = [p for i, p in enumerate(path) if not i or p != path[i-1]]
            length = LineString(path).length
            if length > 3.5 or (best and length >= best[0]):
                continue
            if screen.legal(net, face, path):
                best = length, path
                if abs(length-math.dist(start, point)) < 1e-8:
                    break
        if best:
            length, path = best
            result.append(dict(point=point, layers=list(LAYERS), runs=[(face, path)], vias=[point],
                               cost=length+2.5, group=group, pad=[pad["ref"], pad["pin"]]))
        if len(result) >= limit:
            break
    return result
