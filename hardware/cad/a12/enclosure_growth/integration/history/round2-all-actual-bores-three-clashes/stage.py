"""Private whole enlarged-unit scene: declared geometry, no hardware qualification."""

import argparse
import hashlib
import json
import re
from pathlib import Path

from hardware.cad.a12.repaired import outline, packet
from hardware.electronics.common.sexpr import children, first, read_sexpr
from hardware.electronics.output_stage.check_placement import courtyard, transform

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[4]
A12 = REPO / "hardware/cad/a12"
OUT = ROOT / "generated"
P03 = REPO / "hardware/electronics/power_distribution/p03/candidates/aux-u10-combined"
E28 = REPO / "hardware/electronics/rail_disconnect/revision28/generated/r58-joint-work"
DEFAULT_RECEIVER = A12 / "harness/proposals/processor-awg18-ear-fanout-spaced"


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def actual_bores(tree):
    """Every actual drilled pad; no generic terminal-seat material deletion."""
    holes = []
    for fp in children(tree, "footprint"):
        ref = next(p[2] for p in children(fp, "property") if p[1] == "Reference")
        for pad in children(fp, "pad"):
            drill = children(pad, "drill")
            if not drill:
                continue
            d = drill[0]
            oval = d[1] == "oval"
            dx = float(d[2] if oval else d[1])
            dy = float(d[3]) if oval else dx
            offsets = children(d, "offset")
            assert not offsets or all(float(v) == 0 for v in offsets[0][1:]), "Unmodelled drill offset"
            at = first(pad, "at")
            x, y = transform(fp, at[1:3])
            angle = float(at[3]) if len(at) > 3 else 0
            holes.append([x - 100, y - 100, dx, dy, angle, ref, str(pad[1]), str(pad[2])])
    return holes


