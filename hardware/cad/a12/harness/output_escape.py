"""Protected DIGITAL wire escape study; not a complete output harness.

Two quarter circles leave the actual E28 J4 pads vertically. This separates
the local bend/obstacle problem from the still-unselected receiving termination.
"""

import argparse
import json
import math
import subprocess
from pathlib import Path

from hardware.cad.a12.positive_links.collisions import snapshot
from hardware.cad.a12.thermal.verify import binary_stl
from hardware.electronics.common.sexpr import children, first, read_sexpr
from hardware.electronics.output_stage.check_placement import transform
from hardware.electronics.rail_disconnect.revision28.wire_outputs import WIRE

from ..generate import REPO, sha

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "generated/output-escape"


def box_distance(p, b):
    return math.sqrt(sum(max(b[i + 1] - p[i], 0, p[i] - b[i + 1] - b[i + 4]) ** 2 for i in range(3)))


def cylinder_distance(p, c):
    return math.hypot(
        max(math.hypot(p[0] - c[1], p[1] - c[2]) - c[4] / 2, 0),
        max(c[3] - p[2], 0, p[2] - c[3] - c[5]),
    )


def arc(start, radius, angle, intervals):
    a = math.radians(angle)
    return [
        [
            start[0] + radius * (1 - math.cos(t)) * math.cos(a),
            start[1] + radius * (1 - math.cos(t)) * math.sin(a),
            start[2] + radius * math.sin(t),
        ]
        for t in [math.pi * i / (2 * intervals) for i in range(intervals + 1)]
    ]


def curved_escape(start, profile, intervals):
    """Constant-speed bend with a cubic change of azimuth after theta0.

    Unit tangent=(sin(theta)cos(phi),sin(theta)sin(phi),cos(theta)).
    Speed wrt theta is R, so kappa<=sqrt(1+max(phi')**2)/R.
    Composite midpoint XY integration has an explicit vector error bound.
    """
    radius = profile["radius_mm"]
    begin = math.radians(profile["twist_start_deg"])
    phi0, phi1 = [math.radians(profile[n]) for n in ["angle_start_deg", "angle_finish_deg"]]
    span, delta = math.pi / 2 - begin, phi1 - phi0
    if radius <= 0 or not 0 <= begin < math.pi / 2 or intervals < 120:
        raise ValueError("Invalid controlled bend")
    pmax, qmax = 1.5 * abs(delta) / span, 6 * abs(delta) / span**2
    minimum_radius = radius / math.sqrt(1 + pmax**2)
    h = math.pi / (2 * intervals)
    third_derivative_bound = radius * (1 + 2 * pmax + qmax + pmax**2)
    integration_bound = (math.pi / 2) * h**2 * third_derivative_bound / 24
    points = [list(start)]
    x, y = start[:2]
    for i in range(intervals):
        theta = (i + 0.5) * h
        u = max(0, min(1, (theta - begin) / span))
        phi = phi0 + delta * u * u * (3 - 2 * u)
        x += radius * h * math.sin(theta) * math.cos(phi)
        y += radius * h * math.sin(theta) * math.sin(phi)
        points.append([x, y, start[2] + radius * math.sin((i + 1) * h)])
    metadata = dict(
        centerline_radius_lower_bound_mm=minimum_radius,
        integration_position_error_bound_mm=integration_bound,
        arc_length_mm=radius * math.pi / 2,
        native_chord_error_bound_mm=radius * math.sqrt(1 + pmax**2) * (math.pi / 240) ** 2 / 8,
        angle_derivative_bound=pmax,
        speed_mm_per_theta=radius,
    )
    return points, metadata


