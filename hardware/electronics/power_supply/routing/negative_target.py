"""Negative SET drive/sense routing; DC loss and loop qualification remain open."""

ALIASES = {
    "N19_SET_DRIVE_ROUTE": "N19_SET",
    "N19_SET_SENSE_ROUTE": "N19_SET",
    "N12_SET_DRIVE_ROUTE": "N12_SET",
    "N12_SET_SENSE_ROUTE": "N12_SET",
    "NEG_TARGET_RETURN_ROUTE": "AGND",
}
MOVES = {"R37": (37.3, 21.1, 0, "B"), "R42": (39.2, 23, 0, "B")}


def route(r):
    # Routing-only names share the real schematic net number. They never add
    # board nets; their separate obstacle masks prevent a premature SET shunt.
    for alias, actual in ALIASES.items():
        r.nets[alias] = r.nets[actual]
    p = r.p
    r.path("N19_DRIVE", "B", p("C49", 1), (36.525, 21.1), p("R37", 1), width=0.26)
    r.path(
        "N12_DRIVE",
        "B",
        p("C54", 1),
        (40.8, 20.7),
        (40.8, 21.95),
        (39.2, 21.95),
        (39.2, 22.15),
        (38.2875, 22.15),
        p("R42", 1),
        width=0.26,
    )
    for net, at in (
        ("N19_SET_DRIVE_ROUTE", (24.7, 26.8)),
        ("N19_SET_SENSE_ROUTE", (24.75, 28.4)),
    ):
        r.via(net, at)
    # Separate 0.15 mm necks leave opposite corners of each 0.25 mm SET land.
    # The adjacent GND/SHDN lands retain their required copper clearance.
    r.path("N19_SET_DRIVE_ROUTE", "B", p("U10", 4), (25.625, 27.85), (25.25, 27.85), (24.7, 26.8), width=0.15)
    r.path(
        "N19_SET_SENSE_ROUTE", "B", p("U10", 4), (25.625, 28.15), (25.25, 28.15), (24.75, 28.4), width=0.15
    )
    r.path("N12_SET_DRIVE_ROUTE", "F", p("U11", 4), (55.625, 17.35), (55.25, 17.35), (54.9, 17.1), width=0.15)
    r.path(
        "N12_SET_SENSE_ROUTE", "F", p("U11", 4), (55.625, 17.65), (55.25, 17.65), (55.25, 18.3), width=0.15
    )


