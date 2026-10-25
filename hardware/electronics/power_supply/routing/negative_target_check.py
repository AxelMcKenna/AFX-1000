"""Independent negative DC-target connectivity and Kelvin-return requirements."""

from ...common.sexpr import children, first
from .analog_5v_check import kelvin_separation
from .negative_reference_check import reference_return

ALL = ("F.Cu", "B.Cu", "In1.Cu", "In2.Cu", "In3.Cu", "In4.Cu")
QUIET = ("F.Cu", "B.Cu", "In2.Cu", "In3.Cu")
PATHS = []
MINIMUM_WIDTHS = {}


def path(name, net, start, end, limit, width=0.26, layers=ALL):
    PATHS.append((name, net, start, end, limit, layers))
    MINIMUM_WIDTHS[name] = width


for prefix, reg, iso, upper, middle, lower, cap, out, inv in (
    ("n19", "U10", "R37", "R34", "R35", "R36", "C50", 1, 2),
    ("n12", "U11", "R42", "R39", "R40", "R41", "C55", 7, 6),
):
    rail = prefix.upper()
    path(prefix + "_isolation_drive", rail + "_DRIVE", ("U6", out), (iso, 1), 24, layers=("B.Cu",))
    path(prefix + "_set_drive", rail + "_SET", (iso, 2), (reg, 4), 60, 0.15)
    path(prefix + "_set_kelvin", rail + "_SET", (upper, 1), (reg, 4), 60, 0.15)
    path(prefix + "_set_filter", rail + "_SET", (cap, 1), (reg, 4), 45, 0.15)
    path(prefix + "_feedback_inv", rail + "_FB", (middle, 2), ("U6", inv), 55)
    path(prefix + "_divider_return", "AGND", (lower, 2), ("J2", 2), 140, layers=QUIET)
    path(prefix + "_filter_return", "AGND", (cap, 2), ("J2", 2), 140, layers=QUIET)
path("n12_ratio_lower", "N12_FB", ("R40", 2), ("R41", 1), 45)


def set_kelvin(tree):
    return {
        "N19": kelvin_separation(tree, "U10", 4, "N19_SET", "R37", "R34"),
        "N12": kelvin_separation(tree, "U11", 4, "N12_SET", "R42", "R39"),
    }


def quiet_return(tree):
    return reference_return(
        tree, (("U12", "6"), ("C33", "2"), ("R36", "2"), ("C50", "2"), ("R41", "2"), ("C55", "2"))
    )


def native_connections(drc):
    names = {f"/{rail}_{suffix}" for rail in ("N19", "N12") for suffix in ("SET", "DRIVE", "RMID", "FB")}
    assert not any(any(name + "]" in str(item) for name in names) for item in drc["unconnected_items"]), (
        "Negative target control net has native open connections"
    )
    return dict(
        control_nets_native_open_items=0,
        dc_target_routing_complete=True,
        regulator_power_and_output_complete=not bool(drc["unconnected_items"]),
        noise_or_loop_stability_qualified=False,
    )


def component_faces(tree):
    expected = {"R34", "R35", "R36", "R37", "C50", "R39", "R40", "R41", "R42", "C55", "U10", "U11"}
    found = {}
    for f in children(tree, "footprint"):
        ref = next(p[2] for p in children(f, "property") if p[1] == "Reference")
        if ref in expected:
            face = "F.Cu" if ref == "U11" else "B.Cu"
            assert first(f, "layer")[1] == face, (ref, "negative target component face changed")
            found[ref] = face
    assert set(found) == expected
    assert not any("_ROUTE" in str(n[2]) for n in children(tree, "net")), (
        "Routing masks must not add schematic nets"
    )
    return found