def generate(
    radius=21, angle=-17.3, straight_mm=0, wire_file=None, out=OUT, route_file=None, shell_height=38
):
    proposal = json.loads(wire_file.read_text()) if wire_file is not None else None
    wire = dict(WIRE) if proposal is None else proposal["wire"]
    if proposal and Path(proposal["external_pdf_path"]).exists():
        assert sha(Path(proposal["external_pdf_path"])) == proposal["manufacturer_pdf_sha256"]
    required = wire["minimum_bend_radius_mm"] + wire["insulation_od_mm"][1] / 2
    if (
        radius < required
        or not all(math.isfinite(x) for x in [radius, angle, straight_mm])
        or straight_mm < 0
    ):
        raise ValueError("Quarter-circle radius must exceed the conservative centreline requirement")
    native, data, hashes = snapshot()
    if not math.isfinite(shell_height) or shell_height not in (38, 54):
        raise ValueError("Only the original shell and separate 54mm study have native pose witnesses")
    lift = shell_height - 38
    # Explicitly reallocate complete panel-mounted assemblies. Floor/rear
    # electronics retain their actual board datums. Longer mounts and wires
    # are requirements of this separate enclosure proposal, not qualified parts.
    panel_boards = {"meter_board", "bpm_board", "trill_craft", "settings_board", "release_select_board"}
    panel_bodies = {
        "trill_components",
        "bpm_digits",
        "settings_switch",
        "release_select_switch",
        "angle_sensor_board",
        "angle_sensor",
    }
    raised = []
    for b in data["boards"]:
        if b[0] in panel_boards:
            b[3] += lift
            raised.append(b[0])
    for b in data["envelopes"]:
        if b[0] in panel_bodies or b[0].endswith("_pot"):
            b[3] += lift
            raised.append(b[0])
    for b in native["switch_diagnostic_boxes"]:
        b[3] += lift
    mounts = [list(m) for m in data["board_mounts"]]
    for m in mounts:
        if m[0] in {"lever", "scene_board"}:
            m[3] += lift
    pcb = REPO / "hardware/electronics/rail_disconnect/revision28/rail_disconnect.kicad_pcb"
    tree = read_sexpr(pcb.read_text())
    thickness = float(first(first(tree, "general"), "thickness")[1])
    fp = next(
        f
        for f in children(tree, "footprint")
        if any(p[1:3] == ["Reference", "J4"] for p in children(f, "property"))
    )
    assert first(fp, "layer")[1] == "F.Cu" and "AWG14_Force" in str(fp[1])
    board = next(b for b in native["boards"] if b["id"] == "E28")
    pads = {str(p[1]): p for p in children(fp, "pad")}
    route_spec = json.loads(route_file.read_text()) if route_file is not None else None
    intervals = 600 if route_spec is None else route_spec["intervals"]
    start_height = 3.1 if route_spec is None else route_spec["insulation_start_above_nominal_face_mm"]
    rows, paths = [], []
    for number, net in [("1", "5V_DIG"), ("2", "AGND")]:
        pad = pads[number]
        assert str(first(pad, "net")[-1]).lstrip("/") == net
        xy = transform(fp, first(pad, "at")[1:3])
        start = [
            xy[0] - 100 + board["datum"][0],
            xy[1] - 100 + board["datum"][1],
            board["datum"][2] + thickness + start_height,
        ]
        bend_start = [*start[:2], start[2] + straight_mm]
        line_steps = math.ceil(straight_mm / (math.pi * radius / (2 * intervals)))
        line = [[*start[:2], start[2] + straight_mm * i / line_steps] for i in range(line_steps)]
        profile = dict(radius_mm=radius, angle_start_deg=angle, angle_finish_deg=angle, twist_start_deg=50)
        if route_spec is not None:
            profile = next(p for p in route_spec["profiles"] if p["pin"] == number)
        points, metadata = curved_escape(bend_start, profile, intervals)
        assert metadata["centerline_radius_lower_bound_mm"] >= required, "Controlled bend is too tight"
        assert (
            metadata["integration_position_error_bound_mm"] + metadata["native_chord_error_bound_mm"] < 0.005
        )
        points = line + points
        paths.append(points)
        rows.append(
            dict(
                pin=number,
                net=net,
                insulation_start_mm=start,
                bend_start_mm=bend_start,
                escape_end_mm=points[-1],
                arc_length_mm=metadata["arc_length_mm"],
                straight_length_mm=straight_mm,
                profile=profile,
                geometry_bounds=metadata,
            )
        )
    position, clearance = 0.65, 0.25
    wire_radius = wire["insulation_od_mm"][1] / 2 + position
    # Every continuous arc point is within this distance of a sampled centre.
    # The extra reserve makes a clear point-to-solid screen conservative.
    sampling_cover = max(r["geometry_bounds"]["speed_mm_per_theta"] for r in rows) * math.pi / (4 * intervals)
    sampling_cover += max(r["geometry_bounds"]["integration_position_error_bound_mm"] for r in rows)
    boxes = [b for b in native["boxes"] if not b[0].startswith("E28_J4")]
    other = [b for b in data["envelopes"] if not b[0].startswith("disconnect_")] + data["port_envelopes"]
    screening_boxes = boxes + other + native["switch_diagnostic_boxes"]
    screening_boxes = [
        b for b in screening_boxes if b[1] < 192 and b[1] + b[4] > 130 and b[2] < 155 and b[2] + b[5] > 90
    ]
    screening_cylinders = [c for c in native["cylinders"] if c[1] + c[4] / 2 > 130 and c[1] - c[4] / 2 < 192]
    closest = []
    for b in screening_boxes:
        gap = (
            min(box_distance(p, b) for path in paths for p in path) - wire_radius - clearance - sampling_cover
        )
        closest.append(dict(obstacle=b[0], conservative_gap_mm=gap))
    for c in screening_cylinders:
        gap = (
            min(cylinder_distance(p, c) for path in paths for p in path)
            - wire_radius
            - clearance
            - sampling_cover
        )
        closest.append(dict(obstacle=c[0], conservative_gap_mm=gap))
    closest.sort(key=lambda r: r["conservative_gap_mm"])
    for p in [
        Path(__file__),
        REPO / "hardware/electronics/rail_disconnect/revision28/wire_outputs.py",
        ROOT.parent / "positive_links/generated/positive-links.stl",
    ]:
        hashes[str(p.relative_to(REPO))] = sha(p)
    if wire_file is not None:
        hashes[str(wire_file.relative_to(REPO))] = sha(wire_file)
    if route_file is not None:
        hashes[str(route_file.relative_to(REPO))] = sha(route_file)
    report = dict(
        scope="Insulated quarter-circle J4 escapes only; all destination wiring unfinished",
        source_sha256=hashes,
        selected_wire=wire,
        separate_wire_proposal=proposal,
        separate_route_proposal=route_spec,
        canonical_wire_selection_changed=False,
        separate_enclosure_height_proposal_mm=shell_height if lift else None,
        enclosure_height_adopted=False,
        panel_assembly_lift_mm=lift,
        raised_panel_body_and_board_ids=raised if lift else [],
        proposed_board_mounts=mounts,
        full_revised_enclosure_validated=False,
        straight_before_bend_mm=straight_mm,
        radius_mm=radius,
        horizontal_angle_deg=angle,
        required_centerline_radius_mm=required,
        source_insulation_start_above_nominal_face_mm=start_height,
        source_strip_solder_and_forming_approved=False,
        wire_radius_with_position_allocation_mm=wire_radius,
        position_allocation_mm=position,
        clearance_mm=clearance,
        sample_cover_mm=sampling_cover,
        intervals=intervals,
        routes=rows,
        closest_component_screens=closest[:12],
        numerical_component_screen_clear=closest[0]["conservative_gap_mm"] > 0,
        receiving_E19_J1_is_unselected_Header2=True,
        destination_wire_gauge_and_contact_accepted=False,
        complete_output_harness=False,
        physical_fit_verified=False,
        fabrication_released=False,
    )
    out.mkdir(exist_ok=True)
    (out / "analysis.json").write_text(json.dumps(report, indent=2) + "\n")
    (out / "obstacles.json").write_text(json.dumps(dict(native=native, other=data), indent=2) + "\n")
    source = 'include <../../thermal-integration.scad>\ntrial="geometry";\n'
    stride = intervals // 120
    simple_paths = [p[::stride] + ([] if p[-1] == p[::stride][-1] else [p[-1]]) for p in paths]
    source += "paths=" + json.dumps(simple_paths) + ";\n"
    source += "boxes=" + json.dumps(boxes + other) + ";\n"
    source += "cylinders=" + json.dumps(native["cylinders"]) + ";\n"
    source += f"radius={wire_radius + 0.005};\n"
    source += """module wire(i,margin=0){for(j=[0:len(paths[i])-2])hull(){translate(paths[i][j])sphere(r=(radius+margin)/pow(cos(180/64),2),$fn=64);translate(paths[i][j+1])sphere(r=(radius+margin)/pow(cos(180/64),2),$fn=64);}}
module wires(margin=0){wire(0,margin);wire(1,margin);}
module electronics(){for(b=boxes)translate([b[1],b[2],b[3]-.2])cube([b[4],b[5],b[6]+.4]);for(c=cylinders)translate([c[1],c[2],c[3]-.2])cylinder(d=c[4]/cos(180/128),h=c[5]+.4,$fn=128);
"""
    for b in native["boards"]:
        source += (
            "translate("
            + json.dumps([*b["datum"][:2], b["datum"][2] - 0.2])
            + ")linear_extrude("
            + str(b["thickness_range_allocation_mm"][1] + 0.4)
            + ")polygon("
            + json.dumps(b["outline_relative_mm"])
            + ");\n"
        )
    for b in data["boards"]:
        if b[0] != "disconnect_carrier":
            source += "board_reserve(" + json.dumps(b) + ");\n"
    source += """}
module hardware(){return_assembly();import("../../positive_links/generated/positive-links.stl");}
module case_parts(){retained_thermal_shell();thermal_controls();thermal_metal_base();lower_shell_fasteners();}
if(trial=="geometry")wires();
if(trial=="electronics_collision")intersection(){wires(.25);electronics();}
if(trial=="case_collision")intersection(){wires(.25);case_parts();}
if(trial=="hardware_collision")intersection(){wires(.25);hardware();}
if(trial=="pair_collision")intersection(){wire(0,.125);wire(1,.125);}
if(trial=="positive_control")intersection(){wires();translate(paths[0][floor(len(paths[0])/2)]-[.1,.1,.1])cube([.2,.2,.2]);}
"""
    if lift:
        # The native CLI overrides shell_height and the lever mount list.
        # panel_z is then calculated by the actual housing definition.
        source += f"module raised_controls(){{rear_panel();translate([0,0,{lift}]){{lever_bracket();lever_sweep();}}touch_backer();translate([0,0,panel_z])front_panel();translate([0,0,panel_z-guide_thick])guide_plate();for(b=buttons)button_pose(b){{switch_holder(b);key_sweep(b);}}a12_switch_electronics();}}\n"
        source = source.replace(
            "retained_thermal_shell();thermal_controls();thermal_metal_base();",
            "retained_thermal_shell();raised_controls();thermal_metal_base();",
        )
        source += 'if(trial=="original_height_control")intersection(){wires(.25);case_parts();}\n'
        source += 'if(trial=="raised_wall_control")intersection(){retained_thermal_shell();translate([1,140,44])cube([.2,.2,.2]);}\n'
        source += 'if(trial=="raised_switch_control")intersection(){a12_switch_electronics();translate([160,129,39])cube([.2,.2,.2]);}\n'
    # SCAD paths are relative to this generated subdirectory.
    source = source.replace("../../thermal-integration", "../../../thermal-integration").replace(
        "../../positive_links", "../../../positive_links"
    )
    (out / "checks.scad").write_text(source)
    assert all(sha(REPO / name) == value for name, value in hashes.items()), "Snapshot changed during capture"
    return report


