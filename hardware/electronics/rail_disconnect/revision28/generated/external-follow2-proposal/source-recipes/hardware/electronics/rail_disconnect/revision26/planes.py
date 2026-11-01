"""Proposed E26 wide current/return planes; native fill and loss analysis required."""

import itertools
import math

from ...common.sexpr import children, read_sexpr
from ..placement.generate import OUTLINE

_priorities = itertools.count(1)


def zone(net, layer, points, priority, nets):
    priority = priority * 1000 + next(_priorities)
    pts = " ".join(f"(xy {100 + x:.6f} {100 + y:.6f})" for x, y in points)
    return read_sexpr(f'''(zone (net {nets[net]}) (net_name "/{net}") (layer "{layer}")
      (hatch edge .5) (priority {priority}) (connect_pads yes (clearance .2))
      (min_thickness .15) (fill yes (thermal_gap .25) (thermal_bridge_width .3)
        (island_removal_mode 0) (island_area_min 1)) (polygon (pts {pts})))''')


def ribbon(net, layer, points, width, priority, nets):
    result = []
    for a, b in zip(points, points[1:]):
        dx, dy = b[0] - a[0], b[1] - a[1]
        length = math.hypot(dx, dy)
        nx, ny = -dy / length * width / 2, dx / length * width / 2
        result.append(
            zone(
                net,
                layer,
                [
                    (a[0] + nx, a[1] + ny),
                    (b[0] + nx, b[1] + ny),
                    (b[0] - nx, b[1] - ny),
                    (a[0] - nx, a[1] - ny),
                ],
                priority,
                nets,
            )
        )
    for x, y in points:
        result.append(
            zone(
                net,
                layer,
                [
                    (x + width / 2 * math.cos(i * math.pi / 16), y + width / 2 * math.sin(i * math.pi / 16))
                    for i in range(32)
                ],
                priority,
                nets,
            )
        )
    return result


def add(board):
    global _priorities
    _priorities = itertools.count(1)
    nets = {str(n[2]).lstrip("/"): int(n[1]) for n in children(board, "net")}
    plans = []

    def path(net, layer, points, width, priority):
        board.extend(ribbon(net, layer, points, width, priority, nets))
        plans.append(dict(net=net, layer=layer, centerline_mm=points, width_mm=width, priority=priority))

    for layer in ("In1.Cu", "In4.Cu"):
        board.append(zone("AGND", layer, OUTLINE, 0, nets))
    path("P19_SRC", "F.Cu", [(4, 2.3), (4, 7)], 1.2, 30)
    path("P19_SRC", "F.Cu", [(4, 7), (19.67, 7)], 4, 30)
    path("P19", "F.Cu", [(29.33, 7), (29.33, 25.5), (23.25, 25.5)], 5, 29)
    path("P19", "F.Cu", [(29.33, 25.5), (50, 37.5)], 5, 29)
    path("P12_SRC", "F.Cu", [(11.62, 2.3), (78.67, 2.3), (78.67, 7)], 3, 28)
    path("P12", "F.Cu", [(88.33, 7), (88.33, 20), (81.25, 25.5), (57.62, 37.5)], 5, 27)
    path("N19_SRC", "B.Cu", [(9.08, 2.3), (9.08, 7)], 1.2, 30)
    path("N19_SRC", "B.Cu", [(9.08, 7), (53.67, 7)], 4, 30)
    path("N19", "B.Cu", [(63.33, 7), (66.75, 25.5), (55.08, 37.5)], 5, 29)
    path("N12_SRC", "B.Cu", [(14.16, 2.3), (95.67, 2.3), (95.67, 7)], 3, 28)
    path("N12", "B.Cu", [(105.33, 7), (97.75, 25.5), (60.16, 37.5)], 5, 27)
    path("V5_REG_SRC", "In2.Cu", [(16.7, 2.3), (33.3, 7)], 12, 35)
    path("V5_REG", "In3.Cu", [(49.7, 7), (62.7, 37.5)], 12, 35)
    path("V5_REG", "In3.Cu", [(62.7, 37.5), (142.5, 15.25)], 5, 35)
    path("5V_DIG_SRC", "F.Cu", [(119, 3), (126.67, 7), (126.67, 13)], 8, 35)
    path("5V_DIG", "F.Cu", [(146, 2.5), (136.33, 7), (136.33, 13), (142.75, 37)], 8, 34)
    # Expand the common buses only inside the source-side gap. A wide round
    # track cap at the source lands would short the adjacent drain pad.
    for left, right, y, net in [
        (22.8, 26.2, 7, "P19_COMMON"),
        (56.8, 60.2, 7, "N19_COMMON"),
        (81.8, 85.2, 7, "P12_COMMON"),
        (98.8, 102.2, 7, "N12_COMMON"),
        (39.8, 43.2, 7, "V5_REG_COMMON"),
        (129.8, 133.2, 7, "5V_DIG_COMMON"),
        (129.8, 133.2, 13, "5V_DIG_COMMON"),
    ]:
        board.append(
            zone(
                net,
                "F.Cu",
                [
                    (left - 0.35, y - 1),
                    (left + 0.8, y - 1),
                    (left + 0.8, y - 2.255),
                    (right + 0.35, y - 2.255),
                    (right + 0.35, y + 0.985),
                    (right - 0.8, y + 0.985),
                    (right - 0.8, y + 2.255),
                    (left - 0.35, y + 2.255),
                ],
                50,
                nets,
            )
        )
    # Copper under screw heads is excluded on every layer, not merely around
    # the nominal NPTH drill. The body/escape placer reserves an even larger area.
    for x, y in ((4, 20), (152, 3.8), (10, 36), (100, 36)):
        pts = " ".join(
            f"(xy {100 + x + 3.2 * math.cos(i * math.pi / 16):.6f} {100 + y + 3.2 * math.sin(i * math.pi / 16):.6f})"
            for i in range(32)
        )
        board.append(
            read_sexpr(f"""(zone (net 0) (net_name "") (layers "*.Cu") (hatch edge .5)
          (keepout (tracks not_allowed) (vias not_allowed) (pads allowed) (copperpour not_allowed) (footprints allowed))
          (polygon (pts {pts})))""")
        )
    return plans
