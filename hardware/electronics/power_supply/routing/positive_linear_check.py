"""Positive linear stage path, face and independent SET feedback requirements."""

from ...common.sexpr import children, first
from .analog_5v_check import kelvin_separation

F = ("F.Cu",)
B = ("B.Cu",)
ALL = ("F.Cu", "B.Cu", "In1.Cu", "In2.Cu", "In3.Cu", "In4.Cu")
QUIET = ("F.Cu", "B.Cu", "In2.Cu", "In3.Cu", "In4.Cu")
PATHS = []
MINIMUM_WIDTHS = {}


def path(name, net, start, end, limit, layers=ALL, width=0.26):
    PATHS.append((name, net, start, end, limit, layers))
    MINIMUM_WIDTHS[name] = width


for (
    prefix,
    reg,
    amp_out,
    amp_inv,
    comp,
    iso,
    upper,
    middle,
    lower,
    setcap,
    raw,
    incap,
    outcap,
    hfcap,
    bleed,
    header,
    input_pin,
    ctrl_pin,
    out_pin,
) in [
    (
        "p19",
        "U7",
        1,
        2,
        "C34",
        "R23",
        "R20",
        "R21",
        "R22",
        "C35",
        "RAW_P22",
        "C36",
        "C37",
        "C38",
        "R24",
        1,
        7,
        5,
        1,
    ),
    (
        "p12",
        "U8",
        7,
        6,
        "C39",
        "R28",
        "R25",
        "R26",
        "R27",
        "C40",
        "RAW_P17",
        "C41",
        "C42",
        "C43",
        "R29",
        4,
        4,
        5,
        3,
    ),
]:
    rail = prefix.upper()
    set_pin = 4 if reg == "U7" else 2
    power_ground = ("U1", 11) if reg == "U7" else ("U13", 11)
    path(prefix + "_local_comp_out", rail + "_DRIVE", ("U5", amp_out), (comp, 1), 7)
    path(prefix + "_local_comp_inv", rail + "_FB", ("U5", amp_inv), (comp, 2), 15 if reg == "U7" else 7)
    path(prefix + "_isolation_drive", rail + "_DRIVE", ("U5", amp_out), (iso, 1), 30)
    path(prefix + "_set_drive", rail + "_SET", (iso, 2), (reg, set_pin), 45)
    path(prefix + "_set_kelvin", rail + "_SET", (upper, 1), (reg, set_pin), 30)
    path(prefix + "_divider_middle", rail + "_RMID", (upper, 2), (middle, 1), 7, B)
    path(prefix + "_divider_lower", rail + "_FB", (middle, 2), (lower, 1), 18)
    path(prefix + "_feedback_inv", rail + "_FB", (middle, 2), ("U5", amp_inv), 35)
    path(prefix + "_divider_star_ground", "AGND", (lower, 2), ("J2", 2), 105, QUIET)
    path(prefix + "_set_filter", rail + "_SET", (reg, set_pin), (setcap, 1), 45)
    path(prefix + "_set_filter_ground", "AGND", (setcap, 2), ("J2", 2), 110, QUIET)
    path(prefix + "_input_bypass", raw, (incap, 1), (reg, input_pin), 15 if reg == "U7" else 10, ALL, 0.5)
    path(prefix + "_control_bypass", raw, (incap, 1), (reg, ctrl_pin), 15, ALL, 0.35 if reg == "U7" else 0.5)
    path(
        prefix + "_source_header",
        rail + "_SRC",
        (reg, out_pin),
        ("J2", header),
        80,
        ALL,
        0.8 if reg == "U7" else 1.2,
    )
    path(prefix + "_output_bulk", rail + "_SRC", (outcap, 1), (reg, out_pin), 40, ALL, 0.5)
    path(prefix + "_output_hf", rail + "_SRC", (hfcap, 1), (reg, out_pin), 40, ALL, 0.5)
    path(prefix + "_minimum_load", rail + "_SRC", (bleed, 1), (reg, out_pin), 100)
    path(prefix + "_minimum_load_ground", "AGND", (bleed, 2), power_ground, 135)
    path(prefix + "_input_ground", "AGND", (incap, 2), power_ground, 140, ALL, 0.5)
    path(prefix + "_output_bulk_ground", "AGND", (outcap, 2), power_ground, 125, ALL, 0.5)
    path(prefix + "_output_hf_ground", "AGND", (hfcap, 2), power_ground, 140, ALL, 0.5)
