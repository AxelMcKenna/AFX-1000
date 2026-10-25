"""Negative shunt/filter routing candidate; noise and startup remain unqualified."""

QUIET_VIAS = ((18.25, 20.125),)
QUIET_PAD = (6.8, 8.2)


def route(r):
    p = r.p
    # For a negative reference, LT1634 VOUT is AGND and GND/TEST are -2.5 V.
    # Do not connect the other DNC/NC pins. Bias comes from the raw -22 V rail.
    r.path("NREF_2V5", "B", p("U12", 4), (11.8, 16.095), p("U12", 5), width=0.26)
    r.path("NREF_2V5", "B", p("R18", 1), (8.2, 14), (8.2, 16.095), p("U12", 4), width=0.26)
    r.path("NREF_2V5", "B", p("R19", 1), (7, 20.7), (11.8, 20.7), (11.8, 16.095), width=0.26)
    r.path("NREF_FILTER", "B", p("R19", 2), (6.8, 15.5), p("C33", 1), width=0.26)
    # Independent reference return closes at J2 ground; its annuli are isolated
    # from the power-ground plane. The film capacitor has a plated ground land.
    for at in QUIET_VIAS:
        r.via("AGND", at)
    r.path("AGND", "B", p("U12", 6), (16.3, 17.365), (16.3, 19.5), (18.25, 20.125), width=0.26)
    r.path("AGND", "In3", (18.25, 20.125), (18.25, 19.25), (5.5, 19.25), (5.5, 8.2), p("C33", 2), width=0.26)
    r.path("AGND", "In3", p("C33", 2), (8.1, 8.2), (8.1, 4.9), (12.14, 4.9), p("J2", 2), width=0.26)
    # Conventional via escapes, with no drills in the SOIC or resistor lands.
    r.path("RAW_N22", "B", p("R18", 2), (11.9, 14), (11.9, 11.9), (10, 11.9), width=0.26)
    for at in ((36.875, 15.5), (46.5, 9.875)):
        r.via("NREF_FILTER", at)
    r.path("NREF_FILTER", "B", p("U6", 3), (39.1, 13.365), (39.1, 15.5), (36.875, 15.5), width=0.26)
    r.path("NREF_FILTER", "B", p("U6", 5), (46.5, 12.095), (46.5, 9.875), width=0.26)


def route_distribution(r):
    from . import power_grid

    # Positive distribution already supplies complete six-layer pad/via masks.
    saved = dict(r.connected_points)
    r.connected_points = {}
    r.route_width.update({"RAW_N22": 0.26, "NREF_FILTER": 0.26})
    for net, points in {
        "NREF_FILTER": [r.p("C33", 1), (36.875, 15.5), (46.5, 9.875)],
    }.items():
        power_grid.connect(r, {net: points}, (90, 44), routing_layers=("In2.Cu", "In3.Cu"))
        for shape in r.geometry:
            if shape["kind"] == "circle" and len(shape["layers"]) > 1:
                shape["layers"] = list(power_grid.ALL_LAYERS)
    r.connected_points = {**saved, **r.connected_points}
