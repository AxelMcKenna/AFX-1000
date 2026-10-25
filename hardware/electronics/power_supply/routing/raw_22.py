"""Raw +/-22 V layout candidate; switching, thermal and loop behavior unqualified."""

from ...input_protection import route_grid as control_grid

MOVES = {
    "U1": (21.8, 10.3, 0, "F"),
    "L1": (14.4, 8.9, 0, "F"),
    "C33": (6.8, 13.2, 90, "F"),
    "D1": (23, 6.65, 0, "F"),
    "D2": (23, 15.75, 0, "F"),
    "C1": (25.6, 10.83, 90, "F"),
    "C2": (14.6, 15.2, 0, "F"),
    "C3": (2.35, 11.5, 90, "F"),
    "C4": (26, 10.5, 90, "B"),
    "C5": (26.5, 5.6, 180, "B"),
    "C7": (30.4, 2.5, 90, "B"),
    "R1": (3.3, 15.9, 0, "F"),
    "R2": (6.9, 15.9, 0, "F"),
    "R3": (10.5, 15.9, 0, "F"),
    "R4": (17.5, 15.5, 90, "B"),
    "R5": (16, 5.9, 90, "B"),
    "C11": (17.05, 11, 0, "B"),
    "C14": (8.8, 10.5, 90, "B"),
    "R6": (21, 14.3, 0, "B"),
    "R7": (21, 16.3, 0, "B"),
    "C12": (11, 7, 90, "B"),
}
QUIET_VIAS = ((11, 17.5), (21.8, 8.6), (18.15, 12.4))


