"""New bonded PEEK pedestal, independently removable saddle keepers."""


def parts(d, maximum=False, film_override=None):
    import cadquery as cq

    s = d["support"]
    cx, cy = s["foot_centre_xy"]
    film = (
        d["insulation"]["maximum_build_each_face_allocation_mm"]
        if maximum
        else s["planned_received_wrap_face_mm"]
    )
    if film_override is not None:
        film = film_override
    t = d["bar"]["thickness_range"][1] if maximum else d["bar"]["thickness"]
    w = d["bar"]["width_range"][1] if maximum else d["bar"]["width"]
    base = s["floor_z"] + s["bond_nominal_thickness"]
    feet = cq.Solid.makeBox(
        *s["foot_xy"],
        s["foot_thickness"],
        cq.Vector(cx - s["foot_xy"][0] / 2, cy - s["foot_xy"][1] / 2, base),
    )
    level = min(q[2] for q in s["saddles"].values()) - film
    lower = level - s["arm_vertical_thickness"]
    mast = cq.Solid.makeCylinder(
        s["mast_diameter"] / 2,
        level - base - s["foot_thickness"],
        cq.Vector(cx, cy, base + s["foot_thickness"]),
    )
    arm = cq.Solid.makeBox(
        s["arm_x"] - cx,
        s["arm_width"],
        s["arm_vertical_thickness"],
        cq.Vector(cx, cy - s["arm_width"] / 2, lower),
    )
    y0 = min(q[1] for q in s["saddles"].values())
    y1 = max(q[1] for q in s["saddles"].values())
    long = cq.Solid.makeBox(
        s["arm_width"],
        y1 - y0,
        s["arm_vertical_thickness"],
        cq.Vector(s["arm_x"] - s["arm_width"] / 2, y0, lower),
    )
    main = feet.fuse(mast, arm, long).clean()
    out = {}
    thread_cuts = []
    for name, q in s["saddles"].items():
        local_level = q[2] - film
        local_lower = local_level - s["arm_vertical_thickness"]
        if local_lower > lower:
            main = main.fuse(cq.Solid.makeBox(s["saddle_x_length"],s["saddle_y_length"],local_lower-lower,cq.Vector(q[0]-s["saddle_x_length"]/2,q[1]-s["saddle_y_length"]/2,lower))).clean()
        if q[0] < s["arm_x"]:
            main = main.fuse(
                cq.Solid.makeBox(
                    s["arm_x"] - q[0],
                    s["arm_width"],
                    s["arm_vertical_thickness"],
                    cq.Vector(q[0], q[1] - s["arm_width"] / 2, local_lower),
                )
            ).clean()
        floor = cq.Solid.makeBox(
            s["saddle_x_length"],
            s["saddle_y_length"],
            s["arm_vertical_thickness"],
            cq.Vector(q[0] - s["saddle_x_length"] / 2, q[1] - s["saddle_y_length"] / 2, local_lower),
        )
        top = q[2] + t + film + s["keeper_gap_allocation"]
        bearing = local_level + s["matched_screw_bearing_above_saddle_floor_mm"]
        keeper = cq.Solid.makeBox(
            s["saddle_x_length"],
            s["saddle_y_length"],
            bearing - top,
            cq.Vector(q[0] - s["saddle_x_length"] / 2, q[1] - s["saddle_y_length"] / 2, top),
        )
        for index, dy in enumerate(s.get("screw_y_offsets_by_saddle",{}).get(name,s["screw_y_offsets"])):
            x, y = q[0] + s["screw_x_offset_from_saddle"], q[1] + dy
            floor = floor.fuse(
                cq.Solid.makeCylinder(
                    s["saddle_screw_boss_diameter"] / 2, s["arm_vertical_thickness"], cq.Vector(x, y, local_lower)
                )
            )
            keeper = keeper.fuse(
                cq.Solid.makeCylinder(
                    s["saddle_screw_boss_diameter"] / 2, bearing - top, cq.Vector(x, y, top)
                )
            )
            floor = floor.cut(cq.Solid.makeCylinder(0.65, 3.2, cq.Vector(x, y, local_lower - 0.1)))
            thread_cuts.append(cq.Solid.makeCylinder(0.65, 3.2, cq.Vector(x, y, local_lower - 0.1)))
            keeper = keeper.cut(cq.Solid.makeCylinder(0.9, bearing - top + 0.2, cq.Vector(x, y, top - 0.1)))
            keeper = keeper.cut(cq.Solid.makeCone(0.9, 1.9, 1, cq.Vector(x, y, bearing - 1)))
            # ThroughM1.6 thread is a drawing callout; no helical BREP claim.
            length = s["screw_length_receiving_range_project_mm"][1] if maximum else s["screw_length_nominal"]
            recess = (
                s["screw_seating_recess_range_project_mm"][1]
                if maximum
                else s["head_seating_recess_below_keeper_top_mm"]
            )
            headtop = bearing if maximum else bearing - recess
            tip = bearing - recess - length
            # Supplier maxD3/H.96: .285rim plus .67590degree frustum.
            screw = (
                cq.Solid.makeCylinder(0.825, headtop - 0.96 - tip, cq.Vector(x, y, tip))
                .fuse(
                    cq.Solid.makeCone(0.825, 1.5, 0.675, cq.Vector(x, y, headtop - 0.96)),
                    cq.Solid.makeCylinder(1.5, 0.285, cq.Vector(x, y, headtop - 0.285)),
                )
                .clean()
            )
            out[name + "-SADDLE-SCREW" + str(index)] = screw
        # Matched side rails bound lateral travel, while the keeper leaves the
        # declared vertical gap and allows longitudinal thermal sliding.
        inner = w / 2 + film + s["maximum_received_lateral_or_vertical_float_mm"]
        for side in (-1, 1):
            y = q[1] + inner if side > 0 else q[1] - inner - 0.6
            floor = floor.fuse(
                cq.Solid.makeBox(
                    s["saddle_x_length"],
                    0.6,
                    top - local_level - s["keeper_gap_allocation"],
                    cq.Vector(q[0] - s["saddle_x_length"] / 2, y, local_level),
                )
            )
        main = main.fuse(floor).clean()
        out[name + "-SADDLE-KEEPER"] = keeper
    out["BONDED-PEDESTAL"] = main.cut(*thread_cuts).clean()
    assert all(obj.isValid() and len(obj.Solids()) == 1 for obj in out.values())
    return out
