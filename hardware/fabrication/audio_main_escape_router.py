"""Bounded conventional-via fanouts using exact pad and existing copper shapes."""

import math

from shapely.geometry import LineString, Point
from shapely.strtree import STRtree

from hardware.electronics.common.sexpr import children, first
from hardware.fabrication.audio_main_local_routes import best_path
from hardware.fabrication.route_nf_surface import Screen, candidate_paths, shape


class EscapeScreen:
    def __init__(self, board, captured):
        self.captured = captured
        self.screen = Screen(captured)
        self.nets = {str(n[1]): str(n[2]) for n in children(board, "net")}
        self.pads = {(p["ref"], p["pin"]): p for p in captured["objects"] if p["pin"]}
        self.copper = [(p["net"], shape(ps), p) for p in captured["objects"]
                       for layer, ps in p["layers"].items() if layer in ("F.Cu", "B.Cu") and ps]
        self.copper_index = STRtree([g for _, g, _ in self.copper])
        self.existing_vias = []
        for segment in children(board, "segment"):
            points = [list(map(float, first(segment, key)[1:3])) for key in ("start", "end")]
            self.screen.added.append((self.nets[str(first(segment, "net")[1])], first(segment, "layer")[1], LineString(points)))
        for via in children(board, "via"):
            xy = list(map(float, first(via, "at")[1:3]))
            net = self.nets[str(first(via, "net")[1])]
            self.existing_vias.append(xy)
            for layer in ("F.Cu", "B.Cu"):
                self.screen.added.append((net, layer, Point(xy).buffer(.2)))

    def via_ok(self, xy, net):
        point = Point(xy)
        if not self.screen.outline.buffer(-.2).covers(point):
            return False
        for index in self.copper_index.query(point.buffer(.52)):
            other, copper, pad = self.copper[int(index)]
            distance = point.distance(copper)
            if (other != net and distance < .511) or (not any(pad["drill_mm"]) and distance < .301):
                return False
        if any(any(p["drill_mm"]) and math.dist(xy, p["position_mm"]) < .15 + max(p["drill_mm"]) / 2 + .261
               for p in self.captured["objects"]):
            return False
        if any(point.distance(g) < .611 for other, _, g in self.screen.added if other != net):
            return False
        if any(math.dist(xy, q) < .811 for q in self.existing_vias):
            return False
        return not any(point.distance(shape(z["polygons"])) < .31 for z in self.captured["zones"] if z["keepout"])

    def fanouts(self, pad, layer, limit=2.5):
        start = tuple(pad["position_mm"])
        x, y = start
        left, top, right, bottom = shape(pad["layers"][layer]).bounds
        sites = set()
        for offset in (0, .25, -.25, .5, -.5, .75, -.75, 1., -1., 1.25, -1.25):
            for gap in (.32, .57, .82, 1.07, 1.32):
                sites.update(((left-gap, y+offset), (right+gap, y+offset),
                              (x+offset, top-gap), (x+offset, bottom+gap)))
        accepted = []
        for xy in sites:
            if math.dist(start, xy) > limit or not self.via_ok(xy, pad["net"]):
                continue
            choices = []
            for path in candidate_paths(start, xy):
                path = [p for i, p in enumerate(path) if not i or p != path[i-1]]
                length = sum(math.dist(p, q) for p, q in zip(path, path[1:]))
                if length <= limit and self.screen.legal(pad["net"], layer, path):
                    choices.append((length, path))
            if choices:
                length, path = min(choices, key=lambda p: p[0])
                accepted.append((length, xy, path))
        return sorted(accepted, key=lambda p: p[0])[:80]

    def route(self, row, use_grid=False):
        if use_grid:
            direct = best_path(self.screen, self.pads, row)
        else:
            p, q = self.pads[(row["ref"], row["pin"])], self.pads[(row["owner"], row["owner_pin"])]
            choices = []
            for path in candidate_paths(p["position_mm"], q["position_mm"]):
                path = [xy for i, xy in enumerate(path) if not i or xy != path[i-1]]
                length = sum(math.dist(p, q) for p, q in zip(path, path[1:]))
                if length <= row["route_length_limit_mm"] and self.screen.legal(row["net"], row["layer"], path):
                    choices.append((length, path))
            direct = min(choices, key=lambda p: p[0]) if choices else None
        if direct:
            return dict(length=direct[0], paths=[(row["layer"], direct[1])], vias=[])
        p, q = self.pads[(row["ref"], row["pin"])], self.pads[(row["owner"], row["owner_pin"])]
        left, right = self.fanouts(p, row["layer"]), self.fanouts(q, row["layer"])
        other = "B.Cu" if row["layer"] == "F.Cu" else "F.Cu"
        candidates = sorted((a[0]+b[0]+math.dist(a[1], b[1]), i, j)
                            for i, a in enumerate(left) for j, b in enumerate(right))
        print(row["ref"], "legal fanouts", len(left), len(right), "bounded pairs", len(candidates), flush=True)
        for lower, i, j in candidates:
            if lower > row["route_length_limit_mm"]:
                break
            a, b = left[i], right[j]
            if math.dist(a[1], b[1]) < .811:
                continue
            for middle in candidate_paths(a[1], b[1]):
                middle = [p for k, p in enumerate(middle) if not k or p != middle[k-1]]
                length = a[0]+b[0]+sum(math.dist(p, q) for p, q in zip(middle, middle[1:]))
                if length <= row["route_length_limit_mm"] and self.screen.legal(row["net"], other, middle):
                    return dict(length=length, paths=[(row["layer"], a[2]), (other, middle),
                                                    (row["layer"], list(reversed(b[2])))], vias=[a[1], b[1]])
        return None

