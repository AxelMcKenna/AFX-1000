"""Replace an acute overlapping ribbon/disc seam with one tangent outline.

This changes actual copper. It does not change the native sliver rule, suppress
the finding, or establish a resistance/manufacturing acceptance.
"""

import copy
import hashlib
import json
import math

from ...common.sexpr import a, children, first, read_sexpr, sexpr
from .repair import ROOT

RIBBON = "e9d6bd80-2d6a-5590-8142-772073a1d2f5"
CAP = "a96aea78-53a3-54b2-9b19-274367ca7319"


def tangent_start_cap(start, end, radius=4, arc_segments=32):
    """An actual constant-width arm with a semicircular source termination."""
    angle = math.atan2(end[1] - start[1], end[0] - start[0])
    normal = (-math.sin(angle) * radius, math.cos(angle) * radius)
    points = [
        (start[0] + normal[0], start[1] + normal[1]),
        (end[0] + normal[0], end[1] + normal[1]),
        (end[0] - normal[0], end[1] - normal[1]),
    ]
    points.extend(
        (
            start[0] + radius * math.cos(angle - math.pi / 2 - i * math.pi / arc_segments),
            start[1] + radius * math.sin(angle - math.pi / 2 - i * math.pi / arc_segments),
        )
        for i in range(arc_segments)
    )
    return points


def main():
    path = ROOT / "rail_disconnect.kicad_pcb"
    before = path.read_bytes()
    tree = read_sexpr(before.decode())
    zones = {str(first(z, "uuid")[1]): z for z in children(tree, "zone") if children(z, "uuid")}
    assert RIBBON in zones and CAP in zones, "Exact original copper seam required"
    ribbon, cap = zones[RIBBON], zones[CAP]
    assert first(ribbon, "net_name")[1] == first(cap, "net_name")[1] == "/5V_DIG"
    assert first(ribbon, "layer")[1] == first(cap, "layer")[1] == "In3.Cu"
    originals = [sexpr(copy.deepcopy(z)) for z in (ribbon, cap)]
    polygon = first(ribbon, "polygon")
    polygon[1] = [a("pts")] + [
        [a("xy"), a(f"{x:.6f}"), a(f"{y:.6f}")] for x, y in tangent_start_cap((231.476, 105.5), (246, 102.5))
    ]
    tree.remove(cap)
    path.write_text(sexpr(tree) + "\n")
    (ROOT / "generated/ribbon-tangent-cap-repair.json").write_text(
        json.dumps(
            dict(
                before_sha256=hashlib.sha256(before).hexdigest(),
                after_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                original_zone_objects=originals,
                replacement_zone_object=sexpr(ribbon),
                ribbon_width_mm=8,
                native_verification_required=True,
                resistance_bound_qualified=False,
                physical_qualified=False,
            ),
            indent=2,
        )
        + "\n"
    )


if __name__ == "__main__":
    main()
