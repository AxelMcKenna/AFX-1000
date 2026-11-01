"""Split PEEK terminal covers with captive cross-fasteners; no life approval."""

import math


def frame(d, name, end):
    points = d["paths"][name]["points"]
    q = points[0 if end == 0 else -1]
    neighbor = points[1 if end == 0 else -2]
    return q, 0 if abs(neighbor[0] - q[0]) > 0 else 90, neighbor


def global_shape(obj, q, angle):
    return obj.rotate((0, 0, 0), (0, 0, 1), angle).translate(q)


def hex_prism(cq, af, length, origin):
    radius = af / math.sqrt(3)
    points = [
        cq.Vector(
            origin[0] + radius * math.cos(i * math.pi / 3),
            origin[1],
            origin[2] + radius * math.sin(i * math.pi / 3),
        )
        for i in range(6)
    ]
    wire = cq.Wire.makePolygon(points + [points[0]])
    return cq.Solid.extrudeLinear(wire, [], cq.Vector(0, length, 0))


def pieces(d, name, end, maximum=False):
    import cadquery as cq

    q, angle, neighbor = frame(d, name, end)
    cap = d["cap"]
    h = d["terminal_hardware"]
    axis = cap["cross_bolt_axis_above_copper_bottom_mm"]
    roof = (
        d["bar"]["thickness_range"][1]
        + h["washer_thickness"]
        + h["head_height_envelope"]
        + cap["roof_clearance"]
    )
    offset = 2.7 if name == "ANA" and end == 0 else 0
    v = 4.0 if name == "DIG" and end == 1 else 0
    extra = 0.15 if maximum else 0
    down = 0.35 if maximum else 0
    up = 0.15 if maximum else 0
    top = (
        d["bar"]["thickness_range"][1]
        + h["washer_thickness"]
        + h["head_height_envelope"]
        + cap["roof_clearance"]
        + cap["minimum_wall"]
        + 2 * cap["dimension_tolerance"]
    )
    outer = cq.Solid.makeCylinder(
        cap["outer_diameter"] / 2 + extra, top + 1 + down + up, cq.Vector(0, 0, -1 - down)
    )
    if name == "DIG" and end == 0:
        outer = outer.cut(
            cq.Solid.makeBox(20, 30, 20, cq.Vector(cap["dig_e28_outer_flat_plus_x"] + extra, -15, -2))
        )
    bridge = cq.Solid.makeBox(
        8 + 2 * extra,
        8 + 2 * extra,
        cap["bridge_top_above_copper_bottom_mm"] - 4.4 + down + up,
        cq.Vector(offset - 4 - extra, v - 4 - extra, 4.4 - down),
    )
    outer = outer.fuse(bridge).clean()
    if maximum:
        # Conservative bounded metal hardware at the cross bolt; cap may move
        # -.30/+ .10Z and .10XY within its declared fit allowance.
        screwbox = cq.Solid.makeBox(3.3, 1.9, 3.5, cq.Vector(offset - 1.65, v - 5.75, axis - 1.85))
        nutbox = cq.Solid.makeBox(4.0, 1.6, 3.7, cq.Vector(offset - 2.0, v + 2.55, axis - 1.95))
        shaft = cq.Solid.makeBox(1.95, 8.6, 2.2, cq.Vector(offset - 0.975, v - 4.15, axis - 1.15))
        return {"ENVELOPE": global_shape(outer.fuse(screwbox, nutbox, shaft).clean(), q, angle)}
    # Receive/match the cavity to the actual copper thickness. A fixed1.95mm
    # cavity would permit0.9mm downward cap travel on1mm copper, exceeding the
    # declared -.30mm envelope. This gives .15down/.05up nominal total play.
    landing = cq.Solid.makeCylinder(
        cap["inner_landing_diameter"] / 2, d["bar"]["thickness"] + 0.2, cq.Vector(0, 0, -0.05)
    )
    if name == "DIG" and end == 0:
        landing = landing.cut(
            cq.Solid.makeBox(20, 30, 20, cq.Vector(cap["dig_e28_inner_flat_plus_x"], -15, -2))
        )
    cuts = [
        landing,
        cq.Solid.makeCylinder(cap["inner_head_diameter"] / 2, roof + 1.05, cq.Vector(0, 0, -1.05)),
    ]
    sign = 1 if ((neighbor[0] - q[0]) if angle == 0 else (neighbor[1] - q[1])) > 0 else -1
    cuts.append(cq.Solid.makeBox(20, 8, 2.4, cq.Vector(0 if sign > 0 else -20, -4, -0.4)))
    cuts.append(cq.Solid.makeCylinder(0.9, 10, cq.Vector(offset, v - 5, axis), cq.Vector(0, 1, 0)))
    cuts.append(hex_prism(cq, 3.35, 1.55, (offset, v + 2.55, axis)))
    shell = outer.cut(*cuts).clean()
    first = shell.intersect(cq.Solid.makeBox(40, 20 + v, 20, cq.Vector(-20, -20, -2)))
    second = shell.intersect(cq.Solid.makeBox(40, 20, 20, cq.Vector(-20, v, -2)))
    for x in [offset - 2.5, offset + 2.5]:
        first = first.fuse(cq.Solid.makeCylinder(0.5, 1.1, cq.Vector(x, v - 0.1, axis), cq.Vector(0, 1, 0)))
        second = second.cut(
            cq.Solid.makeCylinder(0.55, 1.25, cq.Vector(x, v - 0.01, axis), cq.Vector(0, 1, 0))
        )
    shaft = cq.Solid.makeCylinder(0.825, 8, cq.Vector(offset, v - 4, axis), cq.Vector(0, 1, 0))
    head = cq.Solid.makeCylinder(1.5, 1.6, cq.Vector(offset, v - 5.6, axis), cq.Vector(0, 1, 0))
    nut = hex_prism(cq, 3.2, 1.3, (offset, v + 2.7, axis)).cut(
        cq.Solid.makeCylinder(0.8, 1.5, cq.Vector(offset, v + 2.6, axis), cq.Vector(0, 1, 0))
    )
    out = {
        "HALF-A": first.clean(),
        "HALF-B": second.clean(),
        "CROSS-SCREW": shaft.fuse(head).clean(),
        "NUT": nut,
    }
    assert all(s.isValid() and len(s.Solids()) == 1 for s in out.values())
    return {k: global_shape(v, q, angle) for k, v in out.items()}
