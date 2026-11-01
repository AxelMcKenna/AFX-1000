"""Reserve conventional escapes before global routing in the new E26 variant."""

import math

from ...common.placement import placed_footprint
from ...common.sexpr import children, first
from ...output_stage.check_placement import courtyard
from ..routing.check import point_segment, segment_distance
from .router import Router

MOUNTS = ((4, 20), (152, 3.8), (10, 36), (100, 36))
MOVES = {
    "Q9": (37, 7, 180, "F"),
    "Q10": (46, 7, 0, "F"),
    "U5": (41.5, 13.8, 0, "F"),
    "U7": (20, 37, 0, "F"),
    "U8": (43.5, 25.5, 0, "F"),
    "U9": (13, 25.5, 0, "F"),
    "U11": (11.5, 14, 0, "F"),
    "U12": (43.5, 33, 0, "F"),
    "J5": (13, 41.5, 90, "F"),
}
BULK = {"C4", "C8", "C12", "C16", "C20", "C24"}
DRIVERS = {
    "U1": ("C1", "C2", "C3"),
    "U2": ("C5", "C6", "C7"),
    "U3": ("C9", "C10", "C11"),
    "U4": ("C13", "C14", "C15"),
    "U5": ("C17", "C18", "C19"),
    "U6": ("C21", "C22", "C23"),
}
POWER_NETS = {
    "P19_SRC",
    "P19",
    "N19_SRC",
    "N19",
    "P12_SRC",
    "P12",
    "N12_SRC",
    "N12",
    "V5_REG_SRC",
    "V5_REG",
    "5V_DIG_SRC",
    "5V_DIG",
}


def rect_distance(point, g):
    dx = max(abs(point[0] - g["xy"][0]) - g["size"][0] / 2, 0)
    dy = max(abs(point[1] - g["xy"][1]) - g["size"][1] / 2, 0)
    return math.hypot(dx, dy)


