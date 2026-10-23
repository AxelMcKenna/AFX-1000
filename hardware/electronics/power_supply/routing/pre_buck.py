"""Explicit analog pre-buck geometry; electrical/thermal qualification stays open."""

MOVES = {
    "U3": (64.8, 20.5, 270, "F"),
    "L5": (64.8, 31.3, 270, "F"),
    "J3": (76.3, 21.2, 0, "F"),
    "C23": (65.9, 23.4, 180, "F"),
    "C24": (69.4, 23.4, 0, "F"),
    "C25": (57.5, 27.5, 90, "F"),
    "C26": (57.5, 32.5, 90, "F"),
    "C27": (69.5, 20.6, 180, "F"),
    "C28": (72.8, 24.8, 270, "F"),
    "C29": (62.4, 20.7, 90, "F"),
    "R12": (70, 21.7, 0, "B"),
    "R13": (72, 23.8, 0, "B"),
    "R14": (74, 28.15, 0, "F"),
    "R15": (76.75, 28.15, 270, "F"),
    "R16": (73, 20.7, 270, "F"),
    "C57": (62.75, 12.75, 90, "B"),
    "C58": (64.25, 16.25, 0, "B"),
}

QUIET_VIAS = ((63.4, 18.2), (74.3, 21.6125))


