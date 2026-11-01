"""Conservative convex support bounds, covering declared Cu/wrap endpoints."""

import json

from .generate import OUT, ROOT, load, sha


def rows(d):
    s = d["support"]
    film = d["insulation"]["maximum_build_each_face_allocation_mm"]
    zlo = 20.5 - film
    zhi = 20.5
    lower = zlo - s["arm_vertical_thickness"]
    low_keeper = 20.5 + d["bar"]["thickness_range"][0] + s["keeper_gap_allocation"]
    high_keeper = zhi + s["matched_screw_bearing_above_saddle_floor_mm"]
    boxes = []
    cyl = []

    def box(x, y, z, w, h, t):
        boxes.append([x, y, z, w, h, t])

    def cylinder(x, y, z, diam, h):
        cyl.append([x, y, z, diam, h])

    cx, cy = s["foot_centre_xy"]
    fw, fh = s["foot_xy"]
    base = s["floor_z"] + s["bond_nominal_thickness"]
    box(cx - fw / 2, cy - fh / 2, base, fw, fh, s["foot_thickness"])
    cylinder(cx, cy, base + s["foot_thickness"], s["mast_diameter"], zhi - base - s["foot_thickness"])
    box(cx, cy - s["arm_width"] / 2, lower, s["arm_x"] - cx, s["arm_width"], zhi - lower)
    ys = [q[1] for q in s["saddles"].values()]
    box(s["arm_x"] - s["arm_width"] / 2, min(ys), lower, s["arm_width"], max(ys) - min(ys), zhi - lower)
    inner_min = d["bar"]["width_range"][0] / 2 + s["maximum_received_lateral_or_vertical_float_mm"]
    outer_max = (
        d["bar"]["width_range"][1] / 2 + film + s["maximum_received_lateral_or_vertical_float_mm"] + 0.6
    )
    for q in s["saddles"].values():
        if q[0] < s["arm_x"]:
            box(q[0], q[1] - s["arm_width"] / 2, lower, s["arm_x"] - q[0], s["arm_width"], zhi - lower)
        box(
            q[0] - s["saddle_x_length"] / 2,
            q[1] - s["saddle_y_length"] / 2,
            lower,
            s["saddle_x_length"],
            s["saddle_y_length"],
            zhi - lower,
        )
        box(
            q[0] - s["saddle_x_length"] / 2,
            q[1] - s["saddle_y_length"] / 2,
            low_keeper,
            s["saddle_x_length"],
            s["saddle_y_length"],
            high_keeper - low_keeper,
        )
        for sign in (-1, 1):
            y = q[1] + inner_min if sign > 0 else q[1] - outer_max
            box(
                q[0] - s["saddle_x_length"] / 2,
                y,
                zlo,
                s["saddle_x_length"],
                outer_max - inner_min,
                20.5 + d["bar"]["thickness_range"][1] + film - zlo,
            )
        for dy in s["screw_y_offsets"]:
            x, y = q[0] + s["screw_x_offset_from_saddle"], q[1] + dy
            cylinder(x, y, lower, s["saddle_screw_boss_diameter"], zhi - lower)
            cylinder(x, y, low_keeper, s["saddle_screw_boss_diameter"], high_keeper - low_keeper)
            tip = (
                zlo
                + s["matched_screw_bearing_above_saddle_floor_mm"]
                - s["screw_seating_recess_range_project_mm"][1]
                - s["screw_length_receiving_range_project_mm"][1]
            )
            cylinder(x, y, tip, 1.65, high_keeper - tip)
            headlow = (
                zlo
                + s["matched_screw_bearing_above_saddle_floor_mm"]
                - s["screw_seating_recess_range_project_mm"][1]
                - s["screw_head_maximum_height"]
            )
            cylinder(x, y, headlow, s["screw_head_maximum_diameter"], high_keeper - headlow)
    return boxes, cyl


def main():
    import cadquery as cq

    d = load()
    boxes, cyl = rows(d)
    pieces = [cq.Solid.makeBox(w, h, t, cq.Vector(x, y, z)) for x, y, z, w, h, t in boxes]
    pieces += [cq.Solid.makeCylinder(diam / 2, h, cq.Vector(x, y, z)) for x, y, z, diam, h in cyl]
    bound = pieces[0].fuse(*pieces[1:]).clean()
    actual = cq.importers.importStep(str(OUT / "SUPPORT-ENVELOPE.step")).val()
    outside = actual.cut(bound).Volume()
    assert outside < 1e-7, outside
    r = dict(
        source_sha256={
            q.name: sha(q) for q in [ROOT / "design.json", ROOT / "bounds.py", ROOT / "support.py"]
        },
        boxes=boxes,
        cylinders=cyl,
        actual_sampled_support_outside_convex_union_mm3=outside,
        nominal_and_generated_extrema_contained=True,
        contained_actual_step_sha256=sha(OUT / "SUPPORT-ENVELOPE.step"),
        full_continuous_interval_basis="Each primitive range encloses Cu thickness1.0..1.4,width6.3..6.5,per-facewrap0..0.32,length5.8..6.2,headseating0..0.30 by monotoniccoordinate bounds. Holes/slots filled conservatively. Actual machining/material/strength/physical acceptance unproved.",
        physical_qualified=False,
    )
    (OUT / "support-bounds.json").write_text(json.dumps(r, indent=2) + "\n")
    print(json.dumps({"outside_mm3": outside, "boxes": len(boxes), "cylinders": len(cyl)}))


if __name__ == "__main__":
    main()
