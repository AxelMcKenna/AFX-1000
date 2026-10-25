"""Positive linear rail routing candidate; electrical/thermal qualification open."""

from ...common.sexpr import read_sexpr

MOVES = {
    "C30": (12.5, 23.1, 0, "B"),
    "C34": (12.5, 26.6, 90, "B"),
    "C39": (17.5, 40, 180, "F"),
    "C41": (33, 40, 270, "F"),
    "C40": (30.1, 36.8, 0, "B"),
    "R24": (4, 40, 0, "B"),
    "R25": (31, 40, 0, "B"),
    "R26": (34.5, 40, 0, "B"),
    "R27": (38, 40, 0, "B"),
    "R29": (43.5, 40, 0, "B"),
    "R28": (16, 40, 0, "B"),
}


QUIET_VIAS = ((1.1, 27.5), (12.8, 38), (30.8, 38.2), (40.3, 40), (13.6, 6.8))
P19_OUT = ((12.5, 34), (13.25, 34), (14, 34))
P12_OUT = ((53.5, 32), (53.5, 33), (53.5, 34))


def route(r):
    p = r.p
    # Local +19 V compensation closes at amplifier OUT/-; isolation follows it.
    r.via("P19_DRIVE", (16, 28))
    r.path("P19_DRIVE", "F", p("U5", 1), (16, 28), width=0.26)
    r.path("P19_DRIVE", "B", (16, 28), p("C34", 1), width=0.26)
    r.via("P19_FB", (16, 30.5))
    r.path("P19_FB", "F", p("U5", 2), (16, 30.5), width=0.26)
    r.path("P19_FB", "B", p("C34", 2), (10.5, 25.125), (10.5, 29.5), (16, 30.5), width=0.26)
    r.via("P19_DRIVE", (5.9, 20))
    r.path("P19_DRIVE", "In4", (16, 28), (16, 20), (5.9, 20), width=0.26)
    r.path("P19_DRIVE", "B", (5.9, 20), p("R23", 1), width=0.26)
    # Distinct drive and sense routes meet only on the LT3080 SET land.
    for at in ((8.8, 22), (8.8, 33.3), (9.7, 26.5), (11.9, 34.7)):
        r.via("P19_SET", at)
    r.path("P19_SET", "B", p("R23", 2), (8.8, 22), width=0.26)
    r.path("P19_SET", "In4", (8.8, 22), (7.8, 22), (7.8, 32.8), (8.8, 33.3), width=0.26)
    r.path("P19_SET", "F", p("U7", 4), (8.8, 32.975), (8.8, 33.3), width=0.26)
    r.path("P19_SET", "B", p("R20", 1), (9.7, 26.5), width=0.26)
    r.path("P19_SET", "In2", (9.7, 26.5), (9.7, 34.7), (11.9, 34.7), width=0.26)
    r.path("P19_SET", "F", p("U7", 4), (10.35, 34.7), (11.9, 34.7), width=0.26)
    r.path("P19_SET", "B", (8.8, 33.3), (8.8, 35.2), (11.55, 35.2), p("C35", 1), width=0.26)
    r.path("P19_RMID", "B", p("R20", 2), (6.25, 24.0875), (6.25, 25.9125), p("R21", 1), width=0.26)
    r.via("P19_FB", (1, 29.4))
    r.path("P19_FB", "B", (1, 29.4), p("R22", 1), width=0.26)
    r.via("P19_FB", (6.6, 23))
    r.path("P19_FB", "B", p("R21", 2), (6.6, 23), width=0.26)
    r.path("P19_FB", "In2", (6.6, 23), (6.6, 29.4), (1, 29.4), width=0.26)
    r.path("P19_FB", "F", (6.6, 23), (6.6, 27.3), (15.4, 27.3), (15.4, 30), (16, 30.5), width=0.26)
    # Precision returns remain separate from reservoir-current returns.
    for at in QUIET_VIAS:
        r.via("AGND", at)
    r.path("AGND", "B", p("R22", 2), (1.1, 27.5), width=0.26)
    r.path("AGND", "In4", (1.1, 27.5), (1.1, 9.6), (13.6, 9.6), (13.6, 6.8), width=0.26)
    r.path("AGND", "In3", (13.6, 6.8), (13.6, 4.7), (12.14, 4.7), p("J2", 2), width=0.26)
    r.path("AGND", "B", p("C35", 2), (12.8, 38), width=0.26)
    r.path("AGND", "In3", (12.8, 38), (8, 38), (8, 27.5), (1.1, 27.5), width=0.26)
    # Full load input and VCONTROL, each with conventional pad escapes.
    for at in ((14.8, 29), (15.2, 33.8)):
        r.via("RAW_P22", at)
    r.path("RAW_P22", "In3", (19.3, 27), (14.8, 27), (14.8, 29), (14.8, 33.8), (15.2, 33.8), width=0.5)
    r.path("RAW_P22", "F", (14.8, 29), p("U7", 8), p("U7", 7), width=0.5)
    r.path("RAW_P22", "F", (15.2, 33.8), p("U7", 5), width=0.35)
    r.path("RAW_P22", "B", (15.2, 33.8), (15.2, 32.9), (18.5, 32.9), p("C36", 1), width=0.5)
    # U7 exposed pad and output leads are OUT, never ground.
    for at in (*P19_OUT, (8.7, 31.5)):
        r.via("P19_SRC", at)
    r.path(
        "P19_SRC",
        "F",
        p("U7", 1),
        p("U7", 2),
        p("U7", 3),
        (12.5, 32.325),
        p("U7", 9),
        (12.5, 34),
        (13.25, 34),
        (14, 34),
        width=0.5,
    )
    r.path("P19_SRC", "F", p("U7", 1), (8.7, 31.025), (8.7, 31.5), width=0.8)
    r.via("P19_SRC", (6, 30.3))
    r.path("P19_SRC", "B", p("C37", 1), (5.7, 28.5), (6, 30.3), width=0.5)
    r.path("P19_SRC", "In2", (6, 30.3), (8.7, 31.5), width=0.5)
    r.path("P19_SRC", "B", p("C38", 1), (14.4, 35.0), (14, 34), width=0.5)
    r.via("P19_SRC", (1.7, 40))
    r.path("P19_SRC", "B", p("R24", 1), (1.7, 40), width=0.26)
    for at in ((20, 27.9), (8.9, 29.9), (19.4, 38)):
        r.via("AGND", at)
    r.path("AGND", "B", p("C36", 2), (20, 27.9), width=0.5)
    r.path("AGND", "In1", (20, 27.9), (21, 27.9), (21, 23), (20, 23), (21.6, 20.8), width=0.8)
    r.path("AGND", "B", p("C37", 2), (8.9, 29.9), width=0.5)
    r.path("AGND", "In1", (8.9, 29.9), (8.7, 24), (16.075, 24), (16.075, 13.3), width=0.8)
    r.path("AGND", "B", p("C38", 2), (16.95, 38.0), (19.4, 38), width=0.5)
    r.path("AGND", "In1", (19.4, 38), (21.6, 38), (21.6, 30), (20, 30), (20, 27.9), width=0.8)
    r.via("AGND", (6.3, 40))
    r.path("AGND", "B", p("R24", 2), (6.3, 40), width=0.26)
    r.path("AGND", "In1", (6.3, 40), (10, 40), (10, 29.9), (8.9, 29.9), width=0.5)

    # +12 V local compensation and post-isolation drive.
    r.path("P12_DRIVE", "F", p("U5", 7), p("C39", 1), (20.7, 40), width=0.26)
    r.path("P12_FB", "F", p("U5", 6), (16, 35.64), (16, 38.5), p("C39", 2), width=0.26)
    for at in ((20.7, 40), (13.4, 40)):
        r.via("P12_DRIVE", at)
    r.path("P12_DRIVE", "In2", (20.7, 40), (13.4, 40), width=0.26)
    r.path("P12_DRIVE", "B", (13.4, 40), p("R28", 1), width=0.26)
    for at in ((18.3, 42), (32.2, 28.3), (28.7, 40), (32.5, 30.8), (28, 38.2)):
        r.via("P12_SET", at)
    r.path("P12_SET", "B", p("R28", 2), (18.3, 40), (18.3, 42), width=0.26)
    r.path(
        "P12_SET", "In4", (18.3, 42), (18.3, 42), (28, 42), (33.3, 42), (33.3, 28.3), (32.2, 28.3), width=0.26
    )
    r.path("P12_SET", "F", p("U8", 2), (32.7, 30), (32.7, 29.2), (32.2, 28.3), width=0.26)
    r.path("P12_SET", "B", p("R25", 1), (28.7, 40), width=0.26)
    r.path("P12_SET", "In4", (28.7, 40), (28.7, 35.6), (32.7, 35.6), (32.7, 30.8), (32.5, 30.8), width=0.26)
    r.path("P12_SET", "F", p("U8", 2), (32.5, 30.8), width=0.26)
    r.path("P12_SET", "B", p("C40", 1), (28, 38.2), width=0.26)
    r.path("P12_SET", "In4", (28, 38.2), (28, 42), width=0.26)
    r.path("P12_RMID", "B", p("R25", 2), p("R26", 1), width=0.26)
    r.path("P12_FB", "B", p("R26", 2), p("R27", 1), width=0.26)
    for at in ((35.5, 38.5), (14.1, 38.5)):
        r.via("P12_FB", at)
    r.path("P12_FB", "B", p("R26", 2), (35.5, 38.5), width=0.26)
    r.path("P12_FB", "In2", (35.5, 38.5), (35.5, 39), (14.1, 39), (14.1, 38.5), width=0.26)
    r.path("P12_FB", "F", (14.1, 38.5), (16, 38.5), width=0.26)
    r.path("AGND", "B", p("C40", 2), (30.8, 38.2), width=0.26)
    r.path("AGND", "In3", (30.8, 38.2), (30.9, 38.3), (30.9, 36.8), (30.9, 31), (31.4, 31), width=0.26)
    r.path("AGND", "B", p("R27", 2), (40.3, 40), width=0.26)
    r.path("AGND", "In3", (40.3, 40), (40.3, 36.8), (30.9, 36.8), width=0.26)
    # +12 V input bypass, LT3080 IN and VCONTROL.
    for at in ((36.5, 24.5), (32, 34.2), (38.7, 10.5)):
        r.via("RAW_P17", at)
    r.path("RAW_P17", "In4", (39.15, 4.9), (38.7, 4.9), (38.7, 10.5), width=0.5)
    r.path("RAW_P17", "In2", (38.7, 10.5), (38.7, 16.8), (36.5, 16.8), (36.5, 24.5), width=0.5)
    r.path("RAW_P17", "In3", (36.5, 24.5), (36.5, 34.2), (32, 34.2), width=0.5)
    r.path("RAW_P17", "F", p("C41", 1), (32, 34.2), width=0.5)
    r.path("RAW_P17", "F", (32, 34.2), p("U8", 4), p("U8", 5), width=0.5)
    # Full load output and conventional thermal vias, with the actual OUT tab.
    for at in (*P12_OUT, (46.5, 24.5), (34.5, 24.25), (31.8, 32.2), (31.8, 33)):
        r.via("P12_SRC", at)
    r.path("P12_SRC", "F", (35.35, 32), (31.8, 32.2), width=1.2)
    r.path("P12_SRC", "F", (31.8, 32.2), (31.8, 33), width=0.5)
    r.path("P12_SRC", "In3", (31.8, 32.2), (31.8, 33), width=0.5)
    r.path("P12_SRC", "F", (35.35, 32), (44.5, 32), (53.5, 32), (53.5, 33), (53.5, 34), width=1.2)
    r.path("P12_SRC", "B", p("C42", 1), (46.5, 24.5), width=0.5)
    r.path("P12_SRC", "B", (46.5, 24.5), (46.5, 32), (53.5, 32), width=0.5)
    r.path("P12_SRC", "In4", (46.5, 24.5), (46.5, 25.5), width=0.5)
    r.path("P12_SRC", "B", p("C43", 1), (34.5, 24.25), width=0.5)
    r.path("P12_SRC", "B", (34.5, 24.25), (34.5, 32.2), (31.8, 32.2), width=0.5)
    r.path("P12_SRC", "In4", (34.5, 24.25), (34.5, 25.5), (46.5, 25.5), (53.5, 25.5), (53.5, 32), width=0.5)
    r.via("P12_SRC", (41.3, 40))
    r.path("P12_SRC", "B", p("R29", 1), (41.3, 40), width=0.26)
    r.path("P12_SRC", "In4", (41.3, 40), (41.3, 41.3), (53.5, 41.3), (53.5, 32), width=0.5)
    # Reservoir power returns, independently of the divider/filter reference.
    for at in ((33, 43), (51, 24), (32.8, 23.2), (45.8, 40)):
        r.via("AGND", at)
    r.path("AGND", "F", p("C41", 2), (33, 43), width=0.5)
    r.path("AGND", "In1", (33, 43), (42, 43), (42, 23.2), width=0.5)
    r.path("AGND", "B", p("C42", 2), (51, 24), width=0.5)
    r.path("AGND", "B", p("C43", 2), (32.8, 21.05), (32.8, 23.2), width=0.5)
    r.path(
        "AGND",
        "In1",
        (32.8, 23.2),
        (42, 23.2),
        (50, 23.2),
        (50, 23.7),
        (51, 24),
        (50, 23.7),
        (50, 5.3),
        width=0.8,
    )
    r.path("AGND", "B", p("R29", 2), (45.8, 40), width=0.26)
    r.path("AGND", "In1", (45.8, 40), (45.8, 23.5), (51, 24), width=0.5)