def route(r):
    p = r.p
    # Local HF bypass and bootstrap stay entirely on F.Cu.
    r.path(
        "VIN_PROTECTED",
        "F",
        p("U3", 3),
        (64.55, 20.5),
        (63.42, 20.5),
        (63.42, 21.65),
        p("C29", 1),
        width=0.26,
    )
    r.path("AGND", "F", p("U3", 4), p("C29", 2), width=0.35)
    r.path("PRE_SW", "F", p("U3", 5), (64.05, 23.4), p("C23", 2), width=0.35)
    r.path("PRE_SW", "F", p("C23", 2), (64.95, 25), p("L5", 1), width=0.8)
    r.path("PRE_BST", "F", p("U3", 6), (64.55, 22), (66.85, 22), p("C23", 1), width=0.26)
    # Input bulk feed branches from the existing protected-input trunk.
    r.path(
        "VIN_PROTECTED",
        "In4",
        (52.1, 10.45),
        (52.1, 23),
        (60.7, 23),
        (70.975, 23),
        (70.975, 18.5),
        (70.2, 18.5),
        width=0.8,
    )
    for at in ((70.975, 18.5), (70.2, 18.5), (60.7, 21.65)):
        r.via("VIN_PROTECTED", at)
    r.path(
        "VIN_PROTECTED", "F", (70.2, 18.5), (70.975, 18.5), p("C27", 1), (71.1, 22), p("C28", 1), width=0.8
    )
    r.path("VIN_PROTECTED", "In4", (60.7, 23), (60.7, 21.65), width=0.8)
    r.path("VIN_PROTECTED", "F", (60.7, 21.65), p("C29", 1), width=0.5)
    # Positive pre-rail output bank, with a bus outside capacitor ground lands.
    r.path("V5_PRE", "F", p("L5", 2), (55.5, 35.625), (55.5, 33.975), (55.5, 28.975), p("C25", 1), width=0.8)
    r.path("V5_PRE", "F", (55.5, 33.975), p("C26", 1), width=0.8)
    r.path("V5_PRE", "F", p("C26", 1), (57.5, 35.5), width=0.8)
    r.via("V5_PRE", (57.5, 35.5))
    r.path("V5_PRE", "In3", (57.5, 35.5), (68.6, 35.5), (68.6, 34.8), width=0.8)
    r.via("V5_PRE", (68.6, 34.8))
    r.path("V5_PRE", "B", (68.6, 34.8), (68.6, 33.975), p("U9", 8), p("U9", 7), width=0.35)
    # Raw-rail engineering access branches from the output bank. It stays
    # away from the separate U9 sense via and passes around the M2 reserve.
    r.path(
        "V5_PRE",
        "In3",
        (57.5, 35.5),
        (57.5, 29.4),
        (78.2, 29.4),
        (78.2, 35.5),
        (82.14, 35.5),
        p("J4", 6),
        width=0.5,
    )
    # Sense at the actual linear-regulator IN land, separate from the feed.
    r.path("V5_PRE", "B", p("U9", 7), (68.8, 33.325), (68.8, 32.5), width=0.26)
    r.via("V5_PRE", (68.8, 32.5))
    r.path("V5_PRE", "In2", (68.8, 32.5), (71.5, 28.15), width=0.26)
    r.via("V5_PRE", (71.5, 28.15))
    r.path("V5_PRE", "F", (71.5, 28.15), p("R14", 1), width=0.26)
    r.path("PRE_RMID", "F", p("R14", 2), p("R15", 1), width=0.26)
    r.path("PRE_FB", "F", p("R15", 2), (76.75, 30.6), width=0.26)
    r.via("PRE_FB", (76.75, 30.6))
    r.path(
        "PRE_FB",
        "In2",
        (76.75, 30.6),
        (73.3, 28.8),
        (73.3, 18),
        (73, 18),
        (73, 15.5),
        (72, 15.5),
        (72, 21.3),
        (66.6, 21.3),
        width=0.26,
    )
    r.via("PRE_FB", (73, 18))
    r.via("PRE_FB", (66.6, 21.3))
    r.path("PRE_FB", "F", (73, 18), p("R16", 1), width=0.26)
    r.path("PRE_FB", "F", (66.6, 21.3), p("U3", 8), width=0.26)
    # Separate quiet reference return; both via annuli get In1 antipads.
    r.path("AGND", "F", p("R16", 2), (74.3, 21.6125), width=0.26)
    r.via("AGND", (74.3, 21.6125))
    r.path("AGND", "In4", (74.3, 21.6125), (74.3, 17), (64.3, 17), (63.4, 18.2), width=0.26)
    r.via("AGND", (63.4, 18.2))
    r.path("AGND", "F", (63.4, 18.2), p("U3", 4), width=0.26)
    # Ground spines accompany the saved In1 fill, making paths independently
    # checkable without treating a fill as an unverified connectivity oracle.
    for at in (
        (62.4, 18.25),
        (67.5, 18.3),
        (68.275, 18.3),
        (74.9, 25.5),
        (74.9, 26.275),
        (74.9, 24.75),
        (59.5, 25),
        (59.5, 32.75),
    ):
        r.via("AGND", at)
    r.path("AGND", "F", p("C29", 2), (62.4, 18.25), width=0.35)
    r.path("AGND", "F", p("C27", 2), (68.025, 18.3), (67.5, 18.3), (68.275, 18.3), width=0.8)
    r.path("AGND", "F", p("C28", 2), (74.9, 26.275), (74.9, 25.5), (74.9, 24.75), width=0.8)
    r.path("AGND", "F", p("C25", 2), (59.5, 25), width=0.8)
    r.path("AGND", "F", p("C26", 2), (59.5, 32.75), width=0.8)
    r.path(
        "AGND",
        "In1",
        (62.4, 18.25),
        (62.4, 22.6),
        (68.025, 22.6),
        (68.025, 18.3),
        (67.5, 18.3),
        (68.275, 18.3),
        width=0.8,
    )
    r.path("AGND", "In1", (68.025, 22.6), (74.9, 22.6), (74.9, 23.74), p("J3", 2), width=0.8)
    r.path("AGND", "In1", (62.4, 22.6), (59.5, 22.6), (59.5, 25), (59.5, 32.75), width=0.8)
    r.path("AGND", "In1", (74.9, 24.75), (74.9, 26.275), (74.9, 25.5), (74.9, 23.74), p("J3", 2), width=0.8)
    # Soft start and the duplicated receiving-end EN divider.
    r.path("PRE_SS", "F", p("U3", 7), (65.05, 20.5), (66.6, 20.5), (66.6, 19), width=0.26)
    r.via("PRE_SS", (66.6, 19))
    r.path("PRE_SS", "In3", (66.6, 19), (68.45, 25), width=0.26)
    r.via("PRE_SS", (68.45, 25))
    r.path("PRE_SS", "F", (68.45, 25), p("C24", 1), width=0.26)
    r.path("AGND", "F", p("C24", 2), (70.35, 25), width=0.26)
    r.via("AGND", (70.35, 25))
    r.path("AGND", "In1", (70.35, 25), (74.9, 25), (74.9, 25.5), width=0.26)
    r.path("SUPPLY_ENABLE", "F", p("U3", 2), (65.05, 18.4), width=0.26)
    r.via("SUPPLY_ENABLE", (65.05, 18.4))
    r.path("SUPPLY_ENABLE", "In3", (65.05, 18.4), (66, 16), (66, 11.5), (58, 11.5), width=0.26)
    r.path(
        "SUPPLY_ENABLE",
        "In2",
        (65.05, 18.4),
        (64.5, 18.4),
        (64.5, 23.6),
        (69.5, 23.6),
        (69.5, 24.8),
        width=0.26,
    )
    r.via("SUPPLY_ENABLE", (69.5, 24.8))
    r.path("SUPPLY_ENABLE", "B", p("R12", 2), p("R13", 1), (69.5, 24.8), width=0.26)
    r.path("POWER_READY", "B", p("R12", 1), (69.5, 19.6), width=0.26)
    r.via("POWER_READY", (69.5, 19.6))
    r.path("POWER_READY", "In2", (69.5, 19.6), (69.5, 20.4), (66, 20.4), (66, 12), (67.5, 11.75), width=0.26)
    r.via("POWER_READY", (67.5, 11.75))
    r.path("POWER_READY", "In3", (67.5, 11.75), (67.5, 1), (66.54, 1), width=0.26)
    r.path("AGND", "B", p("R13", 2), (75, 23.8), width=0.26)
    r.via("AGND", (75, 23.8))
    r.path("AGND", "In1", (75, 23.8), (74.9, 23.74), width=0.26)