def verify(executable, out=OUT):
    report = json.loads((out / "analysis.json").read_text())
    (out / "verification.json").unlink(missing_ok=True)
    evidence_inputs = {
        str(p.relative_to(REPO)): sha(p)
        for p in [out / "checks.scad", out / "analysis.json", out / "obstacles.json"]
    }
    results = {}
    names = [
        "geometry",
        "electronics_collision",
        "case_collision",
        "hardware_collision",
        "pair_collision",
        "positive_control",
    ]
    if report["panel_assembly_lift_mm"]:
        names += ["original_height_control", "raised_wall_control", "raised_switch_control"]
    for case in names:
        target = out / (case + ".stl")
        target.unlink(missing_ok=True)
        cmd = [str(executable), "--hardwarnings", "--backend", "Manifold", "--export-format", "binstl"]
        for name in ["part", "thermal_part", "positive_part"]:
            cmd += ["-D", name + '="output_escape_only"']
        if report["panel_assembly_lift_mm"]:
            height = (
                38 if case == "original_height_control" else report["separate_enclosure_height_proposal_mm"]
            )
            cmd += ["-D", "shell_height=" + str(height)]
            cmd += ["-D", "board_mounts=" + json.dumps(report["proposed_board_mounts"])]
        cmd += ["-D", 'trial="' + case + '"', "-o", str(target), str(out / "checks.scad")]
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        log = p.stdout + p.stderr
        (out / (case + ".log")).write_text(log)
        empty = p.returncode == 1 and "Current top level object is empty." in log and not target.exists()
        if case.endswith("collision") and empty and not any(x in log for x in ["WARNING", "ERROR"]):
            results[case] = dict(clear=True, empty=True)
        elif (
            p.returncode == 0
            and target.exists()
            and "NoError" in log
            and not any(x in log for x in ["WARNING", "ERROR"])
        ):
            results[case] = dict(clear=not case.endswith("collision"), **binary_stl(target))
            if case == "geometry":
                r = report["wire_radius_with_position_allocation_mm"] + 0.005
                length = sum(row["arc_length_mm"] + row["straight_length_mm"] for row in report["routes"])
                expected = math.pi * r * r * length + 8 * math.pi * r**3 / 3
                results[case]["clear"] = math.isclose(results[case]["volume_mm3"], expected, rel_tol=0.03)
            if case in {"positive_control", "raised_wall_control", "raised_switch_control"}:
                results[case]["clear"] = math.isclose(results[case]["volume_mm3"], 0.008, abs_tol=1e-6)
            if case == "original_height_control":
                results[case]["clear"] = results[case]["volume_mm3"] > 0.001
        else:
            results[case] = dict(clear=False, returncode=p.returncode, result="native execution rejected")
        print(case, results[case], flush=True)
    changed = [name for name, value in report["source_sha256"].items() if sha(REPO / name) != value]
    changed += [name for name, value in evidence_inputs.items() if sha(REPO / name) != value]
    result = dict(
        cases=results,
        changed_inputs=changed,
        local_escape_native_clear=all(r["clear"] for r in results.values()) and not changed,
        numerical_component_screen_clear=report["numerical_component_screen_clear"],
        physical_fit_verified=False,
        complete_output_harness=False,
        fabrication_released=False,
        evidence_inputs_sha256=evidence_inputs,
        source_sha256=report["source_sha256"],
        evidence_sha256={
            str(p.relative_to(REPO)): sha(p) for p in out.iterdir() if p.suffix in (".stl", ".log")
        },
    )
    (out / "verification.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--radius", type=float, default=21)
    parser.add_argument("--angle", type=float, default=-17.3)
    parser.add_argument("--straight-mm", type=float, default=0)
    parser.add_argument("--wire", choices=["3079", "6717"], default="3079")
    parser.add_argument("--profile", choices=["quarter", "left"], default="quarter")
    parser.add_argument("--openscad", type=Path)
    parser.add_argument("--shell-height", type=float, default=38)
    args = parser.parse_args()
    wire_file = None if args.wire == "3079" else ROOT / "output-wire-6717.json"
    out = OUT if wire_file is None else ROOT / "generated/output-escape-6717"
    route_file = ROOT / "output-left-route.json" if args.profile == "left" else None
    if route_file:
        assert wire_file is not None and args.straight_mm == 0, "Left route requires the exact 6717 proposal"
        out = ROOT / "generated/output-escape-6717-left"
    if args.shell_height != 38:
        assert args.shell_height == 54 and route_file is None and wire_file is not None, (
            "Only the separate 54mm/6717 study has native pose witnesses"
        )
        out = ROOT / "generated/output-escape-raised-shell"
    r = generate(args.radius, args.angle, args.straight_mm, wire_file, out, route_file, args.shell_height)
    print("Closest component screen:", r["closest_component_screens"][:2], flush=True)
    if args.openscad:
        result = verify(args.openscad, out)
        raise SystemExit(
            0 if result["local_escape_native_clear"] and result["numerical_component_screen_clear"] else 1
        )