def add_output_planes(board, nets):
    for net, bounds in [("P19_SRC", (8.5, 29, 16.5, 35)), ("P12_SRC", (32, 24, 56, 38))]:
        x, y, xx, yy = [100 + v for v in bounds]
        board.append(
            read_sexpr(f"""(zone (net {nets[net]}) (net_name "/{net}") (layer "B.Cu") (hatch edge .5)
        (connect_pads yes (clearance .15)) (min_thickness .15) (fill yes (thermal_gap .2) (thermal_bridge_width .3))
        (polygon (pts (xy {x} {y}) (xy {xx} {y}) (xy {xx} {yy}) (xy {x} {yy}))))""")
        )


def route_distribution(r):
    """Wide inner-layer source-to-header feeds with complete via/pad obstacles."""
    import math

    from ...common.sexpr import children, first
    from ...output_stage.check_placement import transform
    from . import power_grid

    all_layers = list(power_grid.ALL_LAYERS)
    r.geometry[:] = [g for g in r.geometry if g["kind"] != "rect"]
    for g in r.geometry:
        if g["kind"] == "circle" and len(g["layers"]) > 1:
            g["layers"] = all_layers
    for fp in children(r.board, "footprint"):
        angle = float(first(fp, "at")[3]) if len(first(fp, "at")) > 3 else 0
        for pad in children(fp, "pad"):
            x, y = transform(fp, first(pad, "at")[1:3])
            rotation = angle + (float(first(pad, "at")[3]) if len(first(pad, "at")) > 3 else 0)
            w, h = map(float, first(pad, "size")[1:3])
            if abs(math.sin(math.radians(rotation))) > 0.5:
                w, h = h, w
            layers = (
                all_layers
                if "*.Cu" in first(pad, "layers")[1:]
                else [l for l in first(pad, "layers")[1:] if str(l).endswith(".Cu")]
            )
            if not layers:
                continue
            net = str(first(pad, "net")[-1]).lstrip("/") if children(pad, "net") else "NPTH"
            r.geometry.append(
                dict(kind="rect", net=net, layers=layers, x=x - 100, y=y - 100, w=w, h=h, is_pad=True)
            )
    for x, y in ((4, 4), (74, 4), (4, 34), (74, 34)):
        r.geometry.append(dict(kind="circle", net="FIXING_CLEARANCE", layers=all_layers, x=x, y=y, r=3.7))
    saved = dict(getattr(r, "connected_points", {}))
    r.connected_points = {}
    r.route_width = {**getattr(r, "route_width", {}), "P19_SRC": 0.8, "P12_SRC": 1.2}
    tasks = {"P19_SRC": [(8.7, 31.5), r.p("J2", 1), (1.7, 40)], "P12_SRC": [(31.8, 32.2), r.p("J2", 4)]}
    for net, endpoints in tasks.items():
        # Preserve the contiguous In4 analog-5 V plane near the output header.
        power_grid.connect(
            r,
            {net: endpoints},
            (90, 44),
            routing_layers=("In2.Cu", "In3.Cu", "F.Cu") if net == "P19_SRC" else None,
        )
        # Newly drilled through vias also obstruct the next net on every layer.
        for shape in r.geometry:
            if shape["kind"] == "circle" and len(shape["layers"]) > 1:
                shape["layers"] = all_layers
    r.connected_points = {**saved, **r.connected_points}
