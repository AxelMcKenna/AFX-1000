"""Conservative E12 exploratory routing with two exclusively AGND planes."""

import math
from collections import defaultdict

import numpy as np

from ...common.sexpr import children, first
from ...input_range.pcb.router import InputRouter
from ...rail_disconnect.routing.check import point_segment
from ...rail_disconnect.routing.router import STEP
from .generate import MOUNTS, SIZE


class AdcRouter(InputRouter):
    def __init__(self, board):
        super().__init__(board)
        self.nx, self.ny = round(SIZE[0] / STEP) + 1, round(SIZE[1] / STEP) + 1
        self.xx = np.arange(self.nx)[:, None] * STEP
        self.yy = np.arange(self.ny)[None, :] * STEP

    def path(self, net, layer, points, width):
        before = len(self.geometry)
        super().path(net, layer, points, width)
        for g in self.geometry[before:]:
            g["role"] = getattr(self, "role", None)

    def via(self, net, point):
        before = len(self.geometry)
        super().via(net, point)
        for g in self.geometry[before:]:
            g["role"] = getattr(self, "role", None)

    def masks(self, net, width):
        # Parent helper's obstacle mathematics, with this board's rectangular
        # dimensions supplied without changing its module globals.
        return e12_masks(self, net, width)

    def local_paths(self):
        self.escapes = {}
        self.role = None

        def p(ref, pin):
            return next(p["xy"] for p in self.by_ref[ref] if p["pin"] == str(pin))

        for ci, ch in enumerate(("L", "R")):
            dx = 50 * ci
            u = "U" + str(ci + 1)

            def r(k):
                return "R" + str(k + 16 * ci)

            def c(k):
                return "C" + str(k + 14 * ci)

            self.path(
                "FB_N_" + ch,
                0,
                [p(u, 1), (26.8 + dx, 42.025), (26 + dx, 41.5), (22 + dx, 41.5), p(c(2), 2)],
                0.25,
            )
            self.path("FB_N_" + ch, 0, [p(c(2), 2), (22 + dx, 38.5875), p(r(2), 2)], 0.25)
            self.path("FB_N_" + ch, 0, [p(r(4), 2), (22 + dx, 38.5875)], 0.25)
            self.path(
                "FB_P_" + ch,
                0,
                [p(u, 8), (33.2 + dx, 42.025), (34 + dx, 41.5), (38 + dx, 41.5), p(c(1), 2)],
                0.25,
            )
            self.path("FB_P_" + ch, 0, [p(c(1), 2), (38 + dx, 38.5875), p(r(1), 2)], 0.25)
            self.path("FB_P_" + ch, 0, [p(r(3), 2), (38 + dx, 38.5875)], 0.25)
            self.path(
                "DRV_" + ch + "P",
                0,
                [p(u, 4), (26.8 + dx, 43.975), (26 + dx, 44.5), (22 + dx, 44.5), p(c(2), 1)],
                0.25,
            )
            self.path(
                "DRV_" + ch + "P", 0, [p(c(2), 1), (20 + dx, 45.5), (19.0875 + dx, 45.5), p(r(5), 1)], 0.25
            )
            self.path(
                "DRV_" + ch + "N",
                0,
                [p(u, 5), (33.2 + dx, 43.975), (34 + dx, 44.5), (38 + dx, 44.5), p(c(1), 1)],
                0.25,
            )
            self.path(
                "DRV_" + ch + "N", 0, [p(c(1), 1), (40 + dx, 45.5), (40.9125 + dx, 45.5), p(r(6), 1)], 0.25
            )
            for pin, net, xy, mid in [
                (2, "VOCM_" + ch, (25 + dx, 42.6), (26 + dx, 42.675)),
                (3, "V5_REG", (24 + dx, 43.4), (26 + dx, 43.325)),
                (7, "PD_" + ch, (35 + dx, 42.6), (34 + dx, 42.675)),
                (6, "NBIAS_" + ch, (36 + dx, 43.4), (34 + dx, 43.325)),
            ]:
                self.path(net, 0, [p(u, pin), mid, xy], 0.25)
                self.via(net, xy)
                self.escapes[(u, str(pin))] = xy
        self.path("BUF_L", 0, [p("U3", 1), (50.8, 41.095), (50.8, 42.365), p("U3", 2)], 0.25)
        self.path("BUF_R", 0, [p("U3", 7), (59.2, 42.365), (59.2, 43.635), p("U3", 6)], 0.25)
        self.path("REF_HALF_L", 0, [p("U4", 1), (50.8, 14.19), (50.8, 15.46), p("U4", 2)], 0.25)
        self.path("REF_HALF_R", 0, [p("U4", 8), (59.2, 21.81), (59.2, 20.54), p("U4", 9)], 0.25)
        for ref, pin, xy in [
            ("U3", 8, (60, 40.5)),
            ("U3", 4, (50, 45.5)),
            ("U4", 4, (50, 18)),
            ("U4", 11, (60, 18)),
        ]:
            pad = next(p for p in self.by_ref[ref] if p["pin"] == str(pin))
            x, y = pad["xy"]
            mid = (xy[0], y)
            self.path(pad["net"], 0, [pad["xy"], mid, xy], 0.25)
            self.via(pad["net"], xy)
            self.escapes[(ref, str(pin))] = xy
        xy = (77.8, 34)
        self.path("PD_R", 0, [p("R31", 1), xy], 0.25)
        self.via("PD_R", xy)
        self.escapes[("R31", "1")] = xy
        # Charge-pump grounds reach the planes locally before signal routing.
        for ref, x in [("U5", 14), ("U6", 94)]:
            self.path("AGND", 0, [p(ref, 2), (x - 4.5, 10.675), (x - 4.5, 11.325), p(ref, 3)], 0.25)
            self.via("AGND", (x - 4.5, 11.325))
            self.path("AGND", 0, [p(ref, 5), (x + 3.5, 11.975), (x + 4.5, 12.5)], 0.25)
            self.via("AGND", (x + 4.5, 12.5))
            for pin, xy, mid in [
                (1, (x - 5, 9.6), (x - 3.5, 10.025)),
                (4, (x - 6, 12.5), (x - 3.5, 11.975)),
                (8, (x + 5, 9.6), (x + 3.5, 10.025)),
                (7, (x + 5.5, 10.6), (x + 3.5, 10.675)),
                (6, (x + 4.2, 11.4), (x + 3.5, 11.325)),
            ]:
                pad = next(p for p in self.by_ref[ref] if p["pin"] == str(pin))
                self.path(pad["net"], 0, [pad["xy"], mid, xy], 0.25)
                self.via(pad["net"], xy)
                self.escapes[(ref, str(pin))] = xy

    def header_stars(self):
        tasks = []
        # Reserve ALL ADC sense escapes before any trace can fence them in.
        self.role = "sense"
        for ci, ch in enumerate(("L", "R")):
            for polarity, offset in [("P", 0), ("N", 1)]:
                net = "ADC_" + ch + polarity
                header = next(p for p in self.by_ref["J2"] if p["pin"] == str(1 + 3 * ci + offset))
                sense = []
                for ref, pin in [
                    ("R" + str(4 + 16 * ci if polarity == "P" else 3 + 16 * ci), "1"),
                    ("R" + str(10 + 16 * ci if polarity == "P" else 11 + 16 * ci), "1"),
                ]:
                    pad = next(p for p in self.by_ref[ref] if p["pin"] == pin)
                    x, y = pad["xy"]
                    xy = (
                        (x + (-2 if x in (18, 68) else 2), y)
                        if ref in ("R3", "R4", "R19", "R20")
                        else (x, y + 2)
                    )
                    self.path(net, 0, [pad["xy"], xy], 0.25)
                    self.via(net, xy)
                    sense.append(dict(pad, xy=xy, layers=(2,)))
                force = [
                    next(p for p in self.by_ref[ref] if p["pin"] == pin)
                    for ref, pin in [
                        ("R" + str(5 + 16 * ci if polarity == "P" else 6 + 16 * ci), "2"),
                        ("C" + str(3 + 14 * ci), "1" if polarity == "P" else "2"),
                        ("C" + str(4 + 14 * ci if polarity == "P" else 5 + 14 * ci), "1"),
                    ]
                ]
                tasks.append((net, header, sense, force))
        for net, header, sense, force in tasks:
            for role, pads in [("sense", sense), ("force", force)]:
                self.role = role
                targets = [header]
                for pad in pads:
                    target = min(targets, key=lambda p: math.dist(p["xy"], pad["xy"]))
                    if not self.connect(pad, target, 0.25):
                        self.failed.append(
                            dict(net=net, role=role, source=[pad["ref"], pad["pin"]], target="J2 star")
                        )
                    targets.append(pad)
        self.role = None

    def local_grounds(self):
        for pad in self.pads:
            if pad["net"] == "AGND" and not pad["through"] and pad["ref"] not in ("U5", "U6"):
                target = dict(net="AGND", xy=pad["xy"], layers=(1, 4))
                if not self.connect(pad, target, 0.4):
                    self.failed.append(dict(net="AGND", source=[pad["ref"], pad["pin"]], target="AGND plane"))

    def route_all(self):
        self.local_paths()
        self.local_grounds()
        self.header_stars()
        groups = defaultdict(list)
        for pad in self.pads:
            if not pad["net"].startswith("unconnected-"):
                if (pad["ref"], pad["pin"]) in self.escapes:
                    pad = dict(pad, xy=self.escapes[(pad["ref"], pad["pin"])], layers=(2, 3, 5))
                groups[pad["net"]].append(pad)
        for net in sorted(groups, key=lambda n: (n in ("V5_REG", "P12", "N12", "AGND"), n)):
            pads = groups[net]
            if net.startswith("ADC_"):
                continue
            if net == "AGND":
                continue
            connected, remaining = pads[:1], pads[1:]
            failures = 0
            while remaining:
                _, i, j = min(
                    (math.dist(a["xy"], b["xy"]), i, j)
                    for i, a in enumerate(connected)
                    for j, b in enumerate(remaining)
                )
                a, b = connected[i], remaining.pop(j)
                width = 0.5 if net in ("V5_REG", "P12", "N12") else 0.25
                if not self.connect(a, b, width):
                    self.failed.append(
                        dict(net=net, source=[a["ref"], a["pin"]], target=[b["ref"], b["pin"]])
                    )
                    failures += 1
                connected.append(b)
            print(f"E12 route {net}: {len(pads)} lands, {failures} unresolved", flush=True)

    def prune_unused_vias(self):
        removed = []
        for v in list(children(self.board, "via")):
            xy = tuple(float(n) - 100 for n in first(v, "at")[1:3])
            net = next(n for n, c in self.nets.items() if c == int(first(v, "net")[1]))
            if net == "AGND":
                continue
            layers = set()
            for g in self.geometry:
                if g["net"] != net:
                    continue
                if (
                    g["kind"] == "line"
                    and point_segment(xy, g["start"], g["end"]) <= g["width"] / 2 + 0.3 + 1e-6
                ):
                    layers.update(g["layers"])
                if (
                    g["kind"] == "rect"
                    and g.get("through")
                    and all(abs(xy[i] - g["xy"][i]) <= g["size"][i] / 2 + 0.3 for i in (0, 1))
                ):
                    layers.update(g["layers"])
            if len(layers) <= 1:
                self.board.remove(v)
                removed.append(dict(net=net, point_relative_mm=xy, attached_layers=sorted(layers)))
        return removed


