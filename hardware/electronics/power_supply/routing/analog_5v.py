"""Analog 5 V/reference layout candidate; electrical/thermal qualification open."""

from ...common.sexpr import read_sexpr

MOVES = {
    "U4": (18, 23.5, 0, "B"),
    "R17": (30.7, 26.2, 0, "F"),
    "C30": (12.5, 24, 0, "B"),
    "C31": (23, 22.4, 90, "B"),
    "C36": (18.5, 30.6, 90, "B"),
    "C51": (22, 30.6, 90, "B"),
    "C53": (31, 25.5, 90, "B"),
    "C44": (22.9, 35.3, 90, "B"),
    "C59": (19.4, 34.1, 0, "B"),
    "C60": (22, 27.2, 0, "B"),
    "R32": (19.5, 36.8, 0, "B"),
    "R30": (27, 29.8, 0, "F"),
    "R31": (30.5, 29.8, 0, "F"),
    "C46": (68.6, 28.5, 0, "B"),
    "C48": (64.5, 29.3, 0, "B"),
}
QUIET_VIAS = ((19, 22.9), (23.95, 31.6), (31.4, 31), (69, 36.5))
QUIET_PAD = (30.5, 34)
OUT_VIAS = ((64.5, 31.4), (65.25, 31.4), (66, 31.4))


