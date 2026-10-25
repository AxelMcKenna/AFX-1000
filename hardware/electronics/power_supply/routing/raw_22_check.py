"""Independent +/-22 V connection, layer and minimum-width requirements.

Length limits are geometric regression guards, not stability or EMC qualification.
"""

from ...common.sexpr import children, first

F = ("F.Cu",)
B = ("B.Cu",)
POWER = ("F.Cu", "B.Cu", "In2.Cu", "In4.Cu")
GND = ("F.Cu", "B.Cu", "In1.Cu")
PATHS = [
    ("hi_input_feed", "VIN_PROTECTED", ("J1", 1), ("C2", 1), 90, POWER),
    ("hi_boost_input", "VIN_PROTECTED", ("C2", 1), ("L1", 1), 12, F),
    ("hi_input_pair", "VIN_PROTECTED", ("C2", 1), ("C3", 1), 18, F),
    ("hi_cuk_input", "VIN_PROTECTED", ("C3", 1), ("L2", 1), 18, F),
    ("hi_bypass_feed", "VIN_PROTECTED", ("J1", 1), ("C4", 1), 70, POWER),
    ("hi_ic_bypass", "VIN_PROTECTED", ("C4", 1), ("U1", 8), 6, ("F.Cu", "B.Cu")),
    ("hi_boost_switch", "RAW_P_SW", ("U1", 10), ("L1", 2), 15, F),
    ("hi_boost_diode", "RAW_P_SW", ("U1", 10), ("D1", 2), 7, F),
    ("hi_positive_bulk_1", "RAW_P22", ("D1", 1), ("C5", 1), 18, ("F.Cu", "B.Cu", "In2.Cu")),
    ("hi_positive_bulk_2", "RAW_P22", ("D1", 1), ("C6", 1), 22, ("F.Cu", "B.Cu", "In2.Cu")),
    ("hi_positive_bypass", "RAW_P22", ("D1", 1), ("C7", 1), 22, ("F.Cu", "B.Cu", "In2.Cu")),
    ("hi_cuk_switch", "RAW_N_SW", ("U1", 6), ("L2", 2), 30, F),
    ("hi_cuk_transfer", "RAW_N_SW", ("U1", 6), ("C1", 1), 7, F),
    ("hi_cuk_inductor", "RAW_N_SW", ("L2", 2), ("C1", 1), 28, F),
    ("hi_cuk_diode", "CUK_NODE", ("D2", 2), ("C1", 2), 22, F),
    ("hi_cuk_choke", "CUK_NODE", ("C1", 2), ("L3", 1), 28, F),
    ("hi_negative_bulk_1", "RAW_N22", ("L3", 2), ("C8", 1), 40, ("F.Cu", "B.Cu", "In4.Cu")),
    ("hi_negative_bulk_2", "RAW_N22", ("L3", 2), ("C9", 1), 26, ("F.Cu", "B.Cu", "In4.Cu")),
    ("hi_negative_bypass", "RAW_N22", ("L3", 2), ("C10", 1), 46, ("F.Cu", "B.Cu", "In4.Cu")),
    ("hi_input_ground_1", "AGND", ("C2", 2), ("U1", 11), 25, GND),
    ("hi_input_ground_2", "AGND", ("C3", 2), ("U1", 11), 50, GND),
    ("hi_bypass_ground", "AGND", ("C4", 2), ("U1", 11), 30, GND),
    ("hi_positive_ground_1", "AGND", ("C5", 2), ("U1", 11), 32, GND),
    ("hi_positive_ground_2", "AGND", ("C6", 2), ("U1", 11), 32, GND),
    ("hi_positive_ground_3", "AGND", ("C7", 2), ("U1", 11), 50, GND),
    ("hi_negative_ground_1", "AGND", ("C8", 2), ("U1", 11), 70, GND),
    ("hi_negative_ground_2", "AGND", ("C9", 2), ("U1", 11), 42, GND),
    ("hi_negative_ground_3", "AGND", ("C10", 2), ("U1", 11), 36, GND),
    ("hi_diode_ground", "AGND", ("D2", 1), ("U1", 11), 18, GND),
    ("hi_feedback_reference", "AGND", ("U1", 5), ("U1", 11), 4, F),
    ("hi_quiet_divider_ground", "AGND", ("R3", 2), ("U1", 11), 32, ("F.Cu", "In3.Cu")),
    ("hi_quiet_bypass_ground", "AGND", ("C11", 2), ("U1", 11), 22, ("F.Cu", "B.Cu", "In3.Cu")),
    ("hi_reference_pins", "SW_REF_1V", ("U1", 2), ("U1", 3), 3, F),
    ("hi_reference_bypass", "SW_REF_1V", ("U1", 2), ("C11", 1), 9, ("F.Cu", "B.Cu")),
    ("hi_reference_divider", "SW_REF_1V", ("C11", 1), ("R4", 1), 14, B),
    ("hi_positive_sense", "RAW_P22", ("D1", 1), ("R1", 1), 60, ("F.Cu", "In2.Cu")),
    ("hi_positive_mid_arm", "RAW_P_RMID", ("R1", 2), ("R2", 1), 4, F),
    ("hi_positive_lower_arm", "RAW_P_FB", ("R2", 2), ("R3", 1), 4, F),
    ("hi_positive_feedback", "RAW_P_FB", ("R2", 2), ("U1", 1), 36, ("F.Cu", "In2.Cu")),
    ("hi_positive_feedforward_upper", "RAW_P22", ("C12", 1), ("D1", 1), 30, ("F.Cu", "B.Cu", "In2.Cu")),
    ("hi_positive_feedforward_lower", "RAW_P_FB", ("C12", 2), ("U1", 1), 24, ("F.Cu", "B.Cu", "In4.Cu")),
    ("hi_negative_feedback", "RAW_N_FB", ("R4", 2), ("U1", 4), 14, ("F.Cu", "B.Cu", "In2.Cu")),
    ("hi_negative_divider", "RAW_N_FB", ("R4", 2), ("R5", 1), 26, ("B.Cu", "In2.Cu")),
    ("hi_negative_sense", "RAW_N22", ("R5", 2), ("C10", 1), 20, ("B.Cu", "In2.Cu")),
    ("hi_negative_feedforward_upper", "RAW_N22", ("C14", 1), ("C10", 1), 28, ("B.Cu", "In2.Cu", "In3.Cu")),
    ("hi_negative_feedforward_lower", "RAW_N_FB", ("C14", 2), ("U1", 4), 28, ("F.Cu", "B.Cu")),
    ("hi_enable_feed", "5V_DIG_SRC", ("C18", 1), ("R6", 1), 100, ("F.Cu", "B.Cu", "In4.Cu")),
    ("hi_enable_pair", "5V_DIG_SRC", ("R6", 1), ("R7", 1), 12, B),
    ("hi_positive_enable", "RAW_P_SS", ("U1", 9), ("R6", 2), 35, ("F.Cu", "B.Cu")),
    ("hi_positive_start_cap", "RAW_P_SS", ("U1", 9), ("C13", 1), 50, ("F.Cu", "B.Cu")),
    ("hi_negative_enable", "RAW_N_SS", ("U1", 7), ("R7", 2), 35, ("F.Cu", "B.Cu")),
    ("hi_negative_start_cap", "RAW_N_SS", ("U1", 7), ("C15", 1), 50, ("F.Cu", "B.Cu")),
    ("hi_positive_start_ground", "AGND", ("C13", 2), ("U1", 11), 35, GND),
    ("hi_negative_start_ground", "AGND", ("C15", 2), ("U1", 11), 40, GND),
]
MINIMUM_WIDTHS = {
    **{name: 0.8 for name in ("hi_input_feed", "hi_boost_input", "hi_input_pair", "hi_cuk_input")},
    **{name: 0.35 for name in ("hi_bypass_feed", "hi_ic_bypass", "hi_bypass_ground")},
    **{name: 0.3 for name in ("hi_boost_switch", "hi_boost_diode", "hi_cuk_switch", "hi_cuk_transfer")},
    "hi_cuk_inductor": 0.6,
    **{
        name: 0.5
        for name in (
            "hi_positive_bulk_1",
            "hi_positive_bulk_2",
            "hi_positive_bypass",
            "hi_cuk_diode",
            "hi_cuk_choke",
            "hi_negative_bulk_1",
            "hi_negative_bulk_2",
            "hi_negative_bypass",
            "hi_input_ground_1",
            "hi_input_ground_2",
            "hi_positive_ground_1",
            "hi_positive_ground_2",
            "hi_positive_ground_3",
            "hi_negative_ground_1",
            "hi_negative_ground_2",
            "hi_negative_ground_3",
            "hi_diode_ground",
        )
    },
}


def component_faces(tree):
    expected = {"U1", "L1", "L2", "L3", "D1", "D2", "C1", "C2", "C3", "R1", "R2", "R3"}
    back = {*(f"C{i}" for i in range(4, 16)), "R4", "R5", "R6", "R7"}
    found = set()
    for fp in children(tree, "footprint"):
        ref = next(p[2] for p in children(fp, "property") if p[1] == "Reference")
        if ref in expected | back:
            layer = "F.Cu" if ref in expected else "B.Cu"
            assert first(fp, "layer")[1] == layer, (ref, "raw 22V component face changed")
            found.add(ref)
    assert found == expected | back
    return dict(front=len(expected), back=len(back))
