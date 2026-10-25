"""Negative regulator power routing candidate; powered qualification remains open."""

from ...common.sexpr import read_sexpr

MOVES = {}
N19_THERMAL = ((26.75, 26.7), (27.5, 26.7), (28.25, 26.7))
N12_THERMAL = ((57.5, 20.75), (58.25, 20.75), (59, 20.75))


def route(r):
    p = r.p
    for reg, raw, face, bank in (("U10", "RAW_N22", "B", N19_THERMAL), ("U11", "RAW_N17", "F", N12_THERMAL)):
        r.path(raw, face, p(reg, 8), p(reg, 9), p(reg, 10), width=0.35)
        r.path(raw, face, p(reg, 9), (p(reg, 11)[0], p(reg, 9)[1]), p(reg, 11), width=0.5)
        for at in bank:
            r.via(raw, at)
        r.path(raw, face, p(reg, 11), bank[0] if reg == "U11" else bank[1], width=0.8)
        r.path(raw, face, *bank, width=0.8)
    r.path("RAW_N22", "F", (27.5, 23), (27.5, 26.7), width=0.8)
    r.path(
        "AGND", "B", p("U10", 3), (25.625, 28.65), (25.25, 28.65), (25.25, 29.4), (25.125, 29.4), width=0.15
    )
    r.via("AGND", (25.125, 29.4))
    r.path("AGND", "F", p("U11", 3), (55.625, 16.85), (55.25, 16.85), (54.8, 16.5), width=0.15)
    r.path("AGND", "B", p("C56", 2), (52.5, 16.5), width=0.5)
    r.path("N19_SRC", "B", p("U10", 2), p("U10", 1), width=0.35)
    r.path("N12_SRC", "F", p("U11", 2), p("U11", 1), width=0.35)
    r.path("N12_SRC", "F", p("U11", 1), (55.2, 15.6), (54.6, 15.6), width=0.5)
    r.via("N12_SRC", (54.6, 15.6))
    r.path("5V_DIG_SRC", "B", p("U10", 5), (25.6, 27.5), (25.6, 26.8), width=0.15)
    r.via("5V_DIG_SRC", (25.6, 26.8))
    r.path("5V_DIG_SRC", "F", p("U11", 5), (56.05, 20.5), width=0.2)
    r.via("5V_DIG_SRC", (56.05, 20.5))


