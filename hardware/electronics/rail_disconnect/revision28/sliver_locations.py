"""Locate native union sliver vertices; KiCad Python, no DRC settings changed.

KiCad 10's CLI omits the marker coordinate when a finding has no associated
items. This mirrors its public sliver-checker's fixed default angle/length/
width test on actual native polygon unions, solely to locate repair work.
Native CLI DRC, not this locator, decides whether a repair passes.
"""

import argparse
import json
import math
from pathlib import Path

import pcbnew


def scan(board):
    result = []
    for layername in ("F.Cu", "In1.Cu", "In2.Cu", "In3.Cu", "In4.Cu", "B.Cu"):
        layer = board.GetLayerID(layername)
        poly = pcbnew.SHAPE_POLY_SET()
        for item in list(board.GetTracks()) + [p for f in board.GetFootprints() for p in f.Pads()]:
            if item.IsOnLayer(layer):
                item.TransformShapeToPolygon(poly, layer, 0, pcbnew.FromMM(0.02), pcbnew.ERROR_INSIDE)
        for zone in board.Zones():
            if zone.IsOnLayer(layer) and not zone.GetIsRuleArea():
                poly.Append(zone.GetFilledPolysList(layer))
        poly.Simplify()
        for index in range(poly.OutlineCount()):
            chain = poly.Outline(index)
            pts = [(chain.CPoint(i).x, chain.CPoint(i).y) for i in range(chain.PointCount())]
            count = len(pts)
            if count <= 5:
                continue

            def area(p, q, r):
                return (q[1] - p[1]) * (r[0] - q[0]) - (q[0] - p[0]) * (r[1] - q[1])

            def inside(a, b):
                prev = (count + a - 1) % count
                after = (a + 1) % count
                if area(pts[prev], pts[a], pts[after]) < 0:
                    return area(pts[a], pts[b], pts[after]) >= 0 and area(pts[a], pts[prev], pts[b]) >= 0
                return area(pts[a], pts[b], pts[prev]) < 0 or area(pts[a], pts[after], pts[b]) < 0

            k = 0
            while k < count:
                prior = (count + k - 1) % count
                after = (k + 1) % count
                point = pts[k]
                previous = pts[prior]
                vp = (previous[0] - point[0], previous[1] - point[1])
                offset = 1
                while abs(vp[0]) < 800 and abs(vp[1]) < 800 and offset < count:
                    point = pts[(k + offset) % count]
                    offset += 1
                    vp = (previous[0] - point[0], previous[1] - point[1])
                if offset >= count:
                    break
                following = pts[after]
                va = (following[0] - point[0], following[1] - point[1])
                forward = 1
                while abs(va[0]) < 800 and abs(va[1]) < 800 and forward < count:
                    after = (k + forward) % count
                    forward += 1
                    following = pts[after]
                    va = (following[0] - point[0], following[1] - point[1])
                if vp[0] * va[0] + vp[1] * va[1] > 0 and inside(prior, after):
                    included = (following[0] - previous[0], following[1] - previous[1])
                    arm1 = vp[0] ** 2 + vp[1] ** 2
                    arm2 = va[0] ** 2 + va[1] ** 2
                    opp = included[0] ** 2 + included[1] ** 2
                    cosine = abs((opp - arm1 - arm2) / math.sqrt(arm1 * arm2)) if arm1 * arm2 else 0
                    if (
                        cosine > 2 * math.cos(math.radians(20))
                        and 2 - cosine > 1.1920929e-7
                        and opp > 80000**2
                    ):
                        result.append(
                            dict(
                                layer=layername,
                                xy_mm=[point[0] / 1e6, point[1] / 1e6],
                                adjacent_mm=[[x / 1e6, y / 1e6] for x, y in (previous, following)],
                            )
                        )
                k += offset
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("board")
    parser.add_argument("output")
    args = parser.parse_args()
    findings = scan(pcbnew.LoadBoard(args.board))
    Path(args.output).write_text(json.dumps(findings, indent=2) + "\n")
    print(json.dumps(findings, indent=2))
