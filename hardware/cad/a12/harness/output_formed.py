"""Separate AWG18 formed-wire escape on unchanged native J4 pads.

Models both bare conductor and insulated tube, including the flat insulation
cut with its position allowance. Intended source-board contact is checked in
the board's common frame with actual minimum bores; every other PCB/body stays
in the external .65mm position/.25mm clearance checks. This is not a complete
receiving/fanout harness, fabrication approval or physical wire qualification.
"""

import argparse
import json
import math
import subprocess
from pathlib import Path

from hardware.cad.a12.positive_links.collisions import snapshot
from hardware.cad.a12.repaired import packet
from hardware.cad.a12.thermal.verify import binary_stl
from hardware.electronics.common.sexpr import children, first, read_sexpr
from hardware.electronics.output_stage.check_placement import transform

from ..generate import REPO, sha
from .output_escape import arc, box_distance, cylinder_distance

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "generated/output-formed-6715"
PROFILES = {
    "constant": [("1", "5V_DIG", 215, 10.0, 18), ("2", "AGND", 270, 10.0, 18)],
    "positive-raised": [("1", "5V_DIG", 215, 10.0, 24), ("2", "AGND", 270, 10.0, 18)],
    "compact-return": [("1", "5V_DIG", 215, 10.0, 24), ("2", "AGND", 270, 9.7, 24)],
    "balanced-return": [("1", "5V_DIG", 215, 10.0, 23.8), ("2", "AGND", 270, 9.7, 23.6)],
    "east-pair": [("1", "5V_DIG", 0, 10.0, 18), ("2", "AGND", -30, 10.0, 24)],
}


def cut_frame(point, tangent):
    x, y, z = tangent
    norm = math.hypot(x, y)
    u = [1, 0, 0] if norm < 1e-12 else [y / norm, -x / norm, 0]
    v = [y * u[2] - z * u[1], z * u[0] - x * u[2], x * u[1] - y * u[0]]
    return [[u[i], v[i], tangent[i], point[i]] for i in range(3)] + [[0, 0, 0, 1]]


def r58_source_snapshot(candidate, native, hashes):
    """Bind the isolated R58-only proposal, including its unchanged source J4.

    This is not an electrically closed board: the existing 45 opens remain.
    The independent complete parsed-node comparison prevents a different PCB
    from inheriting the original copper, package or source-hole geometry.
    """
    receipt_file = candidate / "generated/current-native.json"
    receipt = json.loads(receipt_file.read_text())
    pcb = candidate / "rail_disconnect.kicad_pcb"
    assert receipt["candidate_pcb_sha256"] == sha(pcb)
    for key in ["source_sha256", "artifact_sha256"]:
        assert all(sha(REPO / n) == h for n, h in receipt[key].items()), "Stale R58 native receipt"
        hashes.update(receipt[key])
    hashes[str(receipt_file.relative_to(REPO))] = sha(receipt_file)
    independent = ROOT / "generated/r58-source-independent.json"
    checked = json.loads(independent.read_text())
    canonical = REPO / "hardware/electronics/rail_disconnect/revision28/rail_disconnect.kicad_pcb"
    assert checked["canonical_pcb_sha256"] == sha(canonical)
    assert checked["candidate_pcb_sha256"] == sha(pcb)
    assert all(checked["exact_top_level_equal"].values())
    assert checked["changed_footprint_refs"] == ["R58"]
    assert checked["r58_after_restoring_Y_equals_canonical"]
    hashes[str(independent.relative_to(REPO))] = sha(independent)
    drc_file = candidate / "generated/drc-r58-yminus02.json"
    erc_file = candidate / "generated/erc-r58-yminus02.json"
    for p in [drc_file, erc_file]:
        assert str(p.relative_to(REPO)) in receipt["artifact_sha256"]
    drc, erc = json.loads(drc_file.read_text()), json.loads(erc_file.read_text())
    assert len(drc["unconnected_items"]) == 45 and len(drc["violations"]) == 76
    assert not drc["schematic_parity"] and not any(v["severity"] == "error" for v in drc["violations"])
    assert erc["sheets"] and all(not sheet["violations"] for sheet in erc["sheets"])
    replacement = packet({"E28": candidate})
    assert not replacement["same_board_component_overlap_candidates"]
    native.update(replacement)
    hashes.update(replacement["source_sha256"])
    return pcb


