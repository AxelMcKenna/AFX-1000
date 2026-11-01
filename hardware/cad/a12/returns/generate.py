"""Machined copper returns and matched-height insulating retention geometry."""

import argparse
import copy
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[3]
OUT = ROOT / "generated"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load():
    return json.loads((ROOT / "design.json").read_text())


def points(d, name):
    path = d["paths"][name]
    begin, end = path["board_end"]
    a, b = path["ramp_indices"]
    low = (
        d["assembled_board_bottom_z_mm"][begin]
        + d["native_boards"][begin]["thickness"]
        + d["e28_stud_body_height_nominal_mm"]
    )
    high = (
        d["assembled_board_bottom_z_mm"][end]
        + d["native_boards"][end]["thickness"]
        + d["p03_stud_body_height_nominal_mm"]
    )
    low = d.get("assembled_terminal_top_override_z_mm", {}).get(begin, low)
    high = d.get("assembled_terminal_top_override_z_mm", {}).get(end, high)
    assert a + 1 == b
    return [[*xy, low if i <= a else high] for i, xy in enumerate(path["xy"])]


def seat(d, name, x):
    p = points(d, name)
    a, b = d["paths"][name]["ramp_indices"]
    left, right = p[a], p[b]
    return left[2] + (right[2] - left[2]) * (x - left[0]) / (right[0] - left[0])


def corner_disks(d, name):
    p = points(d, name)
    answer = []
    for i, q in enumerate(p):
        endpoint = i in (0, len(p) - 1)
        if endpoint:
            r = d["bar"]["landing_diameter"] / 2
            drop = 0
        else:
            a, b = p[i - 1], p[i + 1]
            incoming = [q[j] - a[j] for j in range(3)]
            outgoing = [b[j] - q[j] for j in range(3)]
            if abs(incoming[0] * outgoing[1] - incoming[1] * outgoing[0]) < 1e-9:
                continue
            r = d["bar"]["width"] / 2
            drop = r * max(
                abs(incoming[2]) / math.hypot(*incoming[:2]), abs(outgoing[2]) / math.hypot(*outgoing[:2])
            )
        answer.append([q[0], q[1], q[2] - drop, 2 * r, d["bar"]["thickness"] + drop])
    return answer


def geometry(d):
    report = {}
    bar = d["bar"]
    minbulk = (bar["width"] - bar["width_tolerance"]) * (bar["thickness"] - bar["thickness_tolerance"])
    neck = (
        bar["landing_diameter"] - bar["landing_tolerance"] - bar["hole_diameter"] - bar["hole_tolerance"]
    ) * (bar["thickness"] - bar["thickness_tolerance"])
    for name, path in d["paths"].items():
        p = points(d, name)
        length = sum(math.dist(a, b) for a, b in zip(p, p[1:]))
        a, b = path["ramp_indices"]
        ramp = math.dist(p[a][:2], p[b][:2])
        maxrise = max(
            d["p03_permitted_measured_plane_z_mm"][1] - d["assembled_board_bottom_z_mm"]["E28"],
            abs(p[-1][2] - p[0][2]),
        )
        normal = minbulk / math.sqrt(1 + (maxrise / ramp) ** 2)
        edge_loss = 4 * bar["maximum_edge_break_mm"] ** 2
        lower = min(neck, normal) - edge_loss
        finished = length + bar["landing_diameter"]
        rho20 = 1 / bar["conductivity_receiving_allocation_ms_per_m"]
        rhohot = rho20 * (
            1
            + bar["resistivity_temperature_coefficient_assumed_per_k"] * (bar["dc_screen_temperature_c"] - 20)
        )
        report[name] = dict(
            points_mm=p,
            corner_disk_solids_mm=corner_disks(d, name),
            centreline_length_mm=length,
            conservative_finished_path_length_mm=finished,
            maximum_rise_mm=maxrise,
            ramp_run_mm=ramp,
            minimum_bulk_vertical_section_mm2=minbulk,
            minimum_hole_neck_section_mm2=neck,
            minimum_ramp_normal_section_mm2=normal,
            minimum_normal_section_mm2=lower,
            edge_break_area_deduction_mm2=edge_loss,
            normal_section_allocation_satisfied=lower >= bar["minimum_normal_area_allocation_mm2"],
            length_allocation_satisfied=finished <= path["finished_length_limit_mm"],
            one_dimensional_dc_screen_at20c_mohm=rho20 * (finished / 1000) / lower * 1000,
            one_dimensional_dc_screen_at_declared_hot_c_mohm=rhohot * (finished / 1000) / lower * 1000,
            dc_model_scope="Uniform1D resistivity/area screen; excludes bend/landing current crowding,plating/contact/solder/PCB resistance and RF effects; not a rigorous3D assembled resistance bound",
            material_conductivity_certificate_received=False,
            dc_or_joint_qualified=False,
        )
    return report