path("p19_input_source", "RAW_P22", ("C5", 1), ("U7", 7), 65, ALL, 0.5)
path("p12_input_source", "RAW_P17", ("C64", 1), ("U8", 4), 65, ALL, 0.5)
for n in (2, 3):
    path("p19_output_lead_" + str(n), "P19_SRC", ("U7", n), ("U7", 9), 5, F, 0.5)
path("p19_output_tab", "P19_SRC", ("U7", 1), ("U7", 9), 6, F, 0.5)
path("p19_input_pair", "RAW_P22", ("U7", 7), ("U7", 8), 2, F, 0.5)
path("p12_input_pair", "RAW_P17", ("U8", 4), ("U8", 5), 2, F, 0.5)


path("p12_output_tab", "P12_SRC", ("U8", (3, 0)), ("U8", (3, 1)), 14, F, 1.2)


def component_faces(tree):
    front = {"U7", "U8", "C39", "C41"}
    back = {
        "R20",
        "R21",
        "R22",
        "R23",
        "R24",
        "C34",
        "C35",
        "C36",
        "C37",
        "C38",
        "R25",
        "R26",
        "R27",
        "R28",
        "R29",
        "C40",
        "C42",
        "C43",
    }
    found = {}
    for fp in children(tree, "footprint"):
        ref = next(p[2] for p in children(fp, "property") if p[1] == "Reference")
        if ref in front | back:
            assert first(fp, "layer")[1] == ("F.Cu" if ref in front else "B.Cu"), (
                ref,
                "positive linear stage component face changed",
            )
            found[ref] = first(fp, "layer")[1]
    assert set(found) == front | back
    return found


def set_kelvin(tree):
    return {
        "P19": kelvin_separation(tree, "U7", 4, "P19_SET", "R23", "R20"),
        "P12": kelvin_separation(tree, "U8", 2, "P12_SET", "R28", "R25"),
    }


def output_planes(tree, drc):
    result = {}
    for net, points in [
        ("P19_SRC", [(112.5, 134), (113.25, 134), (114, 134)]),
        ("P12_SRC", [(153.5, 132), (153.5, 133), (153.5, 134)]),
    ]:
        zones = [
            z
            for z in children(tree, "zone")
            if not children(z, "keepout")
            and first(z, "layer")[1] == "B.Cu"
            and str(first(z, "net")[-1]) == "/" + net
        ]
        assert len(zones) == 1, ("Missing positive output spreader", net)
        polygons = [
            [tuple(map(float, p[1:3])) for p in children(first(f, "pts"), "xy")]
            for f in children(zones[0], "filled_polygon")
        ]

        def inside(poly, x, y):
            answer = False
            for (a, b), (c, d) in zip(poly, poly[1:] + poly[:1]):
                if (b > y) != (d > y) and x < (c - a) * (y - b) / (d - b) + a:
                    answer = not answer
            return answer

        assert any(
            all(
                inside(poly, x + dx, y + dy)
                for x, y in points
                for dx, dy in ((0.22, 0), (-0.22, 0), (0, 0.22), (0, -0.22))
            )
            for poly in polygons
        ), ("Positive output thermal vias are not in one filled region", net)
        prefix = net.split("_")[0] + "_"
        assert not any(prefix in str(item) for item in drc["unconnected_items"]), (
            "Positive linear stage has native open connections",
            prefix,
        )
        result[net] = dict(
            layer="B.Cu",
            thermal_vias_in_one_region=3,
            stage_native_open_items=0,
            thermal_or_ampacity_qualified=False,
        )
    return result