def route(r, controls=True):
    p = r.p
    # Input bank and local underside IC bypass. Vias are conventional and
    # outside both-face lands; this does not qualify loop inductance/loss.
    r.via("VIN_PROTECTED", (24.4, 10.4))
    r.path("VIN_PROTECTED", "F", p("U1", 8), (24.4, 10.3), (24.4, 10.4), width=0.35)
    r.path("VIN_PROTECTED", "B", (24.4, 10.4), (25.1, 10.4), p("C4", 1), width=0.35)
    r.via("VIN_PROTECTED", (14.6, 13))
    r.path("VIN_PROTECTED", "F", p("C2", 1), (14.6, 13), width=0.8)
    r.path("VIN_PROTECTED", "F", p("C2", 1), (11.4, 14.4), p("L1", 1), width=0.8)
    r.path("VIN_PROTECTED", "F", p("C3", 1), (0.9, 14.6), (0.9, 23), p("L2", 1), width=0.8)
    r.path("VIN_PROTECTED", "F", p("C3", 1), (2.35, 14.6), (10.8, 14.6), (11.4, 14.4), p("C2", 1), width=0.8)
    r.path("VIN_PROTECTED", "In4", (27.5, 12.8), (25.4, 12.8), (25.4, 10.4), width=0.8)
    r.path("VIN_PROTECTED", "In4", (25.4, 10.4), (24.4, 10.4), width=0.35)
    r.path(
        "VIN_PROTECTED", "In2", (29, 10.075), (28.2, 10), (28.2, 18.5), (14.6, 18.5), (14.6, 13), width=0.8
    )
    # Boost switch fanout remains on the component face.
    r.path(
        "RAW_P_SW",
        "F",
        p("L1", 2),
        (18.2, 7.95),
        (23.45, 7.95),
        (23.45, 7.6),
        (25, 7.6),
        p("D1", 2),
        width=0.3,
    )
    r.path("RAW_P_SW", "F", p("U1", 10), (23.45, 7.95), width=0.3)
    # Rectified positive rail changes layers near D1 and the output bank.
    for at in ((23.4, 5.2), (29.2, 6), (24.6, 13.7)):
        r.via("RAW_P22", at)
    r.path("RAW_P22", "F", p("D1", 1), (23.4, 5.2), width=0.8)
    r.path("RAW_P22", "In2", (23.4, 5.2), (23.4, 6), (29.2, 6), (29.2, 6), width=0.8)
    r.path("RAW_P22", "In2", (23.4, 5.2), (23.4, 13.7), (24.6, 13.7), width=0.8)
    r.path("RAW_P22", "B", (29.2, 6), p("C5", 1), width=0.5)
    r.path("RAW_P22", "B", (24.6, 13.7), p("C6", 1), width=0.5)
    r.path("RAW_P22", "B", (29.2, 6), p("C7", 1), width=0.5)
    # Cuk switch/transfer connections and the continuous-current output choke.
    r.path("RAW_N_SW", "F", p("U1", 6), (23.45, 12.305), p("C1", 1), width=0.3)
    r.path(
        "RAW_N_SW",
        "F",
        p("L2", 2),
        (11.825, 17.2),
        (23.1, 17.2),
        (23.1, 12.305),
        (23.45, 12.305),
        p("C1", 1),
        width=0.6,
    )
    r.path("CUK_NODE", "F", p("C1", 2), (27.37, 9.355), (27.37, 18), (25, 18), p("D2", 2), width=0.5)
    r.path("CUK_NODE", "F", (25, 18), (16.175, 18), p("L3", 1), width=0.5)
    # Negative rail distribution to both bulk capacitors and local bypass.
    for at in ((27.5, 23), (19, 21), (26.2, 13.8), (18.5, 6)):
        r.via("RAW_N22", at)
    r.path("RAW_N22", "F", p("L3", 2), (27.5, 23), width=0.8)
    r.path(
        "RAW_N22",
        "In4",
        (27.5, 23),
        (27.5, 24.2),
        (20.4, 24.2),
        (20.4, 21),
        (19, 21),
        (17, 21),
        (17, 6),
        (18.5, 6),
        width=0.8,
    )
    r.path("RAW_N22", "In4", (27.5, 23), (29.2, 23), (29.2, 14), (26.2, 14), (26.2, 13.8), width=0.8)
    r.path("RAW_N22", "B", (19, 21), p("C9", 1), width=0.5)
    r.path(
        "RAW_N22",
        "B",
        (26.2, 13.8),
        (26.2, 13.6),
        (27.15, 13.6),
        (27.15, 10.8),
        (29, 10.8),
        (29, 11.975),
        p("C8", 1),
        width=0.5,
    )
    r.path("RAW_N22", "B", (18.5, 6), p("C10", 1), width=0.5)
    # PGND spines stay separate from the three quiet return escapes.
    for at in (
        (2.55, 8.5),
        (16.075, 13),
        (20.7, 12.4),
        (21.45, 12.4),
        (22.2, 12.4),
        (26.1, 8.3),
        (18.8, 13),
        (26.5, 17.1),
    ):
        r.via("AGND", at)
    r.path("AGND", "F", p("U1", 11), (21.6, 10.3), (21.6, 12.4), (21.45, 12.4), (20.7, 12.4), width=0.5)
    r.path("AGND", "F", (21.45, 12.4), (22.2, 12.4), width=0.5)
    r.path("AGND", "F", p("U1", 5), (21.5, 11.3), p("U1", 11), width=0.26)
    r.path("AGND", "F", p("C3", 2), (2.55, 8.5), width=0.8)
    r.path("AGND", "F", p("C2", 2), (16.075, 13), width=0.8)
    r.path("AGND", "B", p("C4", 2), (26.1, 8.3), width=0.35)
    r.path("AGND", "F", p("D2", 1), (18.8, 13), width=0.8)
    r.path("AGND", "B", p("C5", 2), (26.1, 5), width=0.5)
    r.path("AGND", "B", p("C6", 2), (26.5, 17.1), width=0.5)
    r.path("AGND", "B", p("C7", 2), (32.325, 1.55), (32.325, 3.8), width=0.5)
    r.path(
        "AGND",
        "In1",
        (2.55, 8.5),
        (2.55, 10.8),
        (16.075, 10.8),
        (16.075, 13),
        (16.075, 13.3),
        (18.8, 13.3),
        (18.8, 13),
        (20.7, 13),
        (20.7, 12.4),
        (21.45, 12.4),
        (22.2, 12.4),
        (25.5, 12.4),
        width=0.8,
    )
    r.path(
        "AGND",
        "In1",
        (26.5, 17.1),
        (25.5, 17.1),
        (25.5, 16.1),
        (27.1, 16.1),
        (27.1, 12.7),
        (25.5, 12.7),
        (25.5, 12.4),
        (25.5, 8.3),
        (26.1, 8.3),
        (26.1, 5),
        width=0.8,
    )
    # Negative output returns reuse nearby dedicated PGND vias.

    r.via("AGND", (21.6, 20.8))
    r.via("AGND", (23.7, 4))

    r.path("AGND", "B", p("C9", 2), (21.6, 20.8), width=0.5)
    r.path("AGND", "B", p("C10", 2), (22.5, 6), (22.5, 4.4), (23.7, 4.4), (23.7, 4), width=0.5)

    r.path("AGND", "In1", (21.6, 20.8), (22.5, 19), (25.5, 19), (25.5, 17.1), width=0.8)
    r.path("AGND", "In1", (23.7, 4), (26.1, 4), (26.1, 5), width=0.8)
    # Separate reference/divider return to the exposed pad.
    for at in QUIET_VIAS:
        r.via("AGND", at)
    r.path("AGND", "F", p("R3", 2), (11, 17.5), width=0.26)
    r.path(
        "AGND",
        "In3",
        (11, 17.5),
        (11, 7),
        (12.5, 7),
        (12.5, 7.5),
        (14.7, 7.5),
        (14.7, 7),
        (18.15, 7),
        (21.8, 7),
        (21.8, 8.6),
        width=0.26,
    )
    r.path("AGND", "B", p("C11", 2), (18.15, 12.4), width=0.26)
    r.path("AGND", "In3", (18.15, 12.4), (18.15, 7), width=0.26)
    r.path("AGND", "F", (21.8, 8.6), p("U1", 11), width=0.26)
    # Feedback/reference fanout and compact reference bypass on B.
    for net, at in (("RAW_P_FB", (19.45, 9.3)), ("SW_REF_1V", (19.45, 10.1)), ("RAW_N_FB", (19.45, 10.9))):
        r.via(net, at)
    r.path("RAW_P_FB", "F", p("U1", 1), (19.45, 9.3), width=0.26)
    r.path("SW_REF_1V", "F", p("U1", 2), (19.45, 10.1), p("U1", 3), width=0.26)
    r.path("RAW_N_FB", "F", p("U1", 4), (19.45, 10.9), width=0.26)
    r.path(
        "SW_REF_1V",
        "B",
        (19.45, 10.1),
        (19.45, 9.9),
        (16.1, 9.9),
        p("C11", 1),
        (14.9, 11),
        (14.9, 12),
        (15.4, 12),
        (15.4, 15.45),
        (17.5, 15.45),
        p("R4", 1),
        width=0.26,
    )
    # Positive divider source sense is independent of its output-bank feed.
    r.via("RAW_P22", (2.3875, 17.5))
    r.path("RAW_P22", "F", (2.3875, 17.5), p("R1", 1), width=0.26)
    r.path(
        "RAW_P22",
        "In2",
        (2.3875, 17.5),
        (1.7, 17.5),
        (1.7, 9.3),
        (9, 9.3),
        (9, 7.95),
        (9, 5),
        (23.4, 5),
        (23.4, 5.2),
        width=0.26,
    )
    r.path("RAW_P_RMID", "F", p("R1", 2), p("R2", 1), width=0.26)
    r.path("RAW_P_FB", "F", p("R2", 2), p("R3", 1), width=0.26)
    r.via("RAW_P_FB", (8, 18))
    r.path("RAW_P_FB", "F", (8, 18), p("R2", 2), width=0.26)
    r.path("RAW_P_FB", "In2", (19.45, 9.3), (17, 9.3), (17, 11), (8.9, 11), (8.9, 17.5), (8, 18), width=0.26)
    r.via("RAW_P_FB", (11, 4.2))
    r.path("RAW_P_FB", "In4", (19.45, 9.3), (19.45, 4.2), (11, 4.2), width=0.26)
    r.path("RAW_P_FB", "B", (11, 4.2), p("C12", 2), width=0.26)
    r.via("RAW_P22", (9, 7.95))
    r.path("RAW_P22", "In2", (9, 5), (9, 7.95), width=0.26)
    r.path("RAW_P22", "B", (9, 7.95), p("C12", 1), width=0.26)
    # Negative feedback has a local B divider and an explicit receiving via.
    r.via("RAW_N_FB", (18.8, 14.6))
    r.path("RAW_N_FB", "In2", (19.45, 10.9), (19.45, 14.6), (18.8, 14.6), width=0.26)
    r.path("RAW_N_FB", "B", (18.8, 14.6), p("R4", 2), width=0.26)
    r.path("RAW_N_FB", "B", (19.45, 10.9), (20.5, 11), (20.5, 8.5), (16, 8.5), p("R5", 1), width=0.26)
    r.path("RAW_N_FB", "B", (16, 8.5), (16, 9), (9.8, 9), (9.8, 9.55), p("C14", 2), width=0.26)
    r.via("RAW_N22", (12.8, 6))
    r.path("RAW_N22", "B", (12.8, 6), p("R5", 2), width=0.26)
    r.path("RAW_N22", "In2", (12.8, 6), (18.5, 6), width=0.26)
    r.via("RAW_N22", (10, 11.9))
    r.path("RAW_N22", "In3", (12.8, 6), (10, 6), (10, 11.9), width=0.26)
    r.path("RAW_N22", "B", (10, 11.9), p("C14", 1), width=0.26)
    # Startup controls take an explicit source-power feed through In4.
    r.via("5V_DIG_SRC", (18.8, 16.2))
    r.path("5V_DIG_SRC", "In4", (47, 1.5), (46.2, 1), (24.8, 1), width=0.35)
    r.path("5V_DIG_SRC", "In4", (24.8, 1), (24.8, 7), (22.9, 7), (22.9, 16.2), (18.8, 16.2), width=0.35)
    r.via("RAW_P_SS", (24.3, 8.25))
    r.path("RAW_P_SS", "F", p("U1", 9), (23.9625, 9.8), (23.9625, 8.25), (24.3, 8.25), width=0.26)
    r.via("RAW_N_SS", (24.4, 11.2))
    r.path("RAW_N_SS", "F", p("U1", 7), (24, 10.9), (24.4, 11.2), width=0.26)
    r.path("AGND", "B", p("C13", 2), (26.5, 17.1), width=0.26)
    r.path("AGND", "B", p("C15", 2), (28.4, 14.05), (28.4, 17.1), (26.5, 17.1), width=0.26)
    for x, y in QUIET_VIAS:
        r.geometry.append(dict(kind="circle", net="QUIET_RETURN_RESERVE", layers=["B.Cu"], x=x, y=y, r=0.5))
    tasks = {
        "5V_DIG_SRC": [(18.8, 16.2), p("R6", 1), p("R7", 1)],
        "RAW_P_SS": [(24.3, 8.25), p("R6", 2), p("C13", 1)],
        "RAW_N_SS": [(24.4, 11.2), p("R7", 2), p("C15", 1)],
    }
    if controls:
        route_power(r)
        route_controls(r, tasks)
    return tasks


def route_power(r):
    route_controls(r, {"AGND": [(32.325, 3.8), r.p("C8", 2)]})


def route_controls(r, tasks):
    r.route_width = {net: (0.5 if net == "AGND" else 0.26) for net in tasks}
    original = control_grid.LAYERS
    connected = getattr(r, "connected_points", {})
    r.connected_points = {}
    try:
        control_grid.LAYERS = ("B.Cu",)
        control_grid.connect(r, tasks, (84, 38))
    finally:
        control_grid.LAYERS = original
        for net, points in connected.items():
            r.connected_points.setdefault(net, []).extend(points)
