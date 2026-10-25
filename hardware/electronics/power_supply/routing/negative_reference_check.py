"""Independent negative-reference connectivity, return and package contracts."""

import math

from ...common.sexpr import children, first
from ...output_stage.check_placement import transform

ALL = ("F.Cu", "B.Cu", "In1.Cu", "In2.Cu", "In3.Cu", "In4.Cu")
B = ("B.Cu",)
PATHS = [
    ("nref_raw_bias", "RAW_N22", ("R18", 2), ("C10", 1), 30, ALL),
    ("nref_bias_shunt", "NREF_2V5", ("R18", 1), ("U12", 4), 6, B),
    ("nref_test_tie", "NREF_2V5", ("U12", 4), ("U12", 5), 6, B),
    ("nref_filter_input", "NREF_2V5", ("R19", 1), ("U12", 4), 20, B),
    ("nref_film_filter", "NREF_FILTER", ("R19", 2), ("C33", 1), 5, ("F.Cu", "B.Cu")),
    ("nref_n19_target", "NREF_FILTER", ("C33", 1), ("U6", 3), 80, ALL),
    ("nref_n12_target", "NREF_FILTER", ("C33", 1), ("U6", 5), 90, ALL),
    ("nref_shunt_return", "AGND", ("U12", 6), ("J2", 2), 65, ("F.Cu", "B.Cu", "In3.Cu")),
    ("nref_filter_return", "AGND", ("C33", 2), ("J2", 2), 15, ("F.Cu", "In3.Cu")),
]
MINIMUM_WIDTHS = {p[0]: 0.26 for p in PATHS}


def component_faces(tree):
    expected = {"U12": "B.Cu", "R18": "B.Cu", "R19": "B.Cu", "C33": "F.Cu", "U6": "B.Cu"}
    found = {}
    for fp in children(tree, "footprint"):
        ref = next(p[2] for p in children(fp, "property") if p[1] == "Reference")
        if ref in expected:
            assert first(fp, "layer")[1] == expected[ref], (ref, "negative reference face changed")
            found[ref] = expected[ref]
    assert found == expected
    return found


def native_connections(drc):
    assert not any("/NREF_" in str(item) for item in drc["unconnected_items"]), (
        "Negative reference has native open connections"
    )
    return dict(stage_native_open_items=0, noise_or_startup_qualified=False)


def reference_return(tree, checked_terminals=(("U12", "6"), ("C33", "2"))):
    """After removing the J2 ground land, reject a copper shunt to PGND.

    Native DRC permits same-net intersections. This checks actual track/via/pad
    contact on all six layers, including surface-pad and midsegment junctions.
    Plane isolation and clearance are checked separately by ground_layout.
    """
    nets = {str(n[1]): str(n[2]).lstrip("/") for n in children(tree, "net")}
    copper, terminals = [], {}

    def add(a, b, radius, layers, power=False, rect=False):
        copper.append((a, b, radius, set(layers), power, rect))
        return len(copper) - 1

    for s in children(tree, "segment"):
        if nets[str(first(s, "net")[1])] == "AGND":
            a, b = [tuple(map(float, first(s, k)[1:3])) for k in ("start", "end")]
            layer = first(s, "layer")[1]
            add(a, b, float(first(s, "width")[1]) / 2, [layer], layer == "In1.Cu")
    for v in children(tree, "via"):
        if nets[str(first(v, "net")[1])] == "AGND":
            a = tuple(map(float, first(v, "at")[1:3]))
            isolated = False
            for z in children(tree, "zone"):
                if not children(z, "keepout") or not children(z, "layer") or first(z, "layer")[1] != "In1.Cu":
                    continue
                pts = children(first(first(z, "polygon"), "pts"), "xy")
                center = tuple(sum(float(p[i]) for p in pts) / len(pts) for i in (1, 2))
                isolated |= math.dist(a, center) < 1e-5
            add(a, a, float(first(v, "size")[1]) / 2, ALL, not isolated)
    for fp in children(tree, "footprint"):
        ref = next(p[2] for p in children(fp, "property") if p[1] == "Reference")
        for pad in children(fp, "pad"):
            if not children(pad, "net") or str(first(pad, "net")[-1]) != "/AGND":
                continue
            key = (ref, str(pad[1]))
            if key == ("J2", "2"):
                continue
            x, y = transform(fp, first(pad, "at")[1:3])
            w, h = map(float, first(pad, "size")[1:3])
            angle = sum(
                float(first(item, "at")[3]) if len(first(item, "at")) > 3 else 0 for item in (fp, pad)
            )
            assert abs(math.sin(math.radians(angle * 2))) < 1e-6
            if abs(math.sin(math.radians(angle))) > 0.5:
                w, h = h, w
            plated = pad[2] == "thru_hole"
            power = plated and key not in (("C32", "2"), ("C33", "2"))
            terminals[key] = add(
                (x - w / 2, y - h / 2),
                (x + w / 2, y + h / 2),
                0,
                ALL if plated else [first(fp, "layer")[1]],
                power,
                True,
            )

    def point_distance(p, a, b):
        dx, dy = b[0] - a[0], b[1] - a[1]
        t = max(0, min(1, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / (dx * dx + dy * dy))) if dx or dy else 0
        return math.dist(p, (a[0] + t * dx, a[1] + t * dy))

    def line_distance(a, b, c, d):
        def cross(u, v):
            return u[0] * v[1] - u[1] * v[0]

        ab, cd, ac = (b[0] - a[0], b[1] - a[1]), (d[0] - c[0], d[1] - c[1]), (c[0] - a[0], c[1] - a[1])
        det = cross(ab, cd)
        if abs(det) > 1e-10 and 0 <= cross(ac, cd) / det <= 1 and 0 <= cross(ac, ab) / det <= 1:
            return 0
        return min(
            point_distance(a, c, d), point_distance(b, c, d), point_distance(c, a, b), point_distance(d, a, b)
        )

    def distance(one, other):
        a, b, _, _, _, rect = one
        c, d, _, _, _, other_rect = other
        if rect and other_rect:
            return math.hypot(max(a[0] - d[0], c[0] - b[0], 0), max(a[1] - d[1], c[1] - b[1], 0))
        if rect:
            return distance(other, one)
        if other_rect:
            if any(c[0] <= p[0] <= d[0] and c[1] <= p[1] <= d[1] for p in (a, b)):
                return 0
            corners = [c, (d[0], c[1]), d, (c[0], d[1])]
            return min(line_distance(a, b, e, f) for e, f in zip(corners, corners[1:] + corners[:1]))
        return line_distance(a, b, c, d)

    parents = list(range(len(copper)))

    def root(i):
        while parents[i] != i:
            parents[i] = parents[parents[i]]
            i = parents[i]
        return i

    for i, one in enumerate(copper):
        for j, other in enumerate(copper[:i]):
            if one[3] & other[3] and distance(one, other) <= one[2] + other[2] + 1e-8:
                parents[root(i)] = root(j)
    reference_roots = {root(terminals[k]) for k in checked_terminals}
    assert len(reference_roots) == 1, "Negative shunt and filter returns are disconnected"
    power_roots = {root(i) for i, shape in enumerate(copper) if shape[4]}
    assert not reference_roots & power_roots, "Negative reference return shunted to power ground before J2"
    return dict(
        output_ground_land=["J2", 2],
        checked_terminals=[list(k) for k in checked_terminals],
        separate_from_power_copper_before_header=True,
        plane_isolation_checked_separately=True,
    )