class Layout:
    def __init__(self, board, parts, pins, library):
        self.board = board
        self.parts = parts
        self.pins = pins
        self.library = library
        self.nets = {str(n[2]).lstrip("/"): int(n[1]) for n in children(board, "net")}
        self.router = None
        self.bodies = []
        self.ports = []
        self.placements = {}
        self.local_paths = []

    def footprint(self, ref, pose):
        c = self.parts[ref]
        lib, name = c["footprint"].split(":")
        p = self.library / (lib + ".pretty") / (name + ".kicad_mod")
        return placed_footprint(
            dict(c, value=c["part"], mpn=c["part"], nets=self.pins[ref]),
            pose,
            p,
            self.nets,
            namespace="rmx:E26:",
        )

    def body(self, fp):
        face = str(first(fp, "layer")[1]).split(".")[0]
        return face, courtyard(fp, face + ".CrtYd")

    def legal_body(self, ref, fp):
        face, b = self.body(fp)
        if not (
            0.5 <= b[0] - 100 < b[2] - 100 <= 155.5
            and 0.5 <= b[1] - 100 < b[3] - 100 <= (45.25 if ref == "C24" else 44.75)
        ):
            return False
        x0, y0, x1, y1 = (v - 100 for v in b)
        if x0 < 5.25 and y1 > 34.75:
            return False
        if x1 > 153.75 and y1 > 35.25 and ref != "C24":
            return False
        for x, y in MOUNTS:
            if math.hypot(max(x0 - x, 0, x - x1), max(y0 - y, 0, y - y1)) < 3.7:
                return False
        for _, side, c in self.bodies:
            if (
                side == face
                and min(b[2], c[2]) - max(b[0], c[0]) > -0.1
                and min(b[3], c[3]) - max(b[1], c[1]) > -0.1
            ):
                return False
        if self.router is not None:
            trial = Router([n for n in self.board if isinstance(n, list) and n and n[0] == "net"] + [fp])
            for pad in trial.by_ref[ref]:
                for g in self.router.geometry:
                    if not set(pad["layers"]) & set(g["layers"]):
                        continue
                    if g["kind"] == "via":
                        need = 0.41 if g["net"] == pad["net"] else g["radius"] + 0.22
                        if rect_distance(g["xy"], pad) < need:
                            return False
                    elif g["kind"] == "line" and g["net"] != pad["net"]:
                        x, y = pad["xy"]
                        w, h = pad["size"]
                        corners = [
                            (x - w / 2, y - h / 2),
                            (x + w / 2, y - h / 2),
                            (x + w / 2, y + h / 2),
                            (x - w / 2, y + h / 2),
                        ]
                        if any(
                            abs(p[0] - x) <= w / 2 and abs(p[1] - y) <= h / 2 for p in (g["start"], g["end"])
                        ):
                            return False
                        if (
                            min(
                                segment_distance(g["start"], g["end"], a, b)
                                for a, b in zip(corners, corners[1:] + corners[:1])
                            )
                            < g["width"] / 2 + 0.22
                        ):
                            return False
        if face == "B":
            for p in self.router.pads:
                if p["through"]:
                    x, y = p["xy"]
                    if min(x1, x + 1.4) - max(x0, x - 1.4) > 0 and min(y1, y + 1.4) - max(y0, y - 1.4) > 0:
                        return False
        return True

    def add_body(self, ref, fp, pose):
        assert self.legal_body(ref, fp), (ref, "courtyard/body placement", self.body(fp))
        self.board.append(fp)
        face, b = self.body(fp)
        self.bodies.append((ref, face, b))
        self.placements[ref] = pose

    def refresh(self):
        self.router = Router(self.board)
        self.router.load_existing_copper()
        # Fastener-head reserves are deliberately more conservative than NPTH DRC.
        for x, y in MOUNTS:
            self.router.geometry.append(
                dict(kind="via", xy=(x, y), radius=3.2, net="HEAD_KEEPOUT", layers=tuple(range(6)))
            )

        sizes = {"C4": 16.5, "C8": 16.5, "C12": 8.5, "C16": 8.5, "C20": 10.5, "C24": 16.5}
        for ref, diameter in sizes.items():
            if ref not in self.router.by_ref:
                continue
            pads = self.router.by_ref[ref]
            center = tuple(sum(p["xy"][i] for p in pads) / len(pads) for i in (0, 1))
            self.router.geometry.append(
                dict(kind="via", xy=center, radius=diameter / 2, net="BULK_BODY_NOVIA", layers=())
            )

    def free_via(self, net, point):
        if not (0.8 < point[0] < 155.2 and 0.8 < point[1] < 44.45):
            return False
        if point[0] < 5.8 and point[1] > 34.2:
            return False
        if point[0] > 153.7 and point[1] > 34.5:
            return False
        for g in self.router.geometry:
            if g["kind"] == "rect":
                need = 0.41 if g["net"] == net else 0.51
                if rect_distance(point, g) < need - 1e-7:
                    return False
                if g.get("through") and abs(point[0] - g["xy"][0]) < 1.7 and abs(point[1] - g["xy"][1]) < 1.7:
                    return False
            elif g["kind"] == "line":
                if (
                    g["net"] != net
                    and point_segment(point, g["start"], g["end"]) < g["width"] / 2 + 0.51 - 1e-7
                ):
                    return False
            else:
                if math.dist(point, g["xy"]) < g["radius"] + (0.26 if g["net"] == net else 0.51) - 1e-7:
                    return False
        return True

    def free_line(self, net, layer, a, b, width=0.2):
        for g in self.router.geometry:
            if g["net"] == net or layer not in g["layers"]:
                continue
            radius = width / 2 + 0.21
            if g["kind"] == "rect":
                x, y = g["xy"]
                w, h = g["size"]
                x0, x1 = x - w / 2, x + w / 2
                y0, y1 = y - h / 2, y + h / 2
                if x0 <= a[0] <= x1 and y0 <= a[1] <= y1:
                    return False
                if x0 <= b[0] <= x1 and y0 <= b[1] <= y1:
                    return False
                corners = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
                if (
                    min(segment_distance(a, b, c, d) for c, d in zip(corners, corners[1:] + corners[:1]))
                    < radius - 1e-7
                ):
                    return False
            elif g["kind"] == "line":
                if segment_distance(a, b, g["start"], g["end"]) < radius + g["width"] / 2 - 1e-7:
                    return False
            elif point_segment(g["xy"], a, b) < radius + g["radius"] - 1e-7:
                return False
        return True

    def pad(self, ref, number):
        return next(p for p in self.router.by_ref[ref] if p["pin"] == str(number))

    def port(self, p, via, path=None, width=0.2):
        path = path or [p["xy"], via]
        layer = p["layers"][0]
        assert self.free_via(p["net"], via), (p["ref"], p["pin"], "via blocked", via)
        assert all(self.free_line(p["net"], layer, a, b, width) for a, b in zip(path, path[1:])), (
            p["ref"],
            p["pin"],
            "escape trace blocked",
            path,
        )
        self.router.path(p["net"], layer, path, width)
        self.router.via(p["net"], via)
        self.ports.append(
            dict(
                ref=p["ref"],
                pin=p["pin"],
                net=p["net"],
                xy=via,
                layers=tuple(range(6)),
                purpose="pre-reserved conventional escape",
            )
        )

    def local(self, net, layer, points, width=0.25):
        assert all(self.free_line(net, layer, a, b, width) for a, b in zip(points, points[1:])), (
            "local trace blocked",
            net,
            points,
        )
        self.router.path(net, layer, points, width)
        self.local_paths.append(dict(net=net, layer=layer, points=points, width_mm=width))
