"""Explicit +/-17V boost/Cuk layout candidate; no switching/thermal qualification."""

from ...input_protection import route_grid as control_grid

MOVES = {
    "U13": (44, 8.2, 0, "F"),
    "L6": (35.5, 7.5, 0, "F"),
    "L8": (48.5, 20.85, 0, "F"),
    "D3": (44, 3.5, 0, "F"),
    "D4": (50.65, 5.3, 270, "F"),
    "C63": (48.5, 11.6, 90, "F"),
    "C64": (28.9, 1.9, 180, "F"),
    "C65": (33.8, 1.9, 180, "F"),
    "C66": (38.2, 1.7, 180, "F"),
    "C70": (28.2, 6.2, 90, "F"),
    "C71": (47.7, 7, 90, "F"),
    "C61": (38, 13.5, 90, "B"),
    "C62": (36.25, 8.5, 90, "B"),
    "C73": (35.75, 13.4, 90, "B"),
    "C75": (41.5, 4, 0, "B"),
    "C74": (49.5, 3.9, 0, "B"),
    "C76": (60.5, 5, 90, "B"),
    "R44": (31, 12.5, 0, "F"),
    "R45": (34.5, 12.5, 0, "F"),
    "R46": (38, 12.5, 0, "F"),
    "R47": (41.5, 12.5, 0, "F"),
    "R48": (49, 18.5, 0, "B"),
    "R49": (49.5, 7, 0, "B"),
    "R50": (49.5, 9.3, 0, "B"),
}
QUIET_VIAS = ((35.4125, 10.8), (44.6, 9.9), (36.35, 2.9))


