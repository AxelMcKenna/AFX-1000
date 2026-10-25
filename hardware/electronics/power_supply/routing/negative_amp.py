"""Negative target amplifier local supply/compensation; loop qualification open."""

MOVES = {
    "C61": (44, 17.7, 0, "B"),
    "C49": (38, 18.5, 0, "B"),
    "C54": (43.3, 20.7, 0, "B"),
    "R34": (32.5, 17, 180, "B"),
}


def route(r):
    p = r.p
    # The OPA2192 uses AGND/RAW_N22, not the full bipolar 44 V span.
    r.path("RAW_N22", "B", p("U6", 4), (42.5, 12.095), (42.5, 16), (42.5, 17.7), p("C61", 1), width=0.35)
    r.path("AGND", "B", p("U6", 8), (46.4, 15.905), (46.4, 17.7), p("C61", 2), width=0.35)
    r.path("AGND", "B", (46.4, 17.7), (46.4, 18.75), (46.5, 18.75), width=0.35)
    r.via("AGND", (46.5, 18.75))
    for at in ((43, 16), (38, 11.45)):
        r.via("RAW_N22", at)
    for at in ((43.2, 14), (47.125, 19.375)):
        r.via("N12_FB", at)
    r.path("RAW_N22", "B", (42.5, 16), (43, 16), width=0.35)
    r.path("RAW_N22", "B", p("C62", 1), (36.25, 11.45), (38, 11.45), width=0.35)
    # The larger supply capacitor has its own power-ground escape.
    r.via("AGND", (34.9, 7.55))
    r.path("AGND", "B", p("C62", 2), (34.9, 7.55), width=0.35)
    # Local HF feedback closes before each series SET-drive resistor.
    r.path("N19_DRIVE", "B", p("U6", 1), (40.525, 16.2), (38.4, 16.2), (38.4, 18.5), p("C49", 1), width=0.26)
    r.path("N19_FB", "B", p("U6", 2), (41.9, 14.635), (41.9, 17), (39.475, 17), p("C49", 2), width=0.26)
    r.path("N12_DRIVE", "B", p("U6", 7), (44, 14.635), (44, 18.8), (41.825, 18.8), p("C54", 1), width=0.26)
    r.path("N12_FB", "B", p("U6", 6), (43.2, 13.365), (43.2, 14), width=0.26)
    r.path("N12_FB", "B", p("C54", 2), (44.775, 20.2), (47.125, 20.2), (47.125, 19.375), width=0.26)
    # Orient the N19 upper divider so the midpoint is a short direct link.
    r.path("N19_RMID", "B", p("R34", 2), p("R35", 1), width=0.26)
    r.path("N19_FB", "B", p("R35", 2), p("R36", 1), width=0.26)
    r.path("N12_RMID", "B", p("R39", 2), (66.9, 10.8), (66.9, 12.6), p("R40", 1), width=0.26)


def route_distribution(r):
    from . import power_grid

    saved = dict(r.connected_points)
    r.connected_points = {}
    r.route_width["RAW_N22"] = 0.35
    points = [(26.2, 13.8), (43, 16), (38, 11.45)]
    power_grid.connect(r, {"RAW_N22": points}, (90, 44), routing_layers=("In2.Cu", "In3.Cu"))
    r.route_width["N12_FB"] = 0.26
    power_grid.connect(
        r, {"N12_FB": [(43.2, 14), (47.125, 19.375)]}, (90, 44), routing_layers=("In2.Cu", "In3.Cu")
    )
    from .analog_5v import QUIET_PAD as film
    from .analog_5v import QUIET_VIAS as analog
    from .negative_reference import QUIET_PAD as nfilm
    from .negative_reference import QUIET_VIAS as nref
    from .positive_linear import QUIET_VIAS as positive
    from .pre_buck import QUIET_VIAS as pre
    from .raw_17 import QUIET_VIAS as raw
    from .raw_22 import QUIET_VIAS as high

    guards = []
    for at in ((65, 4.75), (58, 15.2), *analog, *nref, *positive, *pre, *raw, *high, film, nfilm):
        shape = dict(
            kind="circle",
            net="QUIET_RETURN_GUARD",
            layers=["In1.Cu"],
            x=at[0],
            y=at[1],
            r=0.75 if at in (film, nfilm) else 0.3,
        )
        r.geometry.append(shape)
        guards.append(shape)
    r.route_width["AGND"] = 0.5
    power_grid.connect(
        r, {"AGND": [(47.2, 11.525), (46.5, 18.75), (34.9, 7.55)]}, (90, 44), routing_layers=("In1.Cu",)
    )
    for shape in guards:
        r.geometry.remove(shape)
    r.connected_points = {**saved, **r.connected_points}
