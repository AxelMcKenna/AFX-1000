"""Rectangle/fastener-aware E10 routing aid; native KiCad is authoritative."""

import math

import numpy as np

from ...common.sexpr import children, first
from ...output_stage.check_placement import transform
from ...rail_disconnect.routing.router import STEP, Router
from .generate import MOUNTS, SIZE


class InputRouter(Router):
    def __init__(self, board):
        super().__init__(board)
        self.nx, self.ny = round(SIZE[0] / STEP) + 1, round(SIZE[1] / STEP) + 1
        self.xx = np.arange(self.nx)[:, None] * STEP
        self.yy = np.arange(self.ny)[None, :] * STEP
        self.holes = []
        for fp in children(board, "footprint"):
            for pad in children(fp, "pad"):
                if children(pad, "drill"):
                    drill = first(pad, "drill")
                    diameter = max(float(v) for v in drill[1:] if str(v) != "oval")
                    xy = tuple(v - 100 for v in transform(fp, first(pad, "at")[1:3]))
                    self.holes.append((xy, diameter))

    def masks(self, net, width):
        blocks = np.zeros((6, self.nx, self.ny), dtype=bool)
        edge = 0.5 + width / 2 + 0.03
        border = (self.xx < edge) | (self.xx > SIZE[0] - edge) | (self.yy < edge) | (self.yy > SIZE[1] - edge)
        blocks[:] = border
        via_block = (
            (self.xx < 0.83) | (self.xx > SIZE[0] - 0.83) | (self.yy < 0.83) | (self.yy > SIZE[1] - 0.83)
        )
        for x, y in MOUNTS:
            blocks |= (self.xx - x) ** 2 + (self.yy - y) ** 2 < (3.7 + width / 2 + 0.03) ** 2
            via_block |= (self.xx - x) ** 2 + (self.yy - y) ** 2 < (4.03) ** 2
        for shape in self.geometry:
            same = shape["net"] == net
            for extra, destination in ((0.25 + width / 2 + 0.03, blocks), (0.58, via_block)):
                if same and (destination is blocks or shape["kind"] == "line" or shape.get("through")):
                    continue
                if same and destination is via_block:
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
                if destination is blocks:
                    for layer in shape["layers"]:
                        blocks[layer, ix0:ix1, iy0:iy1] |= hit
                else:
                    via_block[ix0:ix1, iy0:iy1] |= hit
        for xy, diameter in self.holes:
            via_block |= (self.xx - xy[0]) ** 2 + (self.yy - xy[1]) ** 2 < (diameter / 2 + 0.15 + 0.26) ** 2
        for shape in self.geometry:
            if shape["kind"] == "via" and shape["net"] == net:
                ix, iy = (round(v / STEP) for v in shape["xy"])
                if math.dist((ix * STEP, iy * STEP), shape["xy"]) < 1e-7:
                    via_block[ix, iy] = False
        return blocks, via_block

    def local_paths(self):
        def p(ref, number):
            return next(p["xy"] for p in self.by_ref[ref] if p["pin"] == str(number))

        self.path("GAIN_FB_L", 0, [p("R5", 1), (30.2, 17.365), p("U1", 2)], 0.25)
        self.path("GAIN_FB_L", 0, [p("R6", 1), (30.2, 20.2), (30.2, 17.365)], 0.25)
        self.path("BUF_OUT_L", 0, [p("U1", 1), (27.5375, 16.095), p("R5", 2)], 0.25)
        self.path("GAIN_FB_R", 0, [p("R12", 1), (40, 18.635), p("U1", 6)], 0.25)
        self.path("GAIN_FB_R", 0, [p("R13", 1), (40, 20.5), (40, 18.635)], 0.25)
        self.path(
            "BUF_OUT_R",
            0,
            [p("U1", 7), (39.9, 17.365), (39.9, 15.1), (44.2, 15.1), (44.2, 17.365), p("R12", 2)],
            0.25,
        )

        # Reserve conventional ground escapes before global routes can fence
        # these surface lands in. Their drilled holes remain outside SMD pads.
        for ref, xy in [("R13", (45, 20.5)), ("C4", (47, 23.5)), ("C8", (51, 17))]:
            pad = next(p for p in self.by_ref[ref] if p["pin"] == "2")
            self.path("AGND", 0, [pad["xy"], xy], 0.4)
            self.via("AGND", xy)

    def route_all(self):
        self.local_paths()
        super().route_all()
        target = next(p for p in self.by_ref["J3"] if p["pin"] == "2")
        for ref, xy in [("R13", (45, 20.5)), ("C4", (47, 23.5)), ("C8", (51, 17))]:
            # Require an inner-layer connection as well as the F.Cu escape.
            # A via left connected on only its surface layer is not accepted.
            escaped = dict(net="AGND", xy=xy, layers=(1,))
            if not self.connect(escaped, target, 0.4):
                self.failed.append(dict(net="AGND", source=[ref, "2", xy], target=["J3", "2", target["xy"]]))