def route(r):
    p = r.p
    # Conventional through vias stay outside solder lands. Current, ringing
    # and loss in the narrow DFN necks still need qualification.
    r.path("VIN_PROTECTED", "F", p("C70", 1), p("L6", 1), width=0.8)
    r.path("VIN_PROTECTED", "F", p("C70", 1), (28.2, 19.5), p("L7", 1), width=0.8)
    r.path("VIN_PROTECTED", "F", p("U13", 8), (47.7, 8.2), p("C71", 1), (47.6, 9), width=0.35)
    r.via("VIN_PROTECTED", (27.7, 10))
    r.path("VIN_PROTECTED", "F", p("C70", 1), (27.7, 10), width=0.8)
    r.path(
        "VIN_PROTECTED",
        "In4",
        (52.1, 3),
        (52.1, 2.5),
        (38, 2.5),
        (38, 1.9),
        (35, 1.9),
        (35, 2.5),
        (27.5, 2.5),
        (27.7, 10),
        (27.5, 12.8),
        (49, 12.8),
        (49, 9),
        (47.6, 9),
        width=0.8,
    )
    r.via("VIN_PROTECTED", (47.6, 9))
    r.path("LO_P_SW", "F", p("L6", 2), (40.5, 5.8), (45.8, 5.8), p("D3", 2), width=0.3)
    r.path("LO_P_SW", "F", p("U13", 10), (45.8, 6.8), (45.8, 5.8), width=0.3)
    r.path("RAW_P17", "F", p("D3", 1), (42, 5), (39.15, 5), (35.275, 5), (30.375, 5), width=0.8)
    for ref in ("C64", "C65", "C66"):
        r.path("RAW_P17", "F", (p(ref, 1)[0], 5), p(ref, 1), width=0.8)
    # Switched Cuk loop on the component face; output choke feed below the
    # feedback strip, with separate high-current and quiet return paths.
    r.path("LO_N_SW", "F", p("U13", 6), (45.45, 11.7), (46.2, 13.075), p("C63", 1), width=0.3)
    r.path(
        "LO_N_SW",
        "F",
        p("L7", 2),
        (40.8, 19.5),
        (40.8, 15.2),
        (47, 15.2),
        (47, 13.075),
        p("C63", 1),
        width=0.6,
    )
    r.path(
        "LO_CUK_NODE",
        "F",
        p("D4", 2),
        p("C63", 2),
        (50.3, 10.125),
        (50.3, 17.2),
        (44.175, 17.2),
        p("L8", 1),
        width=0.5,
    )
    r.path("RAW_N17", "F", p("L8", 2), (54.6, 17.9), width=0.8)
    r.via("RAW_N17", (54.6, 17.9))
    r.path("RAW_N17", "B", (54.6, 17.9), p("C56", 1), width=0.5)
    r.path("RAW_N17", "In3", (54.6, 17.9), (51.5, 17.9), (47.1, 18), width=0.8)
    r.via("RAW_N17", (47.1, 18))
    r.path("RAW_N17", "B", (47.1, 18), (47.1, 16.5), p("C69", 1), width=0.5)
    r.path("RAW_N17", "B", p("C69", 1), (48.05, 14.475), p("C68", 1), width=0.5)
    r.via("RAW_N17", (56.5, 8.7))
    r.path("RAW_N17", "B", (56.5, 8.7), p("C67", 1), width=0.5)
    r.path("RAW_N17", "In3", (56.5, 8.7), (53, 8.7), (53, 15), (51.5, 15), (51.5, 17.9), width=0.8)
    for at in (
        (26, 2.8),
        (32.325, 3.8),
        (37.25, 3.8),
        (26.1, 5),
        (47.6, 4.7),
        (43.25, 10.8),
        (44, 10.8),
        (44.75, 10.8),
        (50, 5.3),
        (56.2, 6.4),
    ):
        r.via("AGND", at)
    for ref, at, width in (
        ("C64", (26, 2.8), 0.8),
        ("C65", (32.325, 3.8), 0.8),
        ("C66", (37.25, 3.8), 0.8),
        ("C70", (26.1, 5), 0.8),
        ("C71", (47.6, 4.7), 0.35),
    ):
        r.path("AGND", "F", p(ref, 2), at, width=width)
    r.path("AGND", "F", p("D4", 1), (50.65, 5.3), (50, 5.3), width=0.8)
    r.path(
        "AGND",
        "F",
        p("U13", 11),
        (43.6, 8.2),
        (43.6, 10.8),
        (43.25, 10.8),
        (44, 10.8),
        (44.75, 10.8),
        width=0.5,
    )
    r.path("AGND", "F", p("U13", 5), (43.5, 9.2), p("U13", 11), width=0.26)
    r.path(
        "AGND",
        "In1",
        (26.1, 5),
        (26.1, 3.8),
        (26, 2.8),
        (32.325, 3.8),
        (37.25, 3.8),
        (47.6, 3.8),
        (47.6, 4.7),
        (48.9, 4.7),
        (48.9, 10.8),
        (47.6, 10.8),
        (44.75, 10.8),
        (44, 10.8),
        (43.25, 10.8),
        width=0.8,
    )
    r.path("AGND", "In1", (50, 5.3), (50, 10.8), (48.9, 10.8), width=0.8)
    # Shorter power-return spine to the EP; it clears both feedback escapes
    # and the isolated divider-return via rather than sharing their copper.
    r.path("AGND", "In1", (37.25,3.8), (40.45,3.8), (40.45,9.5),
           (39.7,9.5), (39.7,11.8), (43.25,11.8), (43.25,10.8), width=.8)
    r.path("AGND", "B", p("C67", 2), (56.2, 6.4), width=0.5)
    r.path("AGND", "In1", (56.2, 6.4), (56.5, 5.5), width=0.8)
    r.path("AGND", "B", p("C69", 2), (54.8, 16.5), width=0.5)
    r.via("AGND", (47.2, 11.525))
    r.path("AGND", "B", p("C68", 2), (47.2, 11.525), width=0.5)
    r.path("AGND", "In1", (47.2, 11.525), (47.2, 10.8), (47.6, 10.8), width=0.8)
    for at in QUIET_VIAS:
        r.via("AGND", at)
    r.path("AGND", "F", p("R45", 2), (35.4125, 10.8), width=0.26)
    r.path("AGND", "In3", (35.4125, 10.8), (35.4125, 8.7), (44.6, 8.7), (44.6, 9.9), width=0.26)
    r.path("AGND", "F", (44.6, 9.9), p("U13", 11), width=0.26)
    r.path("AGND", "B", p("C72", 2), (36.35, 2.9), width=0.26)
    r.path("AGND", "In3", (36.35, 2.9), (44.6, 2.9), (44.6, 8.7), (44.6, 9.9), width=0.26)
    # Reference and both feedback networks.
    r.via("LO_REF_1V", (41.7, 7.95))
    r.path("LO_REF_1V", "F", p("U13", 2), (41.7, 7.95), p("U13", 3), width=0.26)
    r.path("LO_REF_1V", "B", (41.7, 7.95), p("C72", 1), (37.0875, 10.8), width=0.26)
    r.via("LO_REF_1V", (37.0875, 10.8))
    r.path("LO_REF_1V", "F", (37.0875, 10.8), p("R46", 1), width=0.26)
    for net, at in (
        ("LO_P_FB", (41.7, 6.6)),
        ("LO_P_FB", (31.1, 10)),
        ("RAW_P17", (39.15, 4.9)),
        ("RAW_P17", (30.0875, 10.8)),
    ):
        r.via(net, at)
    r.path("LO_P_FB", "F", p("U13", 1), (41.7, 6.6), width=0.26)
    r.path("LO_P_FB", "In2", (41.7, 6.6), (31.9125, 6.6), (31.1, 10), width=0.26)
    r.path("LO_P_FB", "F", (31.1, 10), p("R44", 2), p("R45", 1), width=0.26)
    r.path("RAW_P17", "F", (39.15, 5), (39.15, 4.9), width=0.8)
    r.path("RAW_P17", "In2", (39.15, 4.9), (39.15, 1), (30.0875, 1), (30.0875, 10.8), width=0.26)
    r.path("RAW_P17", "F", (30.0875, 10.8), p("R44", 1), width=0.26)
    for at in ((41.5, 9.7), (40.5875, 10.8)):
        r.via("LO_N_FB", at)
    r.path("LO_N_FB", "F", p("U13", 4), (41.5, 8.7), (41.5, 9.7), width=0.26)
    r.path("LO_N_FB", "In2", (41.5, 9.7), (40.5875, 9.7), (40.5875, 10.8), width=0.26)
    r.path("LO_N_FB", "F", (40.5875, 10.8), p("R47", 1), p("R46", 2), width=0.26)
    r.via("LO_N_RMID", (42.3, 10.8))
    r.via("LO_N_RMID", (48.1, 20.1))
    r.path("LO_N_RMID", "F", p("R47", 2), (42.3, 10.8), width=0.26)
    r.path("LO_N_RMID", "In2", (42.3, 10.8), (42.3, 20.1), (48.1, 20.1), width=0.26)
    r.path("LO_N_RMID", "B", (48.1, 20.1), p("R48", 1), width=0.26)
    # RC enables take their feed from output power copper, not Kelvin copper.
    r.via("5V_DIG_SRC", (69.375, 4.5))
    r.via("5V_DIG_SRC", (47, 1.5))
    r.path("5V_DIG_SRC", "F", p("C18", 1), (69.375, 4.5), width=0.35)
    r.path("5V_DIG_SRC", "In4", (69.375, 4.5), (69.375, 1.5), (47, 1.5), width=0.35)
    r.via("LO_P_SS", (46.4, 7.4))
    r.via("LO_N_SS", (46.4, 9))
    r.path("LO_P_SS", "F", p("U13", 9), (46.2, 7.7), (46.4, 7.4), width=0.26)
    r.path("LO_N_SS", "F", p("U13", 7), (46.2, 8.7), (46.4, 9), width=0.26)
    r.via("AGND", (58.8, 4.05))
    r.path("AGND", "B", p("C74", 2), (50, 5.3), width=0.26)
    r.path("AGND", "B", p("C76", 2), (58.8, 4.05), width=0.26)
    r.path("AGND", "In1", (58.8, 4.05), (58.8, 5.5), (58, 5.5), width=0.26)
    for x, y in ((4, 4), (74, 4), (4, 34), (74, 34)):
        r.geometry.append(dict(kind="circle", net="MOUNT_RESERVE", layers=["B.Cu"], x=x, y=y, r=3.75))
    # Even on a common net, B-side power routing must avoid quiet-return vias.
    for x, y in (*QUIET_VIAS, (65, 4.75), (58, 15.2), (63.4, 18.2), (74.3, 21.6125)):
        r.geometry.append(dict(kind="circle", net="QUIET_RETURN_RESERVE", layers=["B.Cu"], x=x, y=y, r=0.5))
    tasks = {
        "5V_DIG_SRC": [(47, 1.5), p("R49", 1), p("R50", 1)],
        "LO_P_SS": [(46.4, 7.4), p("R49", 2), p("C74", 1)],
        "LO_N_SS": [(46.4, 9), p("R50", 2), p("C76", 1)],
        "RAW_P17": [(30.0875, 10.8), p("C73", 1)],
        "LO_P_FB": [(31.1, 10), p("C73", 2)],
        "LO_N_FB": [(40.5875, 10.8), p("C75", 2)],
        "RAW_N17": [p("C69", 1), p("R48", 2), p("C75", 1)],
    }
    r.route_width = {net: 0.26 for net in tasks}
    original = control_grid.LAYERS
    try:
        control_grid.LAYERS = ("B.Cu",)
        control_grid.connect(r, tasks, (84, 38))
    finally:
        control_grid.LAYERS = original