def route_distribution(r):
    from . import power_grid
    from .analog_5v import QUIET_PAD as film
    from .analog_5v import QUIET_VIAS as analog
    from .negative_reference import QUIET_PAD as nfilm
    from .negative_reference import QUIET_VIAS as nref
    from .positive_linear import QUIET_VIAS as positive
    from .pre_buck import QUIET_VIAS as pre
    from .raw_17 import QUIET_VIAS as raw
    from .raw_22 import QUIET_VIAS as high

    saved = dict(r.connected_points)
    r.connected_points = {}

    def layers():
        for g in r.geometry:
            if g["kind"] == "circle" and len(g["layers"]) > 1:
                g["layers"] = list(power_grid.ALL_LAYERS)

    def connect(net, points, width, active=("In2.Cu", "In3.Cu")):
        r.route_width[net] = width
        power_grid.connect(r, {net: points}, (90, 44), routing_layers=active)
        layers()

    def escape(net, at, width, face):
        r.route_width[net] = width
        power_grid.connect(r, {net: [at]}, (90, 44), escape=True, routing_layers=(face,))
        layers()
        return r.escape_points[(net, at)]

    layers()
    output_layers = ("In2.Cu", "In3.Cu", "In4.Cu", "F.Cu", "B.Cu", "In1.Cu")
    # Keep the power returns away from reference-return vias before J2.
    guards = []
    quiet = (
        (65, 4.75),
        (58, 15.2),
        *analog,
        *nref,
        *positive,
        *pre,
        *raw,
        *high,
        film,
        nfilm,
        *[at for net, at in r.vias if net == "NEG_TARGET_RETURN_ROUTE"],
    )
    for at in quiet:
        g = dict(
            kind="circle",
            net="POWER_QUIET_RETURN_GUARD",
            layers=list(power_grid.ALL_LAYERS),
            x=at[0],
            y=at[1],
            r=0.75 if at in (film, nfilm) else 0.3,
        )
        r.geometry.append(g)
        guards.append(g)
    for old in list(r.geometry):
        if (
            old["net"] == "AGND"
            and old["kind"] == "line"
            and set(old["layers"]) & {"In2.Cu", "In3.Cu", "In4.Cu"}
        ):
            guard = dict(old, net="POWER_QUIET_RETURN_GUARD")
            r.geometry.append(guard)
            guards.append(guard)
    grounds = [(20, 27.9), (25.125, 29.4)]
    for ref in ("C51", "C52", "C53", "C57", "C58", "R38", "R43"):
        grounds.append(escape("AGND", r.p(ref, 2), 0.5 if ref.startswith("C") else 0.26, "B.Cu"))
    connect("AGND", grounds, 0.5, ("In1.Cu",))
    for g in guards:
        r.geometry.remove(g)
    n19 = escape("N19_SRC", r.p("U10", 1), 0.8, "B.Cu")
    for net, root, pin, caps, bleed in (
        ("N12_SRC", (54.6, 15.6), 5, ("C57", "C58"), "R43"),
        ("N19_SRC", n19, 3, ("C52", "C53"), "R38"),
    ):
        connect(net, [root, r.p("J2", pin)], 0.5 if net == "N12_SRC" else 0.8, output_layers)
        for cap in caps:
            at = escape(net, r.p(cap, 1), 0.5, "B.Cu")
            connect(net, [at], 0.5, output_layers)
        at = escape(net, r.p(bleed, 1), 0.26, "B.Cu")
        connect(net, [at], 0.26, output_layers)
    at = escape("RAW_N22", r.p("C51", 1), 0.5, "B.Cu")
    connect("RAW_N22", [(26.2, 13.8), at], 0.5, output_layers)
    connect("RAW_N17", [(54.6, 17.9), (57.5, 20.75)], 0.8, output_layers)
    connect("5V_DIG_SRC", [r.p("J3", 1), (25.6, 26.8), (56.05, 20.5)], 0.26, output_layers)
    for net, root, pin in (
        ("RAW_P22", (29.2, 6), 1),
        ("RAW_N22", (27.5, 26.7), 3),
        ("RAW_P17", (36.5, 24.5), 4),
        ("RAW_N17", (57.5, 20.75), 5),
    ):
        r.connected_points.pop(net, None)
        connect(net, [root, r.p("J4", pin)], 0.5, output_layers)
    r.connected_points = {**saved, **r.connected_points}


def add_input_planes(board, nets):
    for net, layer, bounds in (
        ("RAW_N22", "F.Cu", (25.5, 25.8, 29.5, 29)),
        ("RAW_N17", "F.Cu", (51, 15.6, 60, 24)),
        ("RAW_N17", "B.Cu", (54.5, 14, 67, 23.8)),
    ):
        x, y, xx, yy = [100 + v for v in bounds]
        board.append(
            read_sexpr(f'''(zone (net {nets[net]}) (net_name "/{net}") (layer "{layer}") (hatch edge .5)
        (connect_pads yes (clearance .15)) (min_thickness .15) (fill yes (thermal_gap .2) (thermal_bridge_width .3))
        (polygon (pts (xy {x} {y}) (xy {xx} {y}) (xy {xx} {yy}) (xy {x} {yy}))))''')
        )


def remove_redundant_vias(r):
    """Drop output escape drills when the finished branch stayed on one face."""
    import math

    from ...common.sexpr import children, first

    def point_segment_distance(p, a, b):
        dx, dy = b[0] - a[0], b[1] - a[1]
        t = max(0, min(1, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / (dx * dx + dy * dy)))
        return math.dist(p, (a[0] + t * dx, a[1] + t * dy))

    for via in list(children(r.board, "via")):
        if str(first(via, "net")[1]) not in {str(r.nets[n]) for n in ("N19_SRC", "N12_SRC")}:
            continue
        at = tuple(map(float, first(via, "at")[1:3]))
        net = str(first(via, "net")[1])
        radius = float(first(via, "size")[1]) / 2
        touched = {
            str(first(s, "layer")[1])
            for s in children(r.board, "segment")
            if str(first(s, "net")[1]) == net
            and point_segment_distance(
                at, tuple(map(float, first(s, "start")[1:3])), tuple(map(float, first(s, "end")[1:3]))
            )
            <= radius + float(first(s, "width")[1]) / 2 + 1e-7
        }
        if len(touched) == 1:
            r.board.remove(via)
            xy = tuple(v - 100 for v in at)
            r.vias[:] = [(n, p) for n, p in r.vias if not (str(r.nets[n]) == net and math.dist(p, xy) < 1e-6)]
    r.counts["vias"] = len(children(r.board, "via"))