def e12_masks(self, net, width):
    blocks = np.zeros((6, self.nx, self.ny), dtype=bool)
    edge = 0.5 + width / 2 + 0.03
    border = (self.xx < edge) | (self.xx > SIZE[0] - edge) | (self.yy < edge) | (self.yy > SIZE[1] - edge)
    blocks[:] = border
    via_block = (self.xx < 0.83) | (self.xx > SIZE[0] - 0.83) | (self.yy < 0.83) | (self.yy > SIZE[1] - 0.83)
    for x, y in MOUNTS:
        blocks |= (self.xx - x) ** 2 + (self.yy - y) ** 2 < (3.7 + width / 2 + 0.03) ** 2
        via_block |= (self.xx - x) ** 2 + (self.yy - y) ** 2 < (4.03) ** 2
    for shape in self.geometry:
        same = shape["net"] == net and not (
            getattr(self, "role", None) and shape.get("role") and self.role != shape["role"]
        )
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
                hit = (x - shape["xy"][0]) ** 2 + (y - shape["xy"][1]) ** 2 <= (shape["radius"] + extra) ** 2
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
    if net != "AGND":
        blocks[1] = True
        blocks[4] = True
    if getattr(self, "role", None) == "sense":
        blocks[0] = True
        blocks[3] = True
        blocks[5] = True
    elif getattr(self, "role", None) == "force":
        blocks[2] = True
    return blocks, via_block
