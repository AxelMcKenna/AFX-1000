"""Make same-net ground T junctions explicit without changing copper geometry."""

import copy
import math

from ...common.sexpr import children, first


def split_ground_junctions(board, layer="In3.Cu"):
    net = next(str(n[1]) for n in children(board, "net") if str(n[2]) == "/AGND")
    tracks = [
        s
        for s in children(board, "segment")
        if first(s, "layer")[1] == layer and str(first(s, "net")[1]) == net
    ]
    lines = [tuple(tuple(map(float, first(s, k)[1:3])) for k in ("start", "end")) for s in tracks]
    cuts = [{0.0, 1.0} for _ in tracks]

    def cross(a, b):
        return a[0] * b[1] - a[1] * b[0]

    def project(p, a, b):
        dx, dy = b[0] - a[0], b[1] - a[1]
        t = ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / (dx * dx + dy * dy)
        if -1e-8 <= t <= 1 + 1e-8 and math.dist(p, (a[0] + t * dx, a[1] + t * dy)) < 1e-7:
            return max(0, min(1, t))

    for i, (a, b) in enumerate(lines):
        for j, (c, d) in enumerate(lines[:i]):
            ab = (b[0] - a[0], b[1] - a[1])
            cd = (d[0] - c[0], d[1] - c[1])
            ac = (c[0] - a[0], c[1] - a[1])
            det = cross(ab, cd)
            if abs(det) > 1e-10:
                t, u = cross(ac, cd) / det, cross(ac, ab) / det
                if -1e-8 <= t <= 1 + 1e-8 and -1e-8 <= u <= 1 + 1e-8:
                    cuts[i].add(max(0, min(1, t)))
                    cuts[j].add(max(0, min(1, u)))
            else:
                for p in (c, d):
                    t = project(p, a, b)
                    if t is not None:
                        cuts[i].add(t)
                for p in (a, b):
                    t = project(p, c, d)
                    if t is not None:
                        cuts[j].add(t)
    vias = [
        tuple(map(float, first(v, "at")[1:3]))
        for v in children(board, "via")
        if str(first(v, "net")[1]) == net
    ]
    pieces = []
    seen = set()
    for s, (a, b), values in zip(tracks, lines, cuts):
        for at in vias:
            t = project(at, a, b)
            if t is not None:
                values.add(t)
        points = [tuple(round(a[k] + t * (b[k] - a[k]), 6) for k in (0, 1)) for t in sorted(values)]
        for start, end in zip(points, points[1:]):
            if start == end:
                continue
            key = (tuple(sorted((start, end))), float(first(s, "width")[1]))
            if key in seen:
                continue
            seen.add(key)
            piece = copy.deepcopy(s)
            first(piece, "start")[1:3] = start
            first(piece, "end")[1:3] = end
            pieces.append(piece)
    ids = {id(s) for s in tracks}
    board[:] = [s for s in board if id(s) not in ids] + pieces
    return len(pieces) - len(tracks)
