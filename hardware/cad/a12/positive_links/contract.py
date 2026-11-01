"""Portable receiving/geometry contract; passing does not qualify hardware."""

from .analysis import area_screens
from .generate import direction


def problems(d):
    errors = []
    b = d["bar"]
    c = d["cap"]
    h = d["terminal_hardware"]
    for kind, value in area_screens(d).items():
        if value < b["minimum_net_normal_area"]:
            errors.append("insufficient copper " + kind)
    for name, row in d["paths"].items():
        p = row["points"]
        malformed = False
        for a, z in zip(p, p[1:]):
            try:
                direction(a, z)
            except AssertionError:
                errors.append(name + " non-orthogonal/zero segment")
                malformed = True
        if len(p) < 3 or len(row["end_refs"]) != 2:
            errors.append(name + " endpoints")
        if malformed:
            continue
        for i, (a, z) in enumerate(zip(p, p[1:])):
            if direction(a, z) == 2 and i > 0 and i + 2 < len(p):
                if direction(p[i - 1], a) != direction(z, p[i + 2]):
                    errors.append(name + " riser changes transverse axis and creates a narrow neck")
    radial_min = (c["inner_landing_diameter"] - c["inner_landing_tolerance"] - b["landing_range"][1]) / 2
    radial_max = (c["inner_landing_diameter"] + c["inner_landing_tolerance"] - b["landing_range"][0]) / 2
    if radial_min <= 0:
        errors.append("cap cannot receive maximum landing")
    if radial_max > c["fit_float_xy_allocation_mm"] + 1e-9:
        errors.append("cap radial motion exceeds envelope")
    if not c["landing_cavity_must_match_received_copper_thickness"]:
        errors.append("cap cavity must match received copper")
    down, up = c["landing_cavity_z_clearance_down_up_mm"]
    if down + 2 * c["dimension_tolerance"] > -c["fit_float_z_allocation_mm"][0] + 1e-9:
        errors.append("cap downward motion exceeds envelope")
    if up + c["dimension_tolerance"] > c["fit_float_z_allocation_mm"][1] + 1e-9:
        errors.append("cap upward motion exceeds envelope")
    roof = b["thickness_range"][1] + h["washer_thickness"] + h["head_height_envelope"] + c["roof_clearance"]
    axis = c["cross_bolt_axis_above_copper_bottom_mm"]
    walls = {
        "nut cavity floor": axis - 3.35 / 2 - roof - 2 * c["dimension_tolerance"],
        "nut cavity roof": c["bridge_top_above_copper_bottom_mm"]
        - axis
        - 3.35 / 2
        - 2 * c["dimension_tolerance"],
    }
    for k, v in walls.items():
        if v < c["minimum_wall"] - 1e-9:
            errors.append("insufficient " + k + " wall")
    if h["trial_torque_nm"] > h["maximum_manufacturer_torque_nm"]:
        errors.append("stud torque exceeds manufacturer")
    for key in [
        "electrical_thermal_qualified",
        "mechanical_lifetime_qualified",
        "fabrication_released",
        "selected_for_production",
    ]:
        if d[key]:
            errors.append("unmeasured release flag " + key)
    return errors