def assembly_stack(d):
    h = d["terminal_hardware"]
    b = d["bar"]
    r = d["retainers"]
    electrical = (
        2 * h["terminal_assembly_resistance_allocation_mohm"]
        + b["bar_resistance_allocation_mohm"]
        + h["pcb_access_resistance_allocation_mohm"]
    )
    j = math.pi * (r["stem_diameter"] ** 4 - 2**4) / 32
    # An annular3mm PEEK stem must never be the reaction fixture for M3 joint torque.
    return dict(
        m3_nominal_thread_engagement_mm=h["length"] - b["thickness"] - h["washer_nominal_thickness"],
        m3_usable_stud_thread_assumed_mm=None,
        stud_thread_depth_original_drawing_approved=False,
        nominal_p03_head_top_z_mm=points(d, "ANA")[-1][2]
        + b["thickness"]
        + h["washer_nominal_thickness"]
        + h["head_max_height"],
        m2_countersink_head_rim_envelope_mm=[3.8, 0.3, 0.9],
        m2_nominal_head_recess_mm=(r["base_countersink_diameter"] - 2) / 2 - 1.2,
        m2_trial_thread_engagement_mm=10 - 6.2 - ((r["base_countersink_diameter"] - 2) / 2 - 1.2),
        cap_minimum_gap_allocated_mm=r["cap_nominal_above_bar_gap"] - r["cap_gap_error_allocation"],
        cap_gap_allocation_satisfied=r["cap_nominal_above_bar_gap"] - r["cap_gap_error_allocation"]
        >= r["cap_required_min_gap_allocation"],
        complete_return_allocated_mohm=electrical,
        electrical_allocation_fits_target=electrical <= h["complete_return_target_mohm"],
        hypothetical_stem_shear_under_m3_torque_mpa=h["trial_torque_nm"]
        * 1000
        * (r["stem_diameter"] / 2)
        / j,
        hypothetical_stem_shear_under_base_trial_torque_mpa=r["base_trial_torque_nm"]
        * 1000
        * (r["stem_diameter"] / 2)
        / j,
        indicative_peek_shear_reference_mpa=55,
        peek_properties_are_guaranteed_allowables=False,
        m3_torque_reaction_through_post_allowed=False,
        temporary_holding_fixture_required=True,
        physical_fit_verified=False,
        electrical_joint_qualified=False,
        mechanical_stability_qualified=False,
    )


