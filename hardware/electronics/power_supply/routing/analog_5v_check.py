"""Independent analog-5 V/reference path and copper-plane requirements."""

import math

from ...common.sexpr import children, first
from ...output_stage.check_placement import transform

F = ("F.Cu",)
B = ("B.Cu",)
MIXED = ("F.Cu", "B.Cu", "In2.Cu", "In3.Cu", "In4.Cu")
QUIET = ("F.Cu", "B.Cu", "In3.Cu")
PATHS = [
    ("ref_input_bypass", "5V_DIG_SRC", ("C30", 1), ("U4", 2), 9, B),
    ("ref_enhanced_enable", "5V_DIG_SRC", ("U4", 1), ("U4", 2), 2, B),
    ("ref_source_feed", "5V_DIG_SRC", ("C18", 1), ("U4", 2), 115, MIXED),
    ("ref_output_bypass", "PREF_2V5", ("U4", 6), ("C31", 1), 4, B),
    ("ref_filter_input", "PREF_2V5", ("U4", 6), ("R17", 1), 22, MIXED),
    ("ref_filter_cap", "PREF_FILTER", ("R17", 2), ("C32", 1), 22, MIXED),
    ("ref_target_5v", "PREF_FILTER", ("C32", 1), ("U5", 10), 5, MIXED),
    ("ref_target_p19", "PREF_FILTER", ("C32", 1), ("U5", 3), 16, MIXED),
    ("ref_target_p12", "PREF_FILTER", ("U5", 3), ("U5", 5), 7, F),
    ("ref_input_ground", "AGND", ("C30", 2), ("U4", 4), 5, B),
    ("ref_output_ground", "AGND", ("C31", 2), ("U4", 4), 10, B),
    ("ref_star_return", "AGND", ("U4", 4), ("J2", 2), 47, QUIET),
    ("ref_film_return", "AGND", ("C32", 2), ("J2", 2), 75, QUIET),
    ("target_positive_supply", "RAW_P22", ("C5", 1), ("U5", 4), 50, MIXED),
    ("target_hf_bypass", "RAW_P22", ("U5", 4), ("C59", 1), 4, MIXED),
    ("target_bulk_bypass", "RAW_P22", ("U5", 4), ("C60", 1), 11, MIXED),
    ("target_hf_return", "AGND", ("C59", 2), ("U5", 11), 12, QUIET),
    ("target_bulk_return", "AGND", ("C60", 2), ("U5", 11), 9, QUIET),
    ("target_spare_input_ground", "AGND", ("U5", 12), ("U5", 11), 6, F),
    ("target_spare_feedback", "SPARE_OUT", ("U5", 13), ("U5", 14), 2, F),
    ("target_star_return", "AGND", ("U5", 11), ("J2", 2), 60, QUIET),
    ("analog_5v_local_comp_out", "V5_REG_DRIVE", ("U5", 8), ("C44", 1), 6, ("F.Cu", "B.Cu")),
    ("analog_5v_local_comp_inv", "V5_REG_FB", ("U5", 9), ("C44", 2), 8, ("F.Cu", "B.Cu")),
    ("analog_5v_drive_isolation", "V5_REG_DRIVE", ("U5", 8), ("R32", 1), 14, MIXED),
    ("analog_5v_drive_set", "V5_REG_SET", ("R32", 2), ("U9", 4), 57, ("B.Cu", "In2.Cu")),
    ("analog_5v_set_kelvin", "V5_REG_SET", ("R30", 1), ("U9", 4), 57, ("F.Cu", "B.Cu", "In2.Cu")),
    ("analog_5v_divider_pair", "V5_REG_FB", ("R30", 2), ("R31", 1), 3, F),
    ("analog_5v_feedback_inv", "V5_REG_FB", ("R30", 2), ("U5", 9), 21, MIXED),
    ("analog_5v_divider_return", "AGND", ("R31", 2), ("J2", 2), 70, QUIET),
    ("analog_5v_set_filter", "V5_REG_SET", ("U9", 4), ("C45", 1), 10, B),
    ("analog_5v_set_filter_return", "AGND", ("C45", 2), ("J2", 2), 110, QUIET),
    ("analog_5v_input_bypass", "V5_PRE", ("C46", 1), ("U9", 7), 16, ("F.Cu", "B.Cu")),
    ("analog_5v_control_power", "VIN_PROTECTED", ("C27", 1), ("U9", 5), 28, ("F.Cu", "B.Cu", "In4.Cu")),
    ("analog_5v_out_pin_1", "V5_REG_SRC", ("U9", 1), ("U9", 9), 4, B),
    ("analog_5v_out_pin_2", "V5_REG_SRC", ("U9", 2), ("U9", 9), 5, B),
    ("analog_5v_out_pin_3", "V5_REG_SRC", ("U9", 3), ("U9", 9), 6, B),
    ("analog_5v_output_bulk", "V5_REG_SRC", ("C47", 1), ("U9", 9), 8, B),
    ("analog_5v_output_hf", "V5_REG_SRC", ("C48", 1), ("U9", 9), 6, B),
    ("analog_5v_input_ground", "AGND", ("C46", 2), ("J1", 2), 70, ("F.Cu", "B.Cu", "In1.Cu")),
    ("analog_5v_output_bulk_ground", "AGND", ("C47", 2), ("C25", 2), 10, ("F.Cu", "B.Cu", "In1.Cu")),
    ("analog_5v_output_hf_ground", "AGND", ("C48", 2), ("C26", 2), 14, ("F.Cu", "B.Cu", "In1.Cu")),
    ("analog_5v_minimum_load_return", "AGND", ("R33", 2), ("C19", 2), 18, ("F.Cu", "B.Cu", "In1.Cu")),
]
MINIMUM_WIDTHS = {
    name: 0.35
    if name in ("target_positive_supply", "target_hf_bypass", "target_bulk_bypass", "analog_5v_control_power")
    else 0.5
    for name in (
        "target_positive_supply",
        "target_hf_bypass",
        "target_bulk_bypass",
        "analog_5v_control_power",
        "analog_5v_out_pin_1",
        "analog_5v_out_pin_2",
        "analog_5v_out_pin_3",
        "analog_5v_output_bulk",
        "analog_5v_output_hf",
        "analog_5v_input_bypass",
        "analog_5v_input_ground",
        "analog_5v_output_bulk_ground",
        "analog_5v_output_hf_ground",
    )
}