def route(r):
    p = r.p
    # Reference input power is drawn from the source copper. The chosen
    # enhanced-grade REF5025E has EN on pin 1; standard grades are different.
    r.via("5V_DIG_SRC", (14.2, 26.5))
    r.path(
        "5V_DIG_SRC",
        "In2",
        (18.8, 16.2),
        (17.4, 16.2),
        (17.4, 11.8),
        (13, 11.8),
        (13, 26.5),
        (14.2, 26.5),
        width=0.35,
    )
    r.path(
        "5V_DIG_SRC", "B", (14.2, 26.5), (14.2, 25.3), (14.2, 24.2), (11.55, 24.2), p("C30", 1), width=0.35
    )
    r.path(
        "5V_DIG_SRC",
        "B",
        p("C30", 1),
        (11.55, 24.2),
        (14.2, 24.2),
        (14.2, 25.3),
        p("U4", 1),
        p("U4", 2),
        width=0.35,
    )
    # Local reference output capacitor, then the existing RC/film filter.
    r.path("PREF_2V5", "B", p("U4", 6), p("C31", 1), width=0.26)
    r.via("PREF_2V5", (22, 25.2))
    r.path("PREF_2V5", "B", p("C31", 1), (22.2, 23.35), (22.2, 25.2), (22, 25.2), width=0.26)
    r.via("PREF_2V5", (29.9, 27.8))
    r.path("PREF_2V5", "In4", (22, 25.2), (22, 27.8), (29.9, 27.8), width=0.26)
    r.path("PREF_2V5", "F", (29.9, 27.8), p("R17", 1), width=0.26)
    r.via("PREF_FILTER", (32.6, 26.2))
    r.path("PREF_FILTER", "F", p("R17", 2), (32.6, 26.2), width=0.26)
    r.path("PREF_FILTER", "In2", (32.6, 26.2), (34, 26.2), (34, 35.4), (25.5, 35.4), p("C32", 1), width=0.26)
    for at in ((23.8, 35), (16, 31.8)):
        r.via("PREF_FILTER", at)
    r.path("PREF_FILTER", "In3", p("C32", 1), (25.5, 34.5), (23.8, 34.5), (16, 34.5), (16, 31.8), width=0.26)
    r.path("PREF_FILTER", "In3", (23.8, 34.5), (23.8, 35), width=0.26)
    r.path("PREF_FILTER", "F", p("U5", 10), (23.8, 35), width=0.26)
    r.path("PREF_FILTER", "F", p("U5", 3), (16, 31.8), (16, 34.37), p("U5", 5), width=0.26)
    # Quad-amplifier bypass. C36/C51/C53 move only to clear these local parts;
    # their respective +/-19 V regulator circuits remain incomplete.
    for at in ((19.3, 27), (19.3, 33.05)):
        r.via("RAW_P22", at)
    r.path(
        "RAW_P22",
        "In3",
        (24.6, 13.7),
        (20.6, 13.7),
        (20.6, 22),
        (18, 22),
        (18, 27),
        (19.3, 27),
        (19.3, 33.05),
        width=0.5,
    )
    r.path("RAW_P22", "B", (19.3, 27), p("C60", 1), width=0.35)
    r.path("RAW_P22", "F", (19.3, 33.05), p("U5", 4), width=0.35)
    r.path("RAW_P22", "B", (19.3, 33.05), p("C59", 1), p("C36", 1), width=0.35)
    # The op-amp HF feedback capacitor is now local to its OUT/- pins.
    r.via("V5_REG_DRIVE", (24.8, 36.5))
    r.path("V5_REG_DRIVE", "F", p("U5", 8), (24.8, 36.5), width=0.26)
    r.path("V5_REG_DRIVE", "B", (24.8, 36.5), p("C44", 1), width=0.26)
    r.via("V5_REG_DRIVE", (19, 35.3))
    r.path("V5_REG_DRIVE", "In3", (24.8, 36.5), (24.8, 36.8), (19, 36.8), (19, 35.3), width=0.26)
    r.path("V5_REG_DRIVE", "B", (19, 35.3), (18.5875, 35.3), p("R32", 1), width=0.26)
    r.via("V5_REG_FB", (24.4, 32.6))
    r.path("V5_REG_FB", "B", p("C44", 2), (24.4, 33.825), (24.4, 32.6), width=0.26)
    r.path("V5_REG_FB", "F", p("U5", 9), (24.4, 35.64), (24.4, 32.6), width=0.26)
    r.via("V5_REG_FB", (31.4, 28))
    r.path("V5_REG_FB", "In2", (24.4, 32.6), (26.6, 32.6), (26.6, 29), (31.4, 29), (31.4, 28), width=0.26)
    r.path("V5_REG_FB", "F", p("R30", 2), p("R31", 1), (31.4, 28), width=0.26)
    # Post-isolation drive and a distinct Kelvin sense path meet at U9 SET.
    for at in ((20.5, 35.4), (25, 31), (61.6, 34.5), (62.85, 30.8)):
        r.via("V5_REG_SET", at)
    r.path("V5_REG_SET", "B", p("R32", 2), (20.5, 35.4), width=0.26)
    r.path(
        "V5_REG_SET",
        "In2",
        (20.5, 35.4),
        (20.5, 37.15),
        (55, 37.15),
        (55, 34),
        (61.6, 34),
        (61.6, 34.5),
        width=0.26,
    )
    r.path("V5_REG_SET", "B", p("U9", 4), (61.6, 32.025), (61.6, 34.5), (61.6, 36), p("C45", 1), width=0.26)
    r.path("V5_REG_SET", "B", p("U9", 4), (62.85, 30.8), width=0.26)
    r.path("V5_REG_SET", "F", p("R30", 1), (25, 31), width=0.26)
    r.path(
        "V5_REG_SET",
        "In2",
        (25, 31),
        (23.5, 31),
        (23.5, 25.2),
        (58.5, 25.2),
        (58.5, 30.8),
        (62.85, 30.8),
        width=0.26,
    )
    # Precision return domain joins the declared output-ground pin, not an
    # upstream switching-current return. Keepouts isolate all its vias/film pad.
    for at in QUIET_VIAS:
        r.via("AGND", at)
    r.path("AGND", "B", p("U4", 4), (19, 22.9), width=0.26)
    r.path("AGND", "B", p("C30", 2), (13.45, 21.595), p("U4", 4), width=0.26)
    r.path("AGND", "B", p("C31", 2), (22, 21.45), (22, 22.2), (19, 22.2), (19, 22.9), width=0.26)
    r.path("AGND", "In3", (19, 22.9), (25.2, 22.9), (25.2, 4.6), (12.14, 4.6), p("J2", 2), width=0.26)
    r.path("AGND", "In3", (23.95, 31.6), (23.95, 26), (19, 26), (19, 22.9), width=0.26)
    r.path("AGND", "In3", p("C32", 2), (30.5, 31), (30.5, 26), (23.95, 26), width=0.26)
    r.path("AGND", "F", p("U5", 11), (23.5, 33.1), (23.95, 31.6), p("U5", 12), width=0.26)
    r.path("AGND", "B", p("C59", 2), (20.35, 32.95), (23.7, 32.95), (23.7, 31.6), (23.95, 31.6), width=0.26)
    r.path("AGND", "B", p("C60", 2), (23.95, 27.2), (23.95, 31.6), width=0.26)
    r.path("SPARE_OUT", "F", p("U5", 13), p("U5", 14), width=0.26)
    r.path("AGND", "F", p("R31", 2), (31.4, 31), width=0.26)
    r.path("AGND", "In3", (31.4, 31), (30.5, 31), (30.5, 26), width=0.26)
    r.path("AGND", "B", p("C45", 2), (69, 36.5), width=0.26)
    r.path("AGND", "In3", (69, 36.5), (69, 36.8), (27.8, 36.8), (27.8, 31.6), (23.95, 31.6), width=0.26)
    # Local LDO input bypass and VCONTROL are separate power inputs.
    r.path(
        "V5_PRE",
        "B",
        p("C46", 1),
        (68.4, 28.5),
        (68.4, 30.4),
        (69.6, 30.4),
        (69.6, 34.8),
        (68.6, 34.8),
        width=0.5,
    )
    r.via("VIN_PROTECTED", (67.6, 31))
    r.path("VIN_PROTECTED", "B", (67.6, 31), p("U9", 5), width=0.35)
    r.path(
        "VIN_PROTECTED", "In4", (70.2, 18.5), (72.5, 18.5), (72.5, 29.5), (67.6, 29.5), (67.6, 31), width=0.35
    )
    # The exposed pad is OUT. Conventional external thermal vias connect it
    # to the proposed In4 output-power plane; thermal performance is unproven.
    for at in OUT_VIAS:
        r.via("V5_REG_SRC", at)
    r.path("V5_REG_SRC", "B", p("U9", 9), (64.5, 33), (64.5, 31.4), (65.25, 31.4), (66, 31.4), width=0.5)
    r.path("V5_REG_SRC", "B", p("U9", 3), p("U9", 2), p("U9", 1), (64, 33.975), p("U9", 9), width=0.5)
    r.path("V5_REG_SRC", "B", p("C47", 1), p("C48", 1), (64.5, 31.4), width=0.5)
    r.path("V5_REG_SRC", "In4", *OUT_VIAS, width=0.8)
    # Reservoir returns use power ground, outside the precision return domain.
    for at in ((70.1, 26.5), (65.45, 30.5), (80.5, 19.6)):
        r.via("AGND", at)
    r.path("AGND", "B", p("C46", 2), (70.1, 26.5), width=0.5)
    r.path("AGND", "In1", (70.1, 26.5), (74.9, 26.5), (74.9, 26.275), width=0.8)
    r.path("AGND", "B", p("C47", 2), (59.5, 25), width=0.5)
    r.path("AGND", "B", p("C48", 2), (65.45, 30.5), width=0.5)
    r.path("AGND", "In1", (65.45, 30.5), (65.45, 29.9), (59.5, 29.9), (59.5, 32.75), width=0.8)
    # Minimum-load resistor is connected to the output plane and PGND.
    r.via("V5_REG_SRC", (80.5, 21.4))
    r.path("V5_REG_SRC", "B", p("R33", 1), (80.5, 21.4), width=0.5)
    r.path("AGND", "B", p("R33", 2), (80.5, 19.6), width=0.26)
    r.path("AGND", "In1", (80.5, 19.6), (82.6, 13.5), width=0.5)
    for x, y in (*QUIET_VIAS, QUIET_PAD):
        r.geometry.append(
            dict(
                kind="circle",
                net="PRECISION_RETURN_RESERVE",
                layers=["B.Cu"],
                x=x,
                y=y,
                r=0.5 if (x, y) != QUIET_PAD else 1.0,
            )
        )


def add_output_plane(board, nets):
    # Review allocation: the filled copper must be checked for connected
    # source/header contacts, necks and resistance before claiming a drop budget.
    board.append(
        read_sexpr(f"""(zone (net {nets["V5_REG_SRC"]}) (net_name "/V5_REG_SRC") (layer "In4.Cu") (hatch edge .5)
      (connect_pads yes (clearance .15)) (min_thickness .15) (fill yes (thermal_gap .2) (thermal_bridge_width .3))
      (polygon (pts (xy 100.6 100.6) (xy 189.4 100.6) (xy 189.4 143.4) (xy 100.6 143.4))))""")
    )