def export(d):
    from importlib.metadata import version

    import cadquery as cq

    def wire(coords):
        return cq.Wire.makePolygon([cq.Vector(*p) for p in coords], close=True)

    def loft(a, b, width, thickness):
        dx, dy = b[0] - a[0], b[1] - a[1]
        length = math.hypot(dx, dy)
        nx, ny = -dy / length * width / 2, dx / length * width / 2

        def end(p):
            return wire(
                [
                    (p[0] + nx, p[1] + ny, p[2]),
                    (p[0] - nx, p[1] - ny, p[2]),
                    (p[0] - nx, p[1] - ny, p[2] + thickness),
                    (p[0] + nx, p[1] + ny, p[2] + thickness),
                ]
            )

        return cq.Solid.makeLoft([end(a), end(b)], ruled=True)

    def sloped_box(x, y, w, h, zleft, zright, top_left, top_right):
        a = wire([(x, y, zleft), (x, y + h, zleft), (x, y + h, top_left), (x, y, top_left)])
        b = wire(
            [(x + w, y, zright), (x + w, y + h, zright), (x + w, y + h, top_right), (x + w, y, top_right)]
        )
        return cq.Solid.makeLoft([a, b], ruled=True)

    def save(shape, label):
        assert shape.isValid() and len(shape.Solids()) == 1, (label, "Invalid or disjoint solid")
        cq.exporters.export(shape, str(OUT / (label + ".step")))
        cq.exporters.export(shape, str(OUT / (label + ".stl")), tolerance=0.01, angularTolerance=0.08)
        back = cq.importers.importStep(str(OUT / (label + ".step"))).val()
        assert back.isValid() and abs(back.Volume() - shape.Volume()) < 1e-5
        return dict(
            volume_mm3=shape.Volume(),
            valid_single_solid=True,
            step_roundtrip_volume_matches=True,
            bbox_min_mm=[shape.BoundingBox().xmin, shape.BoundingBox().ymin, shape.BoundingBox().zmin],
            bbox_max_mm=[shape.BoundingBox().xmax, shape.BoundingBox().ymax, shape.BoundingBox().zmax],
        )

    result = {}
    assembled = []
    for name in d["paths"]:
        p = points(d, name)
        bar = d["bar"]
        t = bar["thickness"]
        w = bar["width"]
        members = [loft(a, b, w, t) for a, b in zip(p, p[1:])]
        for x, y, z, diam, height in corner_disks(d, name):
            members.append(cq.Solid.makeCylinder(diam / 2, height, cq.Vector(x, y, z)))
        copper = members[0].fuse(*members[1:]).clean()
        for q in (p[0], p[-1]):
            copper = copper.cut(
                cq.Solid.makeCylinder(bar["hole_diameter"] / 2, t + 0.2, cq.Vector(q[0], q[1], q[2] - 0.1))
            )
        copper = copper.clean()
        # Actual OCC sections of the manufactured minimum-dimension core,
        # including bend bisectors: straight-section arithmetic cannot detect
        # a missing outer corner at a butt-joined ramp end.
        small = copy.deepcopy(d)
        sb = small["bar"]
        for key, tolerance in [
            ("width", "width_tolerance"),
            ("thickness", "thickness_tolerance"),
            ("landing_diameter", "landing_tolerance"),
        ]:
            sb[key] -= sb[tolerance]
        sb["hole_diameter"] += sb["hole_tolerance"]
        sm = [loft(a, b, sb["width"], sb["thickness"]) for a, b in zip(p, p[1:])]
        for x, y, z, diam, height in corner_disks(small, name):
            sm.append(cq.Solid.makeCylinder(diam / 2, height, cq.Vector(x, y, z)))
        core = sm[0].fuse(*sm[1:]).clean()
        for q in (p[0], p[-1]):
            core = core.cut(
                cq.Solid.makeCylinder(
                    sb["hole_diameter"] / 2, sb["thickness"] + 0.2, cq.Vector(q[0], q[1], q[2] - 0.1)
                )
            )

        def unit(v):
            length = math.sqrt(sum(x * x for x in v))
            return [x / length for x in v]

        samples = []
        samples.append(("left_hole", p[0], unit([p[1][j] - p[0][j] for j in range(3)])))
        samples.append(("right_hole", p[-1], unit([p[-1][j] - p[-2][j] for j in range(3)])))
        for i, (a, b) in enumerate(zip(p, p[1:])):
            samples.append(
                (f"segment{i}", [(a[j] + b[j]) / 2 for j in range(3)], unit([b[j] - a[j] for j in range(3)]))
            )
        for i in range(1, len(p) - 1):
            a = unit([p[i][j] - p[i - 1][j] for j in range(3)])
            b = unit([p[i + 1][j] - p[i][j] for j in range(3)])
            samples.append((f"joint{i}", p[i], unit([a[j] + b[j] for j in range(3)])))
        witnesses = []
        for label, position, normal in samples:
            centre = [*position]
            centre[2] += sb["thickness"] / 2
            slab = (
                cq.Workplane(cq.Plane(origin=cq.Vector(*centre), normal=cq.Vector(*normal)))
                .rect(40, 40)
                .extrude(0.0005, both=True)
                .val()
            )
            area = core.intersect(slab).Volume() / 0.001
            witnesses.append(dict(section=label, normal=normal, core_area_mm2=area))
        result[name + "_minimum_core_section_witnesses"] = witnesses
        assert min(r["core_area_mm2"] for r in witnesses) >= 20, (name, witnesses)
        label = f"AFX-A12-R01-{name}-BAR"
        result[label] = save(copper, label)
        assembled.append(copper)
        for end_index, q in enumerate((p[0], p[-1])):
            wh = d["terminal_hardware"]["washer_nominal_thickness"]
            head_z = q[2] + t + wh
            washer = cq.Solid.makeCylinder(3.5, wh, cq.Vector(q[0], q[1], q[2] + t)).cut(
                cq.Solid.makeCylinder(1.6, wh + 0.2, cq.Vector(q[0], q[1], q[2] + t - 0.1))
            )
            screw = (
                cq.Solid.makeCylinder(1.5, 8, cq.Vector(q[0], q[1], head_z - 8))
                .fuse(cq.Solid.makeCylinder(3, 2.52, cq.Vector(q[0], q[1], head_z)))
                .clean()
            )
            result[f"{name}_END{end_index}_WASHER"] = save(
                washer, f"AFX-A12-R01-{name}-END{end_index}-WASHER"
            )
            result[f"{name}_END{end_index}_SCREW"] = save(screw, f"AFX-A12-R01-{name}-END{end_index}-SCREW")
            assembled.extend([washer, screw])
        r = d["retainers"]
        cx, cy = r["locations"][name]
        x, y = cx - r["head_x_width"] / 2, cy - r["head_y_length"] / 2
        zl = seat(d, name, x) - r["nominal_under_bar_gap"]
        zr = seat(d, name, x + r["head_x_width"]) - r["nominal_under_bar_gap"]
        channel_height = t + r["nominal_under_bar_gap"] + r["cap_nominal_above_bar_gap"]
        head = sloped_box(
            x, y, 4, 14, r["stem_top_z"], r["stem_top_z"], zl + channel_height, zr + channel_height
        )
        post = head.fuse(
            cq.Solid.makeCylinder(r["stem_diameter"] / 2, r["stem_top_z"], cq.Vector(cx, cy, 0))
        ).clean()
        channel = sloped_box(
            x - 0.01,
            cy - r["channel_y_width"] / 2,
            4.02,
            r["channel_y_width"],
            seat(d, name, x - 0.01) - r["nominal_under_bar_gap"],
            seat(d, name, x + 4.01) - r["nominal_under_bar_gap"],
            30,
            30,
        )
        post = post.cut(channel)
        post = post.cut(cq.Solid.makeCylinder(0.8, 5.8, cq.Vector(cx, cy, -0.01)))
        for off in (-r["cap_screw_y_offset"], r["cap_screw_y_offset"]):
            post = post.cut(
                cq.Solid.makeCylinder(
                    0.65,
                    5.3,
                    cq.Vector(cx, cy + off, seat(d, name, cx) + t + r["cap_nominal_above_bar_gap"] - 5.2),
                )
            )
        post = post.clean()
        label = f"AFX-A12-R01-{name}-POST"
        result[label] = save(post, label)
        assembled.append(post)
        capbottomleft = zl + channel_height
        capbottomright = zr + channel_height
        captop = max(capbottomleft, capbottomright) + r["cap_min_vertical_thickness"]
        cap = sloped_box(x, y, 4, 14, capbottomleft, capbottomright, captop, captop)
        for off in (-r["cap_screw_y_offset"], r["cap_screw_y_offset"]):
            cap = cap.cut(
                cq.Solid.makeCylinder(
                    r["cap_hole_diameter"] / 2, 4, cq.Vector(cx, cy + off, capbottomleft - 0.1)
                )
            )
        cap = cap.clean()
        label = f"AFX-A12-R01-{name}-CAP"
        result[label] = save(cap, label)
        assembled.append(cap)
        for index, off in enumerate((-r["cap_screw_y_offset"], r["cap_screw_y_offset"])):
            bolt = (
                cq.Solid.makeCylinder(0.8, 5, cq.Vector(cx, cy + off, captop - 5))
                .fuse(cq.Solid.makeCylinder(1.5, 1.6, cq.Vector(cx, cy + off, captop)))
                .clean()
            )
            result[f"{name}_CAP_SCREW{index}"] = save(bolt, f"AFX-A12-R01-{name}-CAP-SCREW{index}")
            assembled.append(bolt)
        base_bolt = (
            cq.Solid.makeCylinder(1.9, 0.3, cq.Vector(cx, cy, -6.2))
            .fuse(cq.Solid.makeCone(1.9, 1, 0.9, cq.Vector(cx, cy, -5.9)))
            .fuse(cq.Solid.makeCylinder(1, 8.8, cq.Vector(cx, cy, -5)))
            .clean()
        )
        result[name + "_BASE_SCREW"] = save(base_bolt, f"AFX-A12-R01-{name}-BASE-SCREW")
        assembled.append(base_bolt)
        result[name + "_seat"] = dict(
            left_bottom_z=zl,
            right_bottom_z=zr,
            cap_top_z=captop,
            copper_to_cap_nominal_gap_mm=r["cap_nominal_above_bar_gap"],
            cap_screw_nominal_engagement_mm=5
            - (captop - (seat(d, name, cx) + t + r["cap_nominal_above_bar_gap"])),
            post_lower_bore_is_tap_drill_not_thread_brep=True,
            physical_fit_verified=False,
        )
    assembly = cq.Compound.makeCompound(assembled)
    cq.exporters.export(assembly, str(OUT / "AFX-A12-R01-ASSEMBLY.step"))
    cq.exporters.export(assembly, str(OUT / "AFX-A12-R01-ASSEMBLY.stl"))
    cq.exporters.export(
        assembly,
        str(OUT / "assembly-isometric.svg"),
        opt={
            "width": 1200,
            "height": 650,
            "projectionDir": (1, -1, 1),
            "showHidden": False,
            "strokeWidth": 0.3,
        },
    )
    result["versions"] = dict(cadquery=version("cadquery"), ocp=version("cadquery-ocp"))
    result["physical_fit_verified"] = False
    result["fabrication_released"] = False
    return result