def stage(receiver):
    OUT.mkdir(exist_ok=True)
    pm = A12 / "panel_mount_audit"
    tc = A12 / "trill_mount_candidate"
    mapping = json.loads((pm / "report.json").read_text())
    back = json.loads((tc / "report.json").read_text())
    err = json.loads((tc / "PM01-erratum.json").read_text())
    assert err["affected_report_sha256"] == sha(pm / "report.json") and err["correct_mm"] == [34.6, 42.2]
    assert mapping["panel_shift_mm"] == 7.6 and back["design"]["upper_mating_z_mm"] == 42.2
    for d in [pm, tc]:
        seal = json.loads((d / "handoff.json").read_text())
        assert all(sha(d / name) == h for name, h in seal["files_sha256"].items()), ("Stale sealed audit", d)
    lever = json.loads((A12 / "enclosure_growth/lever-fit/analysis.json").read_text())
    lever_proof = json.loads((A12 / "enclosure_growth/lever-fit/verification.json").read_text())
    assert lever_proof["lifted_lever_native_geometry_checks_clear"] and not lever_proof["changed_inputs"]
    mounts = [r["candidate"] for r in mapping["board_mounts"]]
    assert mounts == lever["mounts"] and len(mounts) == 34
    physical = packet({"P03": P03, "E28": E28})
    assert (
        sha(P03 / "power_p03.kicad_pcb") == "db83a26f98e3638d7b1a723be5d54f71c4e3aaa5418021e5b9003afea810283d"
    )
    assert (
        sha(E28 / "rail_disconnect.kicad_pcb")
        == "fed472582baae77623eb76495e82da3286fbedd94ca43a41858120a419ca5cc8"
    )
    # Actual candidate proof must be complete; no prospective native board binding.
    native = json.loads((receiver / "generated/native.json").read_text())
    pcb = receiver / "processor_carrier.kicad_pcb"
    assert native["candidate_pcb_sha256"] == sha(pcb) and not any(native["counts"].values())
    raw = json.loads((receiver / "generated/drc.json").read_text())
    assert not any(raw[k] for k in ["violations", "unconnected_items", "schematic_parity"])
    erc = json.loads((receiver / "generated/erc.json").read_text())
    assert all(not sheet["violations"] for sheet in erc["sheets"])
    tree = read_sexpr(pcb.read_text())
    fps = {
        next(p[2] for p in children(f, "property") if p[1] == "Reference"): f
        for f in children(tree, "footprint")
    }
    h9 = fps["H9"]
    h9xy = transform(h9, first(children(h9, "pad")[0], "at")[1:3])
    assert [round(h9xy[0] - 70, 6), round(h9xy[1] - 58, 6)] == [182, 92.2]
    receiver_holes = actual_bores(tree)
    pad_receipts = {}
    joints = []
    for ref, fp in fps.items():
        if ref not in ["J13", "J14", "J15"]:
            continue
        x0, y0, x1, y1 = courtyard(fp, "F.CrtYd")
        joints.append([ref + "_joint", x0 - 70 - 0.5, y0 - 58 - 0.5, 8.1, x1 - x0 + 1, y1 - y0 + 1, 11.31])
        points = []
        for p in children(fp, "pad"):
            x, y = transform(fp, first(p, "at")[1:3])
            xy = [round(x - 70, 6), round(y - 58, 6)]
            points.append([str(p[1]), *xy, float(first(p, "drill")[1])])
            joints.append([ref + "_tail_" + str(p[1]), xy[0] - 1.7, xy[1] - 1.7, 5, 3.4, 3.4, 1.5])
        pad_receipts[ref] = points
    assert pad_receipts["J13"] == [["1", 188, 100, 2.2], ["2", 188, 104, 2.2]]
    for b, folder, filename in [
        (physical["boards"][0], P03, "power_p03"),
        (physical["boards"][1], E28, "rail_disconnect"),
    ]:
        b["all_actual_drilled_pad_bores"] = actual_bores(
            read_sexpr((folder / (filename + ".kicad_pcb")).read_text())
        )
    # Retain the selected free curves exactly. Native receiving material is fresh.
    baseline = A12 / "harness/generated/receiver-full-route/analysis.json"
    route = json.loads(baseline.read_text())
    root_route_proof = json.loads(
        (A12 / "harness/generated/receiver-full-route/verification.json").read_text()
    )
    assert root_route_proof["whole_pair_native_geometry_clear"] and not root_route_proof["changed_inputs"]
    assert all(row["clear"] for row in root_route_proof["cases"].values())
    assert route["true_radius_requirement_mm"] == 9.6393
    assert all(r["central_external_tube_min_z_lower_mm"] > 8.46 for r in route["routes"])
    original = read_sexpr(
        (A12 / "harness/proposals/processor-awg18-ear-supported/processor_carrier.kicad_pcb").read_text()
    )
    oldfps = {
        next(p[2] for p in children(f, "property") if p[1] == "Reference"): f
        for f in children(original, "footprint")
    }
    for ref, f in oldfps.items():
        if ref != "H9":
            assert fps[ref] == f, ("Receiver mechanical footprint changed", ref)
    inherited = json.loads((A12 / "harness/generated/receiver-awg18/analysis.json").read_text())[
        "current_E19_component_packet"
    ]["bodies"]
    # J1 is explicitly unfitted service access. Do not call its old header a real body.
    e19 = [r for r in inherited if r[0] not in ["e19_J1", "e19_J1_lead_1", "e19_J1_lead_2"]]
    other = json.loads((pm / "baseline-other.json").read_text())
    boards = []
    env = []
    for row in mapping["boards"]:
        if row["id"] in ["dsp_carrier", "disconnect_carrier", "trill_craft"]:
            continue
        assert row["candidate"] is not None
        boards.append(row["candidate"])
    for row in mapping["envelopes"]:
        name = row["id"]
        if name.startswith(("disconnect_", "e19_")) or name == "trill_components":
            continue
        assert row["candidate"] is not None
        env.append(row["candidate"])
    env += e19 + other["port_envelopes"]
    # Native source own terminal joints are tested as joints, not obstacles.
    source_joints = [b for b in physical["boxes"] if b[0].startswith("E28_J4")]
    physical["boxes"] = [b for b in physical["boxes"] if not b[0].startswith("E28_J4")]
    hashes = dict(physical["source_sha256"])
    files = [
        pm / "report.json",
        pm / "handoff.json",
        pm / "baseline-other.json",
        tc / "report.json",
        tc / "handoff.json",
        tc / "PM01-erratum.json",
        tc / "generated/checks.scad",
        tc / "generated/saddle.stl",
        tc / "generated/verification.json",
        A12 / "enclosure_growth/lever-fit/analysis.json",
        A12 / "enclosure_growth/lever-fit/verification.json",
        baseline,
        A12 / "harness/generated/receiver-full-route/checks.scad",
        A12 / "harness/generated/receiver-full-route/verification.json",
        A12 / "harness/generated/receiver-awg18/analysis.json",
        A12 / "harness/proposals/processor-awg18-ear-supported/processor_carrier.kicad_pcb",
        pcb,
        receiver / "components.json",
        receiver / "generated/native.json",
        receiver / "generated/drc.json",
        receiver / "generated/erc.json",
        receiver / "handoff.json",
        receiver / "generated/current-native.json",
        Path(__file__),
    ]
    for key in ["source_sha256", "artifact_sha256"]:
        hashes.update(native[key])
    # Bind all recursively included/imported native CAD, including each real STL.
    pending = [A12 / "harness/generated/receiver-full-route/checks.scad", tc / "generated/checks.scad"]
    seen = set()
    while pending:
        p = pending.pop().resolve()
        if p in seen:
            continue
        seen.add(p)
        files.append(p)
        if p.suffix == ".scad":
            text = p.read_text()
            pending += [(p.parent / q).resolve() for q in re.findall(r"(?:include|use)\s*<([^>]+)>", text)]
            pending += [(p.parent / q).resolve() for q in re.findall(r'import\("([^"\n]+)"', text)]
    for p in files:
        hashes[str(p.relative_to(REPO))] = sha(p)
    for name, h in hashes.items():
        p = REPO / name
        assert sha(p) == h, ("Input changed before capture", name)
        dest = ROOT / "sources" / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(p.read_bytes())
    data = dict(
        mounts=mounts,
        other_boards=boards,
        inherited_envelopes=env,
        native_boards=physical["boards"],
        native_boxes=physical["boxes"],
        native_cylinders=physical["cylinders"],
        receiver_outline=outline(tree),
        receiver_holes=receiver_holes,
        receiver_joints=joints,
        source_joints=source_joints,
    )
    (OUT / "scene.json").write_text(json.dumps(data, indent=2) + "\n")
    meta = dict(
        scope=__doc__,
        source_sha256=hashes,
        shell_mm=[334, 188.4, 45.6],
        panel_z_mm=43.6,
        panel_translation_applied_once=True,
        PM01_touch_backer_erratum_applied=True,
        Trill_C3_used=True,
        E19_E18_E20_low_stack_preserved=True,
        receiver_source_pcb_sha256=sha(pcb),
        receiver_source_folder=str(receiver.relative_to(REPO)),
        receiver_native_counts=native["counts"],
        receiver_actual_ports=pad_receipts,
        physical_component_records=physical["component_records"],
        E28_source_pcb_sha256=sha(E28 / "rail_disconnect.kicad_pcb"),
        E28_electrical_opens_scope=45,
        E28_43open_growth_slab_substituted=False,
        unfitted_service_J1_header_removed=True,
        source_wire_points_mm=[r["start"] for r in route["routes"]],
        destination_wire_points_mm=[r["end"] for r in route["routes"]],
        source_and_receiver_bore_and_central_height_proofs_required=True,
        PCB_Z_sweep_each_mm=0.2,
        positive_hardware_intentional_contact_exclusions=[
            "P03_J24",
            "P03_J23",
            "E28_J10",
            "E28_J11",
            "P03_J20",
            "P03_J21",
            "E28_J7",
            "E28_J8",
        ],
        nine_lid_boss_positions_mm=[[x, y] for y in [8, 149, 180.4] for x in [8, 167, 326]],
        new_lid_hardware_qualified=False,
        old_thermal_base_still_334x157=True,
        enlarged_thermal_base_and_front_attachment_qualified=False,
        J14_J15_outgoing_harness_modelled=False,
        Trill_complete_loose_wiring_modelled=False,
        physical_qualified=False,
        thermal_qualified=False,
        fabrication_released=False,
    )
    (OUT / "analysis.json").write_text(json.dumps(meta, indent=2) + "\n")
    scad = "include <" + str(A12 / "harness/generated/receiver-full-route/checks.scad") + ">\n"
    scad += "include <" + str(tc / "generated/checks.scad") + ">\n"
    data["fanout_points"] = [[p[1], p[2], 8.1] for rows in pad_receipts.values() for p in rows]
    for key, value in data.items():
        if key == "native_boards":
            value = [
                [
                    b["id"],
                    b["datum"],
                    b["nominal_thickness_mm"],
                    b["outline_relative_mm"],
                    b["all_actual_drilled_pad_bores"],
                ]
                for b in value
            ]
        scad += "ui_" + key + "=" + json.dumps(value) + ";\n"
    scad += """
ui_case="whole_geometry";
module ui_boxes(rows,m=0,zsweep=.2){for(b=rows)translate([b[1]-m,b[2]-m,b[3]-m-zsweep])cube([b[4]+2*m,b[5]+2*m,b[6]+2*m+2*zsweep]);}
module ui_cylinders(m=0){for(c=ui_native_cylinders)translate([c[1],c[2],c[3]-.2-m])cylinder(d=c[4]/cos(180/128)+2*m,h=c[5]+.4+2*m,$fn=128);}
module ui_drilled_hole(h,H,min_bore=false){power=min_bore&&in_list(h[5],["J13","J14","J15"]);dx=power?2.1:h[2];dy=power?2.1:h[3];translate([h[0],h[1],-.01])rotate([0,0,h[4]])hull()for(t=[-1,1])translate([dx>dy?t*(dx-dy)/2:0,dy>dx?t*(dy-dx)/2:0,0])cylinder(d=min(dx,dy),h=H,$fn=128);}
module ui_native_PCB(b,mounts=true){translate(b[1])difference(){linear_extrude(b[2])polygon(b[3]);if(mounts)for(h=b[4])ui_drilled_hole(h,b[2]+.02);}}
module ui_receiver(min_bores=false){translate([30,42,min_bores?6.3:6.5])difference(){linear_extrude(min_bores?2.16:1.6)polygon(ui_receiver_outline);for(h=ui_receiver_holes)ui_drilled_hole(h,2.18,min_bores);}}
module ui_PCBS(exclude_own=false){for(b=ui_native_boards)if(!(exclude_own&&b[0]=="E28"))ui_native_PCB(b);if(!exclude_own)ui_receiver();for(b=ui_other_boards)board_reserve(b);board();}
module ui_components(include_trill=true){ui_boxes(ui_native_boxes);ui_cylinders();ui_boxes(ui_inherited_envelopes);if(include_trill){components();tails();}}
module ui_electronics(exclude_own=false){ui_PCBS(exclude_own);ui_components();}
module ui_contact_filtered_components(){ui_boxes([for(b=ui_native_boxes)if(!in_list(b[0],["P03_J24","P03_J23","E28_J10","E28_J11","P03_J20","P03_J21","E28_J7","E28_J8"]))b]);ui_cylinders();ui_boxes(ui_inherited_envelopes);components();tails();}
function in_list(x,rows)=len([for(y=rows)if(x==y)y])>0;
module ui_all_relative_ports(){for(p=ui_fanout_points){pf_sweep([[p[0],p[1],5],[p[0],p[1],11.2]],1.005);intersection(){pf_sweep([[p[0],p[1],15.1],[p[0],p[1],11.2]],1.1813);pf_above(11.2-.305);}}}
module ui_h9_tool(){translate([182,92.2,8.1])cylinder(d=6.5,h=52,$fn=128);}
module ui_h9_reserve(){translate([182,92.2,2.25])cylinder(d=8.1,h=4.7,$fn=128);translate([182,92.2,7.65])cylinder(d=6.5,h=3.21,$fn=128);}
module ui_receiver_joint(include_input=true,m=0){ui_boxes([for(b=ui_receiver_joints)if(include_input||!in_list(b[0],["J13_joint","J13_tail_1","J13_tail_2"]))b],m);}
module ui_source_joint(m=0){ui_boxes(ui_source_joints,m);}
module ui_h9_post(){difference(){translate([182,92.2,2.7])cylinder(d=7.2,h=3.8,$fn=128);translate([182,92.2,3.2])cylinder(d=3.2,h=3.31,$fn=128);}}
module ui_h9_head(){translate([182,92.2,8.1])cylinder(d=5.6,h=2.31,$fn=128);translate([182,92.2,4.1])cylinder(d=2.05,h=4,$fn=128);}
module ui_shell(){retained_thermal_shell();ui_h9_post();}
module ui_lid(){translate([0,0,panel_z])front_panel();}
module ui_mechanics(){translate([0,0,7.6]){lever_bracket();lever_sweep();}translate([0,0,panel_z-guide_thick])guide_plate();touch_backer();for(b=buttons)button_pose(b){switch_holder(b);key_sweep(b);}a12_switch_electronics();for(k=knobs)translate([k[1],k[2],shell_height+2.8])knob(k[3],k[4]);for(c=caps)if(c[1]=="switch")translate([c[2],c[3],panel_z])selector_cap();}
module ui_optics(){translate([244,78,shell_height])ring_lens();translate([74.8,125.8,35.2+panel_z-34])touch_lens();translate([160,31,35.6+panel_z-34])display_lens();for(y=[21.25,35.25])translate([43.9,y,33.2+panel_z-34])meter_lens();for(x=[82,101,120,139])translate([x,103,33.2+panel_z-34])bank_lens();}
module ui_controls(){ui_mechanics();ui_optics();}
module ui_power_hardware(){hardware();lower_shell_fasteners();}
module ui_case_shell(){ui_shell();rear_panel();thermal_metal_base();}
module ui_case_and_lid(){ui_case_shell();ui_lid();}
module ui_controls_and_lid(){ui_controls();ui_lid();}
module ui_environment(){ui_case_shell();ui_lid();ui_controls();}
module ui_shell_rear(){ui_shell();rear_panel();}
module ui_power_h9(){ui_power_only();ui_h9_head();}
module ui_trill_mount(){saddle();hardware();}
// The importedTC01 hardware() name would shadow the ROOT power hardware.
// Use explicit source artifacts for power hardware to avoid that ambiguity.
module ui_power_only(){return_assembly();import("POWER_POSITIVE_STL");lower_shell_fasteners();}
module ui_all_joints(m=0){ui_source_joint(m);ui_receiver_joint(true,m);}
module ui_wire_obstacles(){ui_electronics(true);ui_receiver_joint(false);ui_h9_head();}
if(ui_case=="whole_geometry"){ui_case_shell();ui_lid();ui_controls();ui_electronics();ui_power_only();pf_wires();ui_all_joints();ui_trill_mount();ui_h9_head();}
if(ui_case=="electronics_geometry")ui_electronics();
if(ui_case=="controls_geometry")ui_controls();
if(ui_case=="receiver_PCB_geometry")ui_receiver();
if(ui_case=="wire_geometry"){pf_wires();ui_all_joints();}
if(ui_case=="case_electronics_collision")intersection(){union(){translate([0,0,.00002])ui_PCBS();ui_components();}ui_case_and_lid();}
if(ui_case=="controls_electronics_collision")intersection(){ui_controls();ui_electronics();}
if(ui_case=="power_electronics_collision")intersection(){ui_power_only();union(){ui_PCBS();ui_contact_filtered_components();ui_receiver_joint();}}
if(ui_case=="power_controls_collision")intersection(){ui_power_only();ui_controls_and_lid();}
if(ui_case=="power_case_collision")intersection(){translate([0,0,.00002])ui_power_only();ui_shell_rear();}
if(ui_case=="wire_electronics_collision")intersection(){pf_wires(.25);ui_wire_obstacles();}
if(ui_case=="joint_electronics_collision")intersection(){ui_all_joints(.25);ui_electronics(true);}
if(ui_case=="wire_controls_case_collision")intersection(){pf_wires(.25);ui_environment();}
if(ui_case=="joint_controls_case_collision")intersection(){ui_all_joints(.25);ui_environment();}
if(ui_case=="wire_power_collision")intersection(){pf_wires(.25);ui_power_h9();}
if(ui_case=="trill_other_electronics_collision")intersection(){translate([0,0,-.00002])ui_trill_mount();ui_electronics();}
if(ui_case=="trill_power_collision")intersection(){ui_trill_mount();ui_power_only();}
if(ui_case=="trill_controls_collision")intersection(){translate([0,0,-.00002])ui_trill_mount();ui_controls_and_lid();}
if(ui_case=="joint_power_collision")intersection(){ui_all_joints(.25);ui_power_h9();}
if(ui_case=="receiver_joints_mutual_collision")for(i=[0:2],j=[0:2])if(i<j)intersection(){ui_boxes([for(b=ui_receiver_joints)if(in_list(b[0],[str("J",13+i,"_joint"),str("J",13+i,"_tail_1"),str("J",13+i,"_tail_2")]))b],.25);ui_boxes([for(b=ui_receiver_joints)if(in_list(b[0],[str("J",13+j,"_joint"),str("J",13+j,"_tail_1"),str("J",13+j,"_tail_2")]))b]);}
if(ui_case=="all_receiver_bores_collision")intersection(){ui_all_relative_ports();ui_receiver(true);}
if(ui_case=="H9_tool_ports_collision")intersection(){ui_h9_tool();ui_receiver_joint(true,.25);}
if(ui_case=="H9_head_post_ports_collision")intersection(){ui_h9_reserve();ui_receiver_joint();}
if(ui_case=="all_ports_geometry")ui_all_relative_ports();
if(ui_case=="all_ports_positive_control")intersection(){ui_all_relative_ports();translate([191.9,84.4,7])cube([.2,.2,.2]);}
if(ui_case=="H9_tool_positive_control")intersection(){ui_h9_tool();translate([181.9,92.1,30])cube([.2,.2,.2]);}
if(ui_case=="source_bore_collision")intersection(){pf_relative_source();pf_source_PCB();}
if(ui_case=="receiver_bore_collision")intersection(){pf_relative_receiver();ui_receiver(true);}
if(ui_case=="wire_pair_collision")intersection(){pf_wire(0,.25);pf_wire(1);}
if(ui_case=="receiver_PCB_positive_control")intersection(){ui_receiver();translate([190,90,7])cube([.2,.2,.2]);}
if(ui_case=="wire_positive_control")intersection(){pf_bare(1);translate([187.9,103.9,8.5])cube([.2,.2,.2]);}
if(ui_case=="trill_mount_positive_control")intersection(){saddle();translate([75.2,122.9,35])cube([.2,.2,.2]);}
if(ui_case=="raised_switch_positive_control")intersection(){a12_switch_electronics();translate([133.9,21.9,36])cube([.2,.2,.2]);}
if(ui_case=="front_case_positive_control")intersection(){ui_shell();translate([166.9,187,41.9])cube([.2,.2,.2]);}
"""
    # Prefix every TC01 module in an exact derived copy. Its aperture() and
    # hardware() are local concepts, never replacements for A11/ROOT modules.
    tc_text = (tc / "generated/checks.scad").read_text()
    tc_modules = re.findall(r"module\s+(\w+)\s*\(", tc_text)
    assert set(tc_modules) == {"corners", "saddle", "board", "components", "tails", "hardware", "aperture"}
    tc_text = re.sub(r"\b(" + "|".join(tc_modules) + r")\s*\(", lambda m: "tc_" + m.group(1) + "(", tc_text)
    (OUT / "trill-derived.scad").write_text(tc_text)
    scad = scad.replace(
        "include <" + str(tc / "generated/checks.scad") + ">", "use <" + str(OUT / "trill-derived.scad") + ">"
    )
    scad = re.sub(r"\b(saddle|board|components|tails)\s*\(", lambda m: "tc_" + m.group(1) + "(", scad)
    scad = scad.replace("POWER_POSITIVE_STL", str(A12 / "positive_links/generated/positive-links.stl"))
    scad = scad.replace(
        "module ui_trill_mount(){tc_saddle();hardware();}",
        "module ui_trill_mount(){tc_saddle();tc_hardware();}",
    )
    (OUT / "checks.scad").write_text(scad)
    print(
        json.dumps(
            dict(
                source_count=len(hashes),
                receiver=meta["receiver_source_pcb_sha256"],
                boards=len(boards),
                envelopes=len(env),
                source_components=len(physical["component_records"]),
            )
        )
    )
    return meta


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--receiver", type=Path, default=DEFAULT_RECEIVER)
    a = p.parse_args()
    stage(a.receiver)
