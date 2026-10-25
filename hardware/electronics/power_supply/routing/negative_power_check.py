"""Independent contracts for negative power, SHDN and raw-rail test feeds."""

from ...common.sexpr import children, first

ALL = ("F.Cu", "B.Cu", "In1.Cu", "In2.Cu", "In3.Cu", "In4.Cu")
PATHS = []
MINIMUM_WIDTHS = {}


def path(name, net, start, end, limit, width, layers=ALL):
    PATHS.append((name, net, start, end, limit, layers))
    MINIMUM_WIDTHS[name] = width


for prefix, reg, raw, cap, bulk, hf, bleed, pin, width in (
    ("n19", "U10", "RAW_N22", "C51", "C52", "C53", "R38", 3, 0.8),
    ("n12", "U11", "RAW_N17", "C56", "C57", "C58", "R43", 5, 0.5),
):
    rail = prefix.upper() + "_SRC"
    face = ("B.Cu",) if reg == "U10" else ("F.Cu",)
    path(prefix + "_current_limit", raw, (reg, 8), (reg, 9), 2, 0.35, face)
    path(prefix + "_input_pair", raw, (reg, 9), (reg, 10), 2, 0.35, face)
    path(prefix + "_input_ep", raw, (reg, 9), (reg, 11), 3, 0.5, face)
    path(prefix + "_input_bulk", raw, (cap, 1), (reg, 11), 100, 0.5)
    path(prefix + "_output_pair", rail, (reg, 2), (reg, 1), 2, 0.35, face)
    path(prefix + "_load_header", rail, (reg, 1), ("J2", pin), 120, width)
    path(prefix + "_output_bulk", rail, (reg, 1), (bulk, 1), 100, 0.5)
    path(prefix + "_output_hf", rail, (reg, 1), (hf, 1), 100, 0.5)
    path(prefix + "_output_bleed", rail, (reg, 1), (bleed, 1), 180, 0.26)
    path(prefix + "_shutdown", "5V_DIG_SRC", (reg, 5), ("J3", 1), 200, 0.15 if reg == "U10" else 0.2)
    path(prefix + "_power_ground", "AGND", (reg, 3), ("U13", 11), 160, 0.15)
    for ref in (bulk, hf, bleed):
        path(
            prefix + "_" + ref.lower() + "_return",
            "AGND",
            (ref, 2),
            ("U13", 11),
            180,
            0.5 if ref.startswith("C") else 0.26,
        )
path("n19_input_return", "AGND", ("C51", 2), ("U13", 11), 160, 0.5)
path("n12_input_return", "AGND", ("C56", 2), ("C69", 2), 6, 0.5, ("B.Cu",))
for name, net, start, pin in (
    ("p22", "RAW_P22", ("@via", (29.2, 6, "In2.Cu")), 1),
    ("n22", "RAW_N22", ("@via", (27.5, 26.7, "In2.Cu")), 3),
    ("p17", "RAW_P17", ("@via", (36.5, 24.5, "In2.Cu")), 4),
    ("n17", "RAW_N17", ("@via", (57.5, 20.75, "In2.Cu")), 5),
):
    path("raw_" + name + "_test", net, start, ("J4", pin), 200, 0.5)


def native_connections(drc):
    assert not drc["unconnected_items"], "Supply connectivity is incomplete"
    return dict(native_open_items=0, regulator_power_and_output_complete=True, powered_qualification=False)


def dc_route_estimates(paths):
    # An explicit geometry estimate, not a copper stackup/temperature approval.
    result = {}
    for name, current, budget in (("n19", 0.05, 0.03), ("n12", 0.15, 0.03)):
        p = paths[name + "_load_header"]
        width = MINIMUM_WIDTHS[name + "_load_header"]
        resistance = 1.8e-8 * (p["length_mm"] / 1000) / (width / 1000 * 35e-6)
        drop = resistance * current
        assert drop <= budget, (name, "provisional trace-only DC-drop budget exceeded", drop)
        result[name] = dict(
            path_length_mm=p["length_mm"],
            minimum_width_mm=width,
            current_a=current,
            assumed_copper_thickness_um=35,
            assumed_resistivity_ohm_m=1.8e-8,
            trace_resistance_upper_estimate_ohm=resistance,
            trace_drop_estimate_v=drop,
            trace_drop_budget_v=budget,
            includes_vias_connectors_or_temperature=False,
            fabricated_stackup_or_ampacity_qualified=False,
        )
    return result


def input_planes(tree):
    """The real three-via banks must share a filled region on each spreader."""
    N19_THERMAL = ((26.75, 26.7), (27.5, 26.7), (28.25, 26.7))
    N12_THERMAL = ((57.5, 20.75), (58.25, 20.75), (59, 20.75))
    result = {}

    def inside(poly, x, y):
        answer = False
        for (a, b), (c, d) in zip(poly, poly[1:] + poly[:1]):
            if (b > y) != (d > y) and x < (c - a) * (y - b) / (d - b) + a:
                answer = not answer
        return answer

    for net, layer, bank in (
        ("RAW_N22", "F.Cu", N19_THERMAL),
        ("RAW_N17", "F.Cu", N12_THERMAL),
        ("RAW_N17", "B.Cu", N12_THERMAL),
    ):
        actual_vias = {
            tuple(map(float, first(v, "at")[1:3]))
            for v in children(tree, "via")
            if str(first(v, "net")[-1]).lstrip("/") == net
            and list(first(v, "layers")[1:]) == ["F.Cu", "B.Cu"]
        }
        assert all((100 + x, 100 + y) in actual_vias for x, y in bank), (
            "missing negative input thermal via",
            net,
        )
        zones = [
            z
            for z in children(tree, "zone")
            if not children(z, "keepout")
            and first(z, "layer")[1] == layer
            and str(first(z, "net")[-1]) == "/" + net
        ]
        assert len(zones) == 1, ("missing negative input spreader", net, layer)
        polygons = [
            [tuple(map(float, p[1:3])) for p in children(first(f, "pts"), "xy")]
            for f in children(zones[0], "filled_polygon")
        ]
        assert any(
            all(
                inside(poly, 100 + x + dx, 100 + y + dy)
                for x, y in bank
                for dx, dy in ((0.22, 0), (-0.22, 0), (0, 0.22), (0, -0.22))
            )
            for poly in polygons
        ), ("negative input vias split across filled regions", net, layer)
        result[net + ":" + layer] = dict(thermal_vias_in_one_region=3, thermal_or_ampacity_qualified=False)
    return result