def scad(d):
    # Independent exact segment polyhedra, with circular terminal/corner solids.
    rows = []
    for name in d["paths"]:
        p = points(d, name)
        w = d["bar"]["width"]
        t = d["bar"]["thickness"]
        segments = []
        for a, b in zip(p, p[1:]):
            dx, dy = b[0] - a[0], b[1] - a[1]
            length = math.hypot(dx, dy)
            nx, ny = -dy / length * w / 2, dx / length * w / 2
            v = [
                [q[0] + s * nx, q[1] + s * ny, q[2] + zz]
                for q in (a, b)
                for zz, s in ((0, -1), (0, 1), (t, 1), (t, -1))
            ]
            segments.append(v)
        disks = corner_disks(d, name)
        rows.append(
            f"""module return_{name.lower()}_bar(){{difference(){{union(){{for(v={json.dumps(segments)})polyhedron(points=v,faces=[[1,2,3,0],[7,6,5,4],[4,5,1,0],[5,6,2,1],[6,7,3,2],[7,4,0,3]],convexity=10);for(q={json.dumps(disks)})translate([q[0],q[1],q[2]])cylinder(d=q[3],h=q[4],$fn=96);}}for(q={json.dumps([p[0], p[-1]])})translate([q[0],q[1],q[2]-.1])cylinder(d=4,h={t + 0.2},$fn=64);}}}}"""
        )
    rows.append("module return_bars(){return_ana_bar();return_dig_bar();}")
    # Exported exact STEP-tessellated PEEK parts remain source-hashed evidence.
    rows.append(
        "module return_retention(){"
        + "".join(f'import("AFX-A12-R01-{n}-{p}.stl");' for n in d["paths"] for p in ("POST", "CAP"))
        + "}"
    )
    rows.append(
        "module return_fasteners(){"
        + "".join(
            f'import("AFX-A12-R01-{n}-{p}.stl");'
            for n in d["paths"]
            for p in (
                "BASE-SCREW",
                "CAP-SCREW0",
                "CAP-SCREW1",
                "END0-SCREW",
                "END1-SCREW",
                "END0-WASHER",
                "END1-WASHER",
            )
        )
        + "}"
    )
    rows.append(
        "module return_assembly(){color([.75,.4,.15])return_bars();color([.8,.75,.55])return_retention();color([.6,.6,.6])return_fasteners();}"
    )
    rows.append(
        "module return_floor_windows(){"
        + "".join(
            f"translate([{x},{y},-.01])cylinder(d=3.5,h=2.82,$fn=64);"
            for x, y in d["retainers"]["locations"].values()
        )
        + "}"
    )
    (OUT / "returns.scad").write_text("\n".join(rows) + "\n")
    (OUT / "preview.scad").write_text(
        'include <returns.scad>\npart="assembly";\nif(part=="assembly")return_assembly();\nif(part=="bars")return_bars();\n'
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--p03-plane", type=float)
    parser.add_argument("--e28-plane", type=float)
    parser.add_argument("--e28-terminal-top", type=float)
    parser.add_argument("--p03-terminal-top", type=float)
    args = parser.parse_args()
    d = load()
    for key, value in [("P03", args.p03_plane), ("E28", args.e28_plane)]:
        if value is not None:
            d["assembled_board_bottom_z_mm"][key] = value
    d["assembled_terminal_top_override_z_mm"] = {
        key: value
        for key, value in [("E28", args.e28_terminal_top), ("P03", args.p03_terminal_top)]
        if value is not None
    }
    if args.p03_plane is not None:
        assert 6.3 <= args.p03_plane <= 6.7
    OUT.mkdir(exist_ok=True)
    g = geometry(d)
    assert all(
        r["normal_section_allocation_satisfied"] and r["length_allocation_satisfied"] for r in g.values()
    )
    record = export(d)
    scad(d)
    (OUT / "geometry.json").write_text(
        json.dumps(
            dict(
                design_sha256=sha(ROOT / "design.json"),
                effective_measured_plane_inputs=d["assembled_board_bottom_z_mm"],
                effective_terminal_top_override_z_mm=d["assembled_terminal_top_override_z_mm"],
                bars=g,
                assembly_stack=assembly_stack(d),
                physical_fit_verified=False,
                electrical_joint_qualified=False,
            ),
            indent=2,
        )
        + "\n"
    )
    (OUT / "cad-verification.json").write_text(json.dumps(record, indent=2) + "\n")
    interface = dict(
        revision=d["revision"],
        coordinate_basis="Housing/native+Y; no implicit Cartesian flip",
        measured_board_planes=d["assembled_board_bottom_z_mm"],
        measured_terminal_top_overrides=d["assembled_terminal_top_override_z_mm"],
        bar_points={n: points(d, n) for n in d["paths"]},
        retained_floor_windows=[
            dict(center_xy_mm=xy, diameter_mm=3.5, z_range_mm=[-0.01, 2.81])
            for xy in d["retainers"]["locations"].values()
        ],
        metal_base_attachments=[
            dict(
                center_xy_mm=xy,
                through_diameter_mm=2.4,
                csk_diameter_mm=4.8,
                csk_angle_degrees=90,
                csk_face="underside",
                screw="Accu SPK-M2-10-A2",
                plate_thickness_mm=6.2,
                fin_exclusion_radius_mm=4,
            )
            for xy in d["retainers"]["locations"].values()
        ],
        retainer_details=d["retainers"],
        terminal_hardware=d["terminal_hardware"],
        native_component_and_mate_heights_all_approved=False,
        physical_fit_verified=False,
        electrical_joint_qualified=False,
        fabrication_released=False,
    )
    (OUT / "interface.json").write_text(json.dumps(interface, indent=2) + "\n")
    print(json.dumps(dict(cad=record, geometry=g), indent=2))


if __name__ == "__main__":
    main()
