"""Prune reported dangling leaf chains up to actual pads, vias or junctions."""

import json
from collections import defaultdict

from ...common.sexpr import children, first, read_sexpr, sexpr
from ..revision26 import router as aid
from ..routing.check import point_segment
from .repair import ROOT, Router


def prune(label):
    path = ROOT / "rail_disconnect.kicad_pcb"
    tree = read_sexpr(path.read_text())
    report = json.loads((ROOT / f"generated/drc-{label}.json").read_text())
    targets = {v["items"][0]["uuid"] for v in report["violations"] if v["type"] == "track_dangling"}
    r = Router(tree)
    names = {str(n[1]): str(n[2]).lstrip("/") for n in children(tree, "net")}
    nodes = defaultdict(list)
    segments = {}
    for s in children(tree, "segment"):
        uid = str(first(s, "uuid")[1])
        net = names[str(first(s, "net")[1])]
        layer = aid.LAYERS.index(str(first(s, "layer")[1]))
        ends = [tuple(round(float(v) - 100, 6) for v in first(s, key)[1:3]) for key in ("start", "end")]
        segments[uid] = (s, net, layer, ends)
        for xy in ends:
            nodes[(net, layer, xy)].append(uid)
    removed = set()

    def terminal(net, layer, xy):
        for g in r.geometry:
            if g["net"] != net or layer not in g["layers"]:
                continue
            if (
                g["kind"] == "via"
                and sum((xy[i] - g["xy"][i]) ** 2 for i in (0, 1)) <= (g["radius"] + 0.001) ** 2
            ):
                return True
            if (
                g["kind"] == "line"
                and point_segment(xy, g["start"], g["end"]) < 1e-6
                and min(__import__("math").dist(xy, g["start"]), __import__("math").dist(xy, g["end"])) > 1e-6
            ):
                return True
            if g["kind"] == "rect" and all(
                abs(xy[i] - g["xy"][i]) <= g["size"][i] / 2 + 0.001 for i in (0, 1)
            ):
                return True
        return False

    for start in targets:
        if start in removed or start not in segments:
            continue
        _, net, layer, ends = segments[start]
        leaves = [xy for xy in ends if len(nodes[(net, layer, xy)]) == 1 and not terminal(net, layer, xy)]
        if not leaves:
            continue
        uid = start
        point = leaves[0]
        while uid not in removed:
            removed.add(uid)
            _, net, layer, ends = segments[uid]
            other = ends[1] if ends[0] == point else ends[0]
            attached = [x for x in nodes[(net, layer, other)] if x not in removed]
            if len(nodes[(net, layer, other)]) > 2 or terminal(net, layer, other) or len(attached) != 1:
                break
            uid = attached[0]
            point = other
    result = [
        n
        for n in tree
        if not (isinstance(n, list) and n and n[0] == "segment" and str(first(n, "uuid")[1]) in removed)
    ]
    path.write_text(sexpr(result) + "\n")
    (ROOT / f"generated/pruned-{label}.json").write_text(
        json.dumps([sexpr(segments[u][0]) for u in sorted(removed)], indent=2) + "\n"
    )
    print("Pruned", len(removed), "real dangling-chain segments")


if __name__ == "__main__":
    import sys

    prune(sys.argv[1])