def component_faces(tree):
    expected = {
        "U4": "B.Cu",
        "U5": "F.Cu",
        "U9": "B.Cu",
        "R17": "F.Cu",
        "C30": "B.Cu",
        "C31": "B.Cu",
        "C44": "B.Cu",
        "C59": "B.Cu",
        "C60": "B.Cu",
        "R30": "F.Cu",
        "R31": "F.Cu",
        "R32": "B.Cu",
        "C45": "B.Cu",
        "C46": "B.Cu",
        "C47": "B.Cu",
        "C48": "B.Cu",
    }
    found = {}
    for fp in children(tree, "footprint"):
        props = {p[1]: p[2] for p in children(fp, "property")}
        ref = props["Reference"]
        if ref not in expected:
            continue
        assert first(fp, "layer")[1] == expected[ref], (
            ref,
            "analog regulator/reference component on wrong face",
        )
        if ref == "U4":
            assert props["Value"] == "REF5025EIDR", "Pin 1 enable requires the enhanced E-grade reference"
        found[ref] = expected[ref]
    assert found == expected
    return found


def kelvin_separation(tree, regulator="U9", pad_number=4, net_name="V5_REG_SET", driver="R32", sense="R30"):
    """Drive and sense must be disconnected after removing the U9 SET land.

    Use actual copper widths and same-layer intersections, including T junctions
    and vias. Native same-net DRC alone cannot detect this layout error.
    """
    footprints = {
        next(p[2] for p in children(f, "property") if p[1] == "Reference"): f
        for f in children(tree, "footprint")
    }
    set_pad = next(p for p in children(footprints[regulator], "pad") if str(p[1]) == str(pad_number))
    center = transform(footprints[regulator], first(set_pad, "at")[1:3])
    width, height = map(float, first(set_pad, "size")[1:3])
    bounds = (
        (center[0] - width / 2, center[0] + width / 2),
        (center[1] - height / 2, center[1] + height / 2),
    )

    def outside(a, b):
        enter, leave = 0, 1
        delta = (b[0] - a[0], b[1] - a[1])
        for i, (lo, hi) in enumerate(bounds):
            if abs(delta[i]) < 1e-9:
                if not lo <= a[i] <= hi:
                    return [(a, b)]
                continue
            start, end = sorted(((lo - a[i]) / delta[i], (hi - a[i]) / delta[i]))
            enter, leave = max(enter, start), min(leave, end)
        if enter > leave:
            return [(a, b)]

        def point(t):
            return (a[0] + delta[0] * t, a[1] + delta[1] * t)

        return ([(a, point(enter))] if enter > 1e-9 else []) + (
            [(point(leave), b)] if leave < 1 - 1e-9 else []
        )

    nets = {str(n[1]): str(n[2]).lstrip("/") for n in children(tree, "net")}
    copper = []
    for s in children(tree, "segment"):
        if nets[str(first(s, "net")[1])] != net_name:
            continue
        a, b = [tuple(map(float, first(s, k)[1:3])) for k in ("start", "end")]
        fragments = (
            outside(a, b) if first(s, "layer")[1] == first(footprints[regulator], "layer")[1] else [(a, b)]
        )
        copper.extend((a, b, float(first(s, "width")[1]) / 2, {first(s, "layer")[1]}) for a, b in fragments)
    layers = {"F.Cu", "In1.Cu", "In2.Cu", "In3.Cu", "In4.Cu", "B.Cu"}
    for v in children(tree, "via"):
        if nets[str(first(v, "net")[1])] == net_name:
            at = tuple(map(float, first(v, "at")[1:3]))
            copper.append((at, at, float(first(v, "size")[1]) / 2, layers))

    def point_distance(p, a, b):
        dx, dy = b[0] - a[0], b[1] - a[1]
        t = max(0, min(1, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / (dx * dx + dy * dy))) if dx or dy else 0
        return math.dist(p, (a[0] + t * dx, a[1] + t * dy))

    def separation(a, b, c, d):
        def cross(u, v):
            return u[0] * v[1] - u[1] * v[0]

        ab, cd, ac = (b[0] - a[0], b[1] - a[1]), (d[0] - c[0], d[1] - c[1]), (c[0] - a[0], c[1] - a[1])
        det = cross(ab, cd)
        if abs(det) > 1e-10 and 0 <= cross(ac, cd) / det <= 1 and 0 <= cross(ac, ab) / det <= 1:
            return 0
        return min(
            point_distance(a, c, d), point_distance(b, c, d), point_distance(c, a, b), point_distance(d, a, b)
        )

    parents = list(range(len(copper)))

    def root(i):
        while parents[i] != i:
            parents[i] = parents[parents[i]]
            i = parents[i]
        return i

    for i, (a, b, radius, layer) in enumerate(copper):
        for j, (c, d, other_radius, other_layer) in enumerate(copper[:i]):
            if layer & other_layer and separation(a, b, c, d) < radius + other_radius - 1e-8:
                parents[root(i)] = root(j)

    def terminal(ref, number):
        fp = footprints[ref]
        pad = next(p for p in children(fp, "pad") if str(p[1]) == str(number))
        at, layer = transform(fp, first(pad, "at")[1:3]), first(fp, "layer")[1]
        matches = {
            root(i)
            for i, (a, b, radius, layers) in enumerate(copper)
            if layer in layers and point_distance(at, a, b) <= radius
        }
        assert len(matches) == 1, ("Missing Kelvin terminal copper", ref)
        return matches.pop()

    assert terminal(driver, 2) != terminal(sense, 1), (
        "SET Kelvin sense shunted into drive before regulator land"
    )
    return dict(net=net_name, common_land=[regulator, pad_number], separate_upstream_drive_and_sense=True)