def route_distribution(r):
    from . import power_grid

    saved = dict(r.connected_points)
    r.connected_points = {}

    def via_layers():
        for shape in r.geometry:
            if shape["kind"] == "circle" and len(shape["layers"]) > 1:
                shape["layers"] = list(power_grid.ALL_LAYERS)

    def rename_pad(ref, pin, net):
        at = r.p(ref, pin)
        found = [
            g
            for g in r.geometry
            if g["kind"] == "rect" and abs(g["x"] - at[0]) < 1e-6 and abs(g["y"] - at[1]) < 1e-6
        ]
        assert len(found) == 1, (ref, pin, "ambiguous route-mask pad")
        found[0]["net"] = net

    def escape(net, endpoints, face="B.Cu"):
        r.route_width[net] = 0.26
        power_grid.connect(r, {net: endpoints}, (90, 44), escape=True, routing_layers=(face,))
        via_layers()
        return [r.escape_points[(net, at)] for at in endpoints]

    def connect(net, endpoints, roots=()):
        points = [*roots, *escape(net, endpoints)]
        r.connected_points.pop(net, None)
        power_grid.connect(
            r,
            {net: points},
            (90, 44),
            routing_layers=("In2.Cu", "In3.Cu", "In4.Cu")
            if net == "N19_SET_SENSE_ROUTE"
            else ("In2.Cu", "In3.Cu"),
        )
        via_layers()

    for net, pads, roots in (
        ("N19_FB", (("U6", 2), ("R35", 2)), ()),
        ("N12_FB", (("R40", 2), ("R41", 1)), ((43.2, 14),)),
    ):
        connect(net, [r.p(*pad) for pad in pads], roots)
    f_esc = {
        "N12_SET_DRIVE_ROUTE": escape("N12_SET_DRIVE_ROUTE", [(54.9, 17.1)], "F.Cu")[0],
        "N12_SET_SENSE_ROUTE": escape("N12_SET_SENSE_ROUTE", [(55.25, 18.3)], "F.Cu")[0],
    }
    for alias, pads, root in (
        ("N19_SET_DRIVE_ROUTE", (("R37", 2), ("C50", 1)), (24.7, 26.8)),
        ("N19_SET_SENSE_ROUTE", (("R34", 1),), (24.75, 28.4)),
        ("N12_SET_DRIVE_ROUTE", (("R42", 2), ("C55", 1)), f_esc["N12_SET_DRIVE_ROUTE"]),
        ("N12_SET_SENSE_ROUTE", (("R39", 1),), f_esc["N12_SET_SENSE_ROUTE"]),
    ):
        for pad in pads:
            rename_pad(*pad, alias)
        connect(alias, [r.p(*pad) for pad in pads], [root])
    return_net = "NEG_TARGET_RETURN_ROUTE"
    grounds = [("R36", 2), ("C50", 2), ("R41", 2), ("C55", 2)]
    for pad in grounds:
        rename_pad(*pad, return_net)
    # Reuse the already verified output-reference domain, while power-ground
    # copper remains a foreign obstacle. This graph is a routing aid; the
    # independent checker audits actual copper intersections after generation.
    from ...common.sexpr import children, first
    from ...output_stage.check_placement import transform

    graph = {}

    def edge(a, b):
        graph.setdefault(a, set()).add(b)
        graph.setdefault(b, set()).add(a)

    def node(point, layer):
        return (round(point[0], 6), round(point[1], 6), layer)

    for shape in r.geometry:
        if shape["net"] != "AGND":
            continue
        if shape["kind"] == "line":
            layer = shape["layers"][0]
            edge(node(shape["start"], layer), node(shape["end"], layer))
        elif shape["kind"] == "circle" and len(shape["layers"]) > 1:
            at = (shape["x"], shape["y"])
            for layer in shape["layers"]:
                edge(node(at, "B.Cu"), node(at, layer))
    for fp in children(r.board, "footprint"):
        for pad in children(fp, "pad"):
            if pad[2] == "thru_hole" and children(pad, "net") and first(pad, "net")[-1] == "/AGND":
                at = transform(fp, first(pad, "at")[1:3])
                at = (at[0] - 100, at[1] - 100)
                for layer in power_grid.ALL_LAYERS:
                    edge(node(at, "B.Cu"), node(at, layer))
    root = (18.25, 20.125)
    reached = {node(root, "In3.Cu")}
    pending = list(reached)
    while pending:
        for other in graph.get(pending.pop(), ()):
            if other not in reached:
                reached.add(other)
                pending.append(other)
    for shape in r.geometry:
        if shape["net"] != "AGND":
            continue
        if shape["kind"] == "line":
            belongs = node(shape["start"], shape["layers"][0]) in reached
        else:
            belongs = any(node((shape["x"], shape["y"]), layer) in reached for layer in shape["layers"])
        if belongs:
            shape["net"] = return_net
    points = escape(return_net, [r.p(*pad) for pad in grounds])
    r.connected_points[return_net] = [root, (25.2, 22.9), (13.6, 6.8), r.p("J2", 2)]
    guards = []
    for shape in list(r.geometry):
        if (
            shape["net"] == return_net
            and shape["kind"] == "circle"
            and len(shape["layers"]) > 1
            and (shape["x"], shape["y"]) not in points
        ):
            guard = dict(shape, net="EXISTING_QUIET_LAYER_GUARD", layers=["In2.Cu"])
            r.geometry.append(guard)
            guards.append(guard)
    old_endpoints = dict(getattr(r, "endpoint_layers", {}))
    r.endpoint_layers = {
        **old_endpoints,
        **{(return_net, point): ("In3.Cu",) for point in (root, (25.2, 22.9), (13.6, 6.8))},
    }
    power_grid.connect(r, {return_net: points}, (90, 44), routing_layers=("In2.Cu", "In3.Cu"))
    r.endpoint_layers = old_endpoints
    for guard in guards:
        r.geometry.remove(guard)
    via_layers()
    print("Negative target quiet vias:", [at for net, at in r.vias if net == return_net], flush=True)
    r.connected_points = {**saved, **r.connected_points}
