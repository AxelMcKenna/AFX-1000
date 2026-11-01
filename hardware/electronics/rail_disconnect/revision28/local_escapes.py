"""Focused native bare-pad escapes using actual local pad/track/drill obstacles.

Only pins lacking a native via anchor are targeted. Outboard0.3/0.6mm filled
through vias and0.2mm tracks remain actual PCB objects checked by KiCad.
"""

import heapq
import itertools
import json
import math
import uuid

import numpy as np

from ...common.sexpr import a, children, read_sexpr, sexpr
from ..revision26 import router as aid
from .manufacturer import ROOT
from .repair import Router


def escape(rt, pad, maxdistance=6, step=0.025, min_distance=0):
    px, py = pad["xy"]
    extent = math.ceil(maxdistance / step)
    x = px + (np.arange(2 * extent + 1) - extent) * step
    y = py + (np.arange(2 * extent + 1) - extent) * step
    xx = x[:, None]
    yy = y[None, :]
    face = pad["layers"][0]
    net = pad["net"]
    blocked = np.zeros((len(x), len(y)), bool)
    vias = np.zeros_like(blocked)
    for g in rt.geometry:
        if g["net"] == "BULK_BODY_NOVIA":
            continue  # declared filled/capped flush process
        same = g["net"] == net
        for extra, dest in ((0.32, blocked), (0.52, vias)):
            if dest is blocked and (same or face not in g["layers"]):
                continue
            if dest is vias and same:
                if g["kind"] in ("line", "rect") or g.get("through"):
                    # E28 explicitly requires filled/capped via-in-pad. Its own
                    # SMD copper is not a foreign obstacle; every foreign pad,
                    # barrel, mounting hole and physical terminal reserve stays
                    # in this exact clearance calculation. Same-net drill-to-
                    # drill spacing still applies below.
                    continue
                extra = 0.26
            if g["kind"] == "line":
                ax, ay = g["start"]
                bx, by = g["end"]
                r = g["width"] / 2 + extra
                if (
                    max(ax, bx) + r < px - maxdistance
                    or min(ax, bx) - r > px + maxdistance
                    or max(ay, by) + r < py - maxdistance
                    or min(ay, by) - r > py + maxdistance
                ):
                    continue
                dx, dy = bx - ax, by - ay
                t = np.clip(((xx - ax) * dx + (yy - ay) * dy) / max(dx * dx + dy * dy, 1e-30), 0, 1)
                hit = (xx - ax - t * dx) ** 2 + (yy - ay - t * dy) ** 2 < r * r
            elif g["kind"] == "via":
                gx, gy = g["xy"]
                r = g["radius"] + extra
                if abs(gx - px) > maxdistance + r or abs(gy - py) > maxdistance + r:
                    continue
                hit = (xx - gx) ** 2 + (yy - gy) ** 2 < r * r
            else:
                gx, gy = g["xy"]
                w, h = g["size"]
                if abs(gx - px) > maxdistance + w / 2 + extra or abs(gy - py) > maxdistance + h / 2 + extra:
                    continue
                hit = (
                    np.maximum(abs(xx - gx) - w / 2, 0) ** 2 + np.maximum(abs(yy - gy) - h / 2, 0) ** 2
                    < extra * extra
                )
            dest |= hit
    border = (
        (xx < 0.81)
        | (xx > 155.19)
        | (yy < 0.81)
        | (yy > 44.44)
        | ((xx < 5.81) & (yy > 34.19))
        | ((xx > 153.69) & (yy > 34.49))
    )
    blocked |= border
    vias |= border
    # Candidate drill must allow at least one initial trace direction.
    radius2 = (xx - px) ** 2 + (yy - py) ** 2
    targets = ~vias & (radius2 <= maxdistance**2) & (radius2 >= min_distance**2)
    start = (extent, extent)
    if blocked[start]:
        return None, "native pad centre is trapped by foreign copper"
    serial = itertools.count()
    queue = [(0, next(serial), start)]
    costs = {start: 0}
    previous = {}
    visited = set()
    found = None
    while queue:
        _, _, point = heapq.heappop(queue)
        if point in visited:
            continue
        visited.add(point)
        if targets[point]:
            found = point
            break
        ix, iy = point
        for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1)):
            nx, ny = ix + dx, iy + dy
            if not (0 <= nx < len(x) and 0 <= ny < len(y)) or blocked[nx, ny]:
                continue
            value = costs[point] + math.hypot(dx, dy)
            if value < costs.get((nx, ny), float("inf")):
                costs[(nx, ny)] = value
                previous[(nx, ny)] = point
                heapq.heappush(queue, (value, next(serial), (nx, ny)))
    if found is None:
        return None, "no actual clearance path to an outboard drill within6mm"
    nodes = [found]
    while nodes[-1] != start:
        nodes.append(previous[nodes[-1]])
    nodes.reverse()
    points = [(px, py)]
    direction = None
    for before, after in zip(nodes, nodes[1:]):
        delta = (after[0] - before[0], after[1] - before[1])
        if delta != direction:
            points.append((float(x[before[0]]), float(y[before[1]])))
            direction = delta
    end = (round(float(x[found[0]]), 6), round(float(y[found[1]]), 6))
    points.append(end)
    rt.path(net, face, points, 0.2)
    rt.via(net, end)
    return dict(path=points, via=end, layer=aid.LAYERS[face]), None


def main(pins=None):
    path = ROOT / "rail_disconnect.kicad_pcb"
    tree = read_sexpr(path.read_text())
    rt = Router(tree)
    rows = json.loads((ROOT / "generated/open-components.json").read_text())
    targets = {}
    for row in rows:
        for group in row["components"]:
            if any(p["kind"] == "PCB_VIA" or len(p["layers"]) == 6 for p in group):
                continue
            for p in group:
                if p["kind"] == "PAD":
                    targets[p["uuid"]] = (row["net"], p)
    result = []
    for uid, (net, anchor) in targets.items():
        pad = next((p for p in rt.pads if p["net"] == net and math.dist(p["xy"], anchor["xy"]) < 1e-5), None)
        if pad is None:
            continue
        if pins is not None and [pad["ref"], pad["pin"]] not in pins:
            continue
        route, reason = escape(rt, pad)
        result.append(dict(ref=pad["ref"], pin=pad["pin"], net=net, route=route, unmet_reason=reason))
        print(pad["ref"], pad["pin"], net, bool(route), reason, flush=True)
    for index, n in enumerate(tree):
        if isinstance(n, list) and n and n[0] in ("segment", "via") and not children(n, "uuid"):
            n.append(
                [
                    a("uuid"),
                    a(str(uuid.uuid5(uuid.NAMESPACE_URL, f"rmx:E28:local-escape:{index}:{sexpr(n)}"))),
                ]
            )
    path.write_text(sexpr(tree) + "\n")
    (ROOT / "generated/local-pin-escapes.json").write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
