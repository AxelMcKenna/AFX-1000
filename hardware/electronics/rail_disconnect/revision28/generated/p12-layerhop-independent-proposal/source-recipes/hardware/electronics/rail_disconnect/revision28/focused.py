"""Exact-coordinate local escapes where a coarse routing grid traps real pins."""

import json
import math
import uuid

from ...common.sexpr import a, children, read_sexpr, sexpr
from ..revision26 import router as aid
from ..routing.check import point_segment, segment_distance
from .repair import ROOT, Router

PINS = [
    ("U11", "10"),
    ("U9", "5"),
    ("R63", "1"),
    ("R64", "2"),
    ("R68", "1"),
    ("R59", "2"),
    ("R60", "2"),
    ("R36", "2"),
    ("R38", "1"),
]


def rect_edges(g):
    x, y = g["xy"]
    w, h = g["size"]
    corners = [(x - w / 2, y - h / 2), (x + w / 2, y - h / 2), (x + w / 2, y + h / 2), (x - w / 2, y + h / 2)]
    return list(zip(corners, corners[1:] + corners[:1]))


def inside(p, g):
    return all(abs(p[i] - g["xy"][i]) <= g["size"][i] / 2 for i in (0, 1))


def legal_line(r, net, layer, start, end, width=0.25):
    for g in r.geometry:
        if g["net"] == net or layer not in g["layers"]:
            continue
        need = 0.200001 + width / 2
        if g["kind"] == "line":
            distance = segment_distance(start, end, g["start"], g["end"]) - g["width"] / 2
        elif g["kind"] == "via":
            distance = point_segment(g["xy"], start, end) - g["radius"]
        else:
            if inside(start, g) or inside(end, g):
                return False
            distance = min(segment_distance(start, end, a, b) for a, b in rect_edges(g))
        if distance < need:
            return False
    return True


def legal_via(r, net, point):
    x, y = point
    if not (0.81 <= x <= 155.19 and 0.81 <= y <= 44.44):
        return False
    for g in r.geometry:
        if g["kind"] == "line":
            if g["net"] == net:
                continue
            distance = point_segment(point, g["start"], g["end"]) - g["width"] / 2
            need = 0.500001
        elif g["kind"] == "via":
            distance = math.dist(point, g["xy"]) - g["radius"]
            need = 0.550001 if g["net"] == net else 0.500001
        else:
            distance = math.hypot(*(max(abs(point[i] - g["xy"][i]) - g["size"][i] / 2, 0) for i in (0, 1)))
            need = 0.410001 if g["net"] == net else 0.500001
        if distance < need:
            return False
    return True


def main():
    aid.STEP = 0.125
    board = ROOT / "rail_disconnect.kicad_pcb"
    tree = read_sexpr(board.read_text())
    r = Router(tree)
    results = []
    for ref, pin in PINS:
        pad = next(p for p in r.by_ref[ref] if p["pin"] == pin)
        others = r.by_ref[ref]
        cx = sum(p["xy"][0] for p in others) / len(others)
        sign = 1 if pad["xy"][0] > cx else -1
        start = pad["xy"]
        layer = pad["layers"][0]
        # Keep the initial section exactly on the manufacturer's lead centerline.
        choices = []
        for distance in (1.5, 2, 2.5, 3, 4, 5, 6, 8):
            corner = (start[0] + sign * distance, start[1])
            for dy in (0, 0.5, -0.5, 1, -1, 2, -2, 3, -3, 4, -4):
                end = (corner[0], corner[1] + dy)
                choices.append((distance + abs(dy), corner, end))
        good = False
        for _, corner, end in sorted(choices):
            if not legal_via(r, pad["net"], end) or not legal_line(r, pad["net"], layer, start, corner):
                continue
            if corner != end and not legal_line(r, pad["net"], layer, corner, end):
                continue
            r.path(pad["net"], layer, [start, corner, end], 0.25)
            r.via(pad["net"], end)
            good = True
            break
        results.append(
            dict(
                ref=ref,
                pin=pin,
                net=pad["net"],
                escaped=good,
                exact_pin_mm=start,
                via_mm=end if good else None,
            )
        )
        print(ref, pin, good, end if good else None, flush=True)
    for index, node in enumerate(tree):
        if isinstance(node, list) and node and node[0] in ("segment", "via") and not children(node, "uuid"):
            node.append(
                [a("uuid"), a(str(uuid.uuid5(uuid.NAMESPACE_URL, f"rmx:E28:focused:{index}:{sexpr(node)}")))]
            )
    board.write_text(sexpr(tree) + "\n")
    (ROOT / "generated/focused-escapes.json").write_text(json.dumps(results, indent=2) + "\n")


if __name__ == "__main__":
    main()
