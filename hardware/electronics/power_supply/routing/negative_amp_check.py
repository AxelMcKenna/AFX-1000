"""Negative target amplifier bypass, HF feedback and supply contracts."""

from ...common.sexpr import children, first

B = ("B.Cu",)
ALL = ("F.Cu", "B.Cu", "In1.Cu", "In2.Cu", "In3.Cu", "In4.Cu")
PATHS = [
    ("negative_amp_local_supply", "RAW_N22", ("C61", 1), ("U6", 4), 10, B),
    ("negative_amp_local_return", "AGND", ("C61", 2), ("U6", 8), 6, B),
    ("negative_amp_bulk_supply", "RAW_N22", ("C62", 1), ("C61", 1), 40, ALL),
    ("negative_amp_bulk_return", "AGND", ("C62", 2), ("C61", 2), 60, ALL),
    ("negative_amp_raw_source", "RAW_N22", ("C8", 1), ("U6", 4), 60, ALL),
    ("negative_amp_power_return", "AGND", ("U6", 8), ("U13", 11), 35, ALL),
    ("n19_hf_feedback_out", "N19_DRIVE", ("U6", 1), ("C49", 1), 8, B),
    ("n19_hf_feedback_inv", "N19_FB", ("U6", 2), ("C49", 2), 9, B),
    ("n12_hf_feedback_out", "N12_DRIVE", ("U6", 7), ("C54", 1), 12, B),
    ("n12_hf_feedback_inv", "N12_FB", ("U6", 6), ("C54", 2), 18, ALL),
    ("n19_ratio_middle", "N19_RMID", ("R34", 2), ("R35", 1), 3, B),
    ("n19_ratio_lower", "N19_FB", ("R35", 2), ("R36", 1), 4, B),
    ("n12_ratio_middle", "N12_RMID", ("R39", 2), ("R40", 1), 4, B),
]
MINIMUM_WIDTHS = {p[0]: 0.35 if p[0].startswith("negative_amp") else 0.26 for p in PATHS}


def component_faces(tree):
    expected = {"U6", "C49", "C54", "C61", "C62"}
    found = {}
    for fp in children(tree, "footprint"):
        props = {p[1]: p[2] for p in children(fp, "property")}
        ref = props["Reference"]
        if ref in expected:
            assert first(fp, "layer")[1] == "B.Cu", (ref, "negative target amplifier face changed")
            if ref == "U6":
                assert props["Value"] == "OPA2192ID"
                actual = {str(p[1]): str(first(p, "net")[-1]) for p in children(fp, "pad")}
                assert actual["4"] == "/RAW_N22" and actual["8"] == "/AGND", (
                    "Negative amplifier supply must not span both raw rails"
                )
            found[ref] = "B.Cu"
    assert set(found) == expected
    return found