def generate(out=OUT, profile="constant", source_candidate=None):
    assert profile in PROFILES, "Unknown separate formed-wire study"
    wire_file = ROOT / "output-wire-6715.json"
    proposal = json.loads(wire_file.read_text())
    wire = proposal["wire"]
    external = Path(proposal["external_pdf_path"])
    if external.exists():
        assert sha(external) == proposal["manufacturer_pdf_sha256"]
    native, other, hashes = snapshot()
    pcb = REPO / "hardware/electronics/rail_disconnect/revision28/rail_disconnect.kicad_pcb"
    if source_candidate is not None:
        source_candidate = source_candidate.resolve()
        source_candidate.relative_to(REPO)
        pcb = r58_source_snapshot(source_candidate, native, hashes)
    tree = read_sexpr(pcb.read_text())
    fp = next(
        f
        for f in children(tree, "footprint")
        if any(p[1:3] == ["Reference", "J4"] for p in children(f, "property"))
    )
    assert first(fp, "layer")[1] == "F.Cu"
    board = next(b for b in native["boards"] if b["id"] == "E28")
    face = board["datum"][2] + float(first(first(tree, "general"), "thickness")[1])
    bare_length = 3.1
    required = wire["minimum_bend_radius_mm"] + wire["insulation_od_mm"][1] / 2
    metal_od, centering, position, clearance, reserve = 1.4, 0.3, 0.65, 0.25, 0.005
    assert metal_od + 2 * centering < 2.1, "Pretinned bundle/centering does not fit minimum bore"
    bare_paths, insulated_paths, full_paths, frames, rows = [], [], [], [], []
    for number, net, angle, radius, plane in PROFILES[profile]:
        assert radius >= required, "Formed-wire centreline radius is too small"
        straight = plane - face - radius
        assert 0 < straight and bare_length < straight + radius * math.pi / 2
        pad = next(p for p in children(fp, "pad") if str(p[1]) == number)
        assert str(first(pad, "net")[-1]).lstrip("/") == net
        assert float(first(pad, "drill")[1]) == 2.2
        assert list(map(float, first(pad, "size")[1:3])) == [4.2, 4.2]
        xy = transform(fp, first(pad, "at")[1:3])
        start = [xy[0] - 100 + board["datum"][0], xy[1] - 100 + board["datum"][1], face]
        bend = [*start[:2], face + straight]
        a = math.radians(angle)

        def at(t):
            return [
                bend[0] + radius * (1 - math.cos(t)) * math.cos(a),
                bend[1] + radius * (1 - math.cos(t)) * math.sin(a),
                bend[2] + radius * math.sin(t),
            ]

        theta = [i * math.pi / 240 for i in range(121)]
        if bare_length <= straight:
            cut = [*start[:2], face + bare_length]
            tangent = [0, 0, 1]
            bare = [start, cut]
            insulated = [cut, bend] + [at(t) for t in theta[1:]]
        else:
            theta_cut = (bare_length - straight) / radius
            cut = at(theta_cut)
            bare = [start, bend] + [at(t) for t in theta[1:] if t < theta_cut] + [cut]
            insulated = [cut] + [at(t) for t in theta if t > theta_cut]
            tangent = [math.sin(theta_cut) * math.cos(a), math.sin(theta_cut) * math.sin(a), math.cos(theta_cut)]
        bare_paths.append(bare)
        insulated_paths.append(insulated)
        frames.append(cut_frame(cut, tangent))
        line_steps = math.ceil(straight / (radius * math.pi / 1200))
        line = [[*start[:2], face + straight * i / line_steps] for i in range(line_steps)]
        full_paths.append(line + arc(bend, radius, angle, 600))
        rows.append(
            dict(
                pin=number,
                net=net,
                source_face_mm=start,
                initial_straight_mm=straight,
                nominal_bend_radius_mm=radius,
                angle_deg=angle,
                bare_length_above_face_mm=bare_length,
                insulation_cut_mm=cut,
                insulation_cut_tangent=tangent,
                insulated_curve_length_mm=straight + radius * math.pi / 2 - bare_length,
                escape_end_mm=at(math.pi / 2),
            )
        )
    boxes = [b for b in native["boxes"] if not b[0].startswith("E28_J4")]
    joints = [b for b in native["boxes"] if b[0].startswith("E28_J4")]
    others = [b for b in other["envelopes"] if not b[0].startswith("disconnect_")] + other["port_envelopes"]
    wire_r = wire["insulation_od_mm"][1] / 2 + position
    maximum_radius = max(r["nominal_bend_radius_mm"] for r in rows)
    cover = maximum_radius * math.pi / 2400
    closest = []
    for b in boxes + others + native["switch_diagnostic_boxes"]:
        gap = min(box_distance(p, b) for path in full_paths for p in path) - wire_r - clearance - cover
        closest.append(dict(obstacle=b[0], conservative_gap_mm=gap))
    for c in native["cylinders"]:
        gap = min(cylinder_distance(p, c) for path in full_paths for p in path) - wire_r - clearance - cover
        closest.append(dict(obstacle=c[0], conservative_gap_mm=gap))
    closest.sort(key=lambda r: r["conservative_gap_mm"])
    chord_bound = maximum_radius * (math.pi / 240) ** 2 / 8
    assert chord_bound < reserve
    for p in [
        Path(__file__),
        wire_file,
        ROOT / "output_escape.py",
        ROOT.parent / "positive_links/generated/positive-links.stl",
    ]:
        hashes[str(p.relative_to(REPO))] = sha(p)
    out.mkdir(parents=True, exist_ok=True)
    source = 'include <../../../thermal-integration.scad>\ntrial="geometry";\n'
    values = dict(
        bare_paths=bare_paths,
        insulated_paths=insulated_paths,
        cut_frames=frames,
        joints=joints,
        boxes=boxes + others,
        cylinders=native["cylinders"],
        insulated_radius=wire_r + reserve,
        bare_radius=metal_od / 2 + position + reserve,
        relative_metal_radius=metal_od / 2 + centering + reserve,
        relative_insulated_radius=wire["insulation_od_mm"][1] / 2 + centering + reserve,
        source_origin=board["datum"],
        source_outline=board["outline_relative_mm"],
        source_board_max_thickness=board["thickness_range_allocation_mm"][1],
    )
    for key, value in values.items():
        source += key + "=" + json.dumps(value) + ";\n"
    source += """module sweep(path,r){for(j=[0:len(path)-2])hull(){translate(path[j])sphere(r=r/pow(cos(180/64),2),$fn=64);translate(path[j+1])sphere(r=r/pow(cos(180/64),2),$fn=64);}}
module past_cut(i,back){multmatrix(cut_frames[i])translate([-500,-500,-back])cube([1000,1000,1000]);}
module bare(i,m=0){sweep(bare_paths[i],bare_radius+m);}
module insulated(i,m=0){intersection(){sweep(insulated_paths[i],insulated_radius+m);past_cut(i,.655+m);}}
module wire(i,m=0){bare(i,m);insulated(i,m);}
module wires(m=0){wire(0,m);wire(1,m);}
module joint_reserves(m=0){for(b=joints)translate([b[1]-m,b[2]-m,b[3]-.2-m])cube([b[4]+2*m,b[5]+2*m,b[6]+.4+2*m]);}
module subject(m=0){wires(m);joint_reserves(m);}
module source_PCB(){translate([source_origin[0],source_origin[1],source_origin[2]-.2])difference(){linear_extrude(source_board_max_thickness+.4)polygon(source_outline);for(path=bare_paths)translate([path[0][0]-source_origin[0],path[0][1]-source_origin[1],-.01])cylinder(d=2.1,h=3,$fn=64);}}
module relative_wire(i){sweep(concat([[bare_paths[i][0][0],bare_paths[i][0][1],source_origin[2]-1.5]],bare_paths[i]),relative_metal_radius);intersection(){sweep(insulated_paths[i],relative_insulated_radius);past_cut(i,.305);}}
module electronics(){for(b=boxes)translate([b[1],b[2],b[3]-.2])cube([b[4],b[5],b[6]+.4]);for(c=cylinders)translate([c[1],c[2],c[3]-.2])cylinder(d=c[4]/cos(180/128),h=c[5]+.4,$fn=128);
"""
    for b in native["boards"]:
        if b["id"] != "E28":
            source += (
                "translate("
                + json.dumps([*b["datum"][:2], b["datum"][2] - 0.2])
                + ")linear_extrude("
                + str(b["thickness_range_allocation_mm"][1] + 0.4)
                + ")polygon("
                + json.dumps(b["outline_relative_mm"])
                + ");\n"
            )
    for b in other["boards"]:
        if b[0] != "disconnect_carrier":
            source += "board_reserve(" + json.dumps(b) + ");\n"
    source += """}
module hardware(){return_assembly();import("../../../positive_links/generated/positive-links.stl");}
module case_parts(){retained_thermal_shell();thermal_controls();thermal_metal_base();lower_shell_fasteners();}
if(trial=="geometry")subject();
if(trial=="bare_geometry"){bare(0);bare(1);}
if(trial=="insulated_geometry"){insulated(0);insulated(1);}
if(trial=="electronics_collision")intersection(){subject(.25);electronics();}
if(trial=="wire_electronics_collision")intersection(){wires(.25);electronics();}
if(trial=="joint_electronics_collision")intersection(){joint_reserves(.25);electronics();}
if(trial=="hardware_collision")intersection(){subject(.25);hardware();}
if(trial=="case_collision")intersection(){subject(.25);case_parts();}
if(trial=="pair_collision")intersection(){wire(0,.125);wire(1,.125);}
if(trial=="source_PCB_geometry")source_PCB();
if(trial=="source_joint_collision")intersection(){source_PCB();union(){relative_wire(0);relative_wire(1);}}
if(trial=="bare_positive_control")intersection(){bare(0);translate(bare_paths[0][0]+[-.1,-.1,.4])cube([.2,.2,.2]);}
if(trial=="insulated_positive_control")intersection(){insulated(0);translate(insulated_paths[0][floor(len(insulated_paths[0])/2)]-[.1,.1,.1])cube([.2,.2,.2]);}
if(trial=="source_PCB_positive_control")intersection(){source_PCB();translate([160,134,5.7])cube([.2,.2,.2]);}
"""
    (out / "checks.scad").write_text(source)
    report = dict(
        scope=__doc__,
        source_sha256=hashes,
        separate_wire_proposal=proposal,
        source_native_PCB_sha256=sha(pcb),
        source_R58_proposal=str(source_candidate.relative_to(REPO)) if source_candidate else None,
        source_face_z_mm=face,
        routes=rows,
        profile=profile,
        required_centerline_radius_mm=required,
        bare_conductor_maximum_pretinned_OD_requirement_mm=metal_od,
        source_relative_centering_allocation_mm=centering,
        minimum_finished_source_bore_requirement_mm=2.1,
        source_hole_bores_are_actual_J4_only=True,
        source_PCB_excluded_only_from_external_wire_comparison=True,
        source_common_frame_intrinsic_comparison_required=True,
        source_joint_and_lead_reserves_included=True,
        source_projection_trim_maximum_mm=1.5,
        position_allocation_mm=position,
        clearance_mm=clearance,
        curve_chord_error_bound_mm=chord_bound,
        curve_geometry_reserve_mm=reserve,
        straight_and_curved_bare_metal_included=True,
        insulation_cut_is_tangent_plane_with_position_reserve=True,
        closest_component_screens=closest[:12],
        numerical_component_screen_clear=closest[0]["conservative_gap_mm"] > 0,
        insulated_radius_with_position_and_geometry_reserve_mm=wire_r + reserve,
        bare_radius_with_position_and_geometry_reserve_mm=metal_od / 2 + position + reserve,
        actual_formed_radius_inspected=False,
        source_and_receiving_solder_process_approved=False,
        source_native_BOM_still_AWG14=True,
        canonical_BOM_changed=False,
        destination_interface_redesigned=False,
        fanout_selected=False,
        complete_output_harness=False,
        physical_fit_verified=False,
        fabrication_released=False,
    )
    assert all(sha(REPO / n) == h for n, h in hashes.items()), "Source changed during formed-wire snapshot"
    (out / "analysis.json").write_text(json.dumps(report, indent=2) + "\n")
    (out / "obstacles.json").write_text(json.dumps(dict(native=native, other=other), indent=2) + "\n")
    return report