def output_plane_contacts(tree, drc):
    """All power-plane contacts must lie within the same saved native island."""
    planes = [
        z for z in children(tree, "zone") if not children(z, "keepout") and first(z, "layer")[1] == "In4.Cu"
    ]
    assert len(planes) == 1 and str(first(planes[0], "net")[-1]) == "/V5_REG_SRC", (
        "Missing analog output plane"
    )
    polygons = children(planes[0], "filled_polygon")
    assert len(polygons) == 1, "Analog output plane is not one connected filled island"
    polygon = [tuple(map(float, p[1:3])) for p in children(first(polygons[0], "pts"), "xy")]

    def inside(point):
        x, y = point
        result = False
        for (ax, ay), (bx, by) in zip(polygon, polygon[1:] + polygon[:1]):
            if (ay > y) != (by > y) and x < (bx - ax) * (y - ay) / (by - ay) + ax:
                result = not result
        return result

    vias = [v for v in children(tree, "via") if str(first(v, "net")[-1]) == "/V5_REG_SRC"]
    assert len(vias) == 4, "Missing analog output/bleed power via"
    contacts = [(tuple(map(float, first(v, "at")[1:3])), 0.22) for v in vias]
    header = next(
        f
        for f in children(tree, "footprint")
        if any(p[1:3] == ["Reference", "J2"] for p in children(f, "property"))
    )
    pad = next(p for p in children(header, "pad") if str(p[1]) == "6")
    assert first(pad, "net")[-1] == "/V5_REG_SRC"
    contacts.append((transform(header, first(pad, "at")[1:3]), 0.65))
    for (x, y), radius in contacts:
        for dx, dy in ((radius, 0), (-radius, 0), (0, radius), (0, -radius)):
            assert inside((x + dx, y + dy)), ("Analog output plane contact disconnected", x, y)
    assert not any("V5_REG_SRC" in str(item) for item in drc["unconnected_items"]), (
        "Analog output still has native open connections"
    )
    return dict(
        layer="In4.Cu",
        net="V5_REG_SRC",
        filled_connected_islands=1,
        source_and_bleed_vias=4,
        header=["J2", 6],
        all_contact_annuli_in_same_island=True,
        resistance_or_ampacity_qualified=False,
    )