def verify(executable, out=OUT):
    report = json.loads((out / "analysis.json").read_text())
    (out / "verification.json").unlink(missing_ok=True)
    inputs = {
        str(p.relative_to(REPO)): sha(p)
        for p in [out / "analysis.json", out / "checks.scad", out / "obstacles.json"]
    }
    cases = {}
    for case in [
        "geometry",
        "bare_geometry",
        "insulated_geometry",
        "electronics_collision",
        "wire_electronics_collision",
        "joint_electronics_collision",
        "hardware_collision",
        "case_collision",
        "pair_collision",
        "source_PCB_geometry",
        "source_joint_collision",
        "bare_positive_control",
        "insulated_positive_control",
        "source_PCB_positive_control",
    ]:
        target = out / (case + ".stl")
        target.unlink(missing_ok=True)
        cmd = [str(executable), "--hardwarnings", "--backend", "Manifold", "--export-format", "binstl"]
        for name in ["part", "thermal_part", "positive_part"]:
            cmd += ["-D", name + '="formed_wire_only"']
        cmd += ["-D", 'trial="' + case + '"', "-o", str(target), str(out / "checks.scad")]
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        log = p.stdout + p.stderr
        (out / (case + ".log")).write_text(log)
        empty = p.returncode == 1 and "Current top level object is empty." in log and not target.exists()
        if empty and case.endswith("collision") and not any(s in log for s in ["WARNING", "ERROR"]):
            cases[case] = dict(clear=True, empty=True)
        elif (
            p.returncode == 0
            and target.exists()
            and ("NoError" in log or "Top level object is a 3D object (PolySet):" in log)
            and not any(s in log for s in ["WARNING", "ERROR"])
        ):
            stats = binary_stl(target)
            clear = not case.endswith("collision") and stats["volume_mm3"] > 0.001
            if case == "bare_geometry":
                r = report["bare_radius_with_position_and_geometry_reserve_mm"]
                expected = 2 * (math.pi * r * r * 3.1 + 4 * math.pi * r**3 / 3)
                clear = math.isclose(stats["volume_mm3"], expected, rel_tol=0.03)
            if case == "insulated_geometry":
                r = report["insulated_radius_with_position_and_geometry_reserve_mm"]
                back = 0.655
                length = sum(row["insulated_curve_length_mm"] for row in report["routes"])
                expected = math.pi * r * r * length + 2 * (
                    2 * math.pi * r**3 / 3 + math.pi * (r * r * back - back**3 / 3)
                )
                clear = math.isclose(stats["volume_mm3"], expected, rel_tol=0.03)
            if case.endswith("positive_control"):
                clear = math.isclose(stats["volume_mm3"], 0.008, abs_tol=1e-6)
            cases[case] = dict(clear=clear, **stats)
        else:
            cases[case] = dict(clear=False, returncode=p.returncode)
        print(case, cases[case], flush=True)
    changed = [n for n, h in {**report["source_sha256"], **inputs}.items() if sha(REPO / n) != h]
    result = dict(
        scope=__doc__,
        cases=cases,
        changed_inputs=changed,
        local_formed_escape_clear=not changed
        and all(r["clear"] for r in cases.values())
        and report["numerical_component_screen_clear"],
        source_sha256=report["source_sha256"],
        evidence_inputs_sha256=inputs,
        evidence_sha256={
            str(p.relative_to(REPO)): sha(p) for p in out.iterdir() if p.suffix in (".log", ".stl")
        },
        complete_output_harness=False,
        physical_fit_verified=False,
        fabrication_released=False,
    )
    (out / "verification.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--openscad", type=Path)
    parser.add_argument("--profile", choices=list(PROFILES), default="constant")
    parser.add_argument("--source-candidate", type=Path)
    args = parser.parse_args()
    out = OUT if args.profile == "constant" else ROOT / ("generated/output-formed-6715-" + args.profile)
    if args.source_candidate:
        out = out.with_name(out.name + "-r58")
    r = generate(out, args.profile, args.source_candidate)
    print("Closest screens", r["closest_component_screens"][:3], flush=True)
    if args.openscad:
        raise SystemExit(0 if verify(args.openscad, out)["local_formed_escape_clear"] else 1)
