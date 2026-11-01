"""EI02 repaired scene; EI01 failures remain historical evidence, never overwritten."""

import hashlib
import json
import re
from pathlib import Path

from hardware.cad.a12.enclosure_growth.integration.stage import actual_bores
from hardware.cad.a12.repaired import outline
from hardware.electronics.common.sexpr import children, first, read_sexpr
from hardware.electronics.output_stage.check_placement import courtyard, transform

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[4]
A12 = ROOT.parents[1]
OUT = ROOT / "generated"
EI = A12 / "enclosure_growth/integration"
TC = A12 / "trill_front_bay"
REAR = A12 / "enclosure_growth/rear-ports"
RECEIVER = A12 / "harness/proposals/processor-awg18-ear-fanout-j29-central"


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def stage():
    OUT.mkdir(exist_ok=True)
    for parent in [EI, TC]:
        s = json.loads((parent / "handoff.json").read_text())
        assert all(sha(parent / n) == h for n, h in s["files_sha256"].items())
    rp = json.loads((REAR / "analysis.json").read_text())
    proof = json.loads((REAR / "verification.json").read_text())
    assert proof["rear_body_envelope_native_checks_clear"] and not proof["changed_inputs"]
    base = json.loads((EI / "generated/scene.json").read_text())
    meta = json.loads((EI / "generated/analysis.json").read_text())
    pcb = RECEIVER / "processor_carrier.kicad_pcb"
    assert sha(pcb) == "3b2a8197e1452c00fb9f7a99a3730cfb97fe176e7f5f41ee6a8a732a843e8ed6"
    n = json.loads((RECEIVER / "generated/native.json").read_text())
    assert n["candidate_pcb_sha256"] == sha(pcb) and not any(n["counts"].values())
    tree = read_sexpr(pcb.read_text())
    fps = {
        next(p[2] for p in children(f, "property") if p[1] == "Reference"): f
        for f in children(tree, "footprint")
    }
    old_source = A12 / "harness/proposals/processor-awg18-ear-fanout-j29/processor_carrier.kicad_pcb"
    old_tree = read_sexpr(old_source.read_text())
    old_fps = {
        next(p[2] for p in children(f, "property") if p[1] == "Reference"): f
        for f in children(old_tree, "footprint")
    }
    assert set(old_fps) == set(fps) and len(fps) == 88
    assert all(fps[k] == f for k, f in old_fps.items() if k != "J29"), "Unexpected other footprint change"
    f = fps["J29"]
    x0, y0, x1, y1 = courtyard(f, "F.CrtYd")
    j29 = [
        "e19_J29",
        round(x0 - 70 - 0.5, 6),
        round(y0 - 58 - 0.5, 6),
        8.1,
        round(x1 - x0 + 1, 6),
        round(y1 - y0 + 1, 6),
        11.31,
    ]
    assert j29[1:] == [102.73, 73.73, 8.1, 4.54, 9.62, 11.31]
    ports = {p[0] for p in rp["candidate_port_envelopes"]}
    inherited = [
        r for r in base["inherited_envelopes"] if not r[0].startswith("e19_J29") and r[0] not in ports
    ] + [j29]
    for p in children(f, "pad"):
        x, y = transform(f, first(p, "at")[1:3])
        inherited.append(["e19_J29_lead_" + str(p[1]), x - 71, y - 59, 3.35, 2, 2, 3.15])
    scene = dict(
        base,
        inherited_envelopes=inherited,
        receiver_outline=outline(tree),
        receiver_holes=actual_bores(tree),
        rear_ports=rp["candidate_rear_ports"],
        rear_port_reserves=rp["candidate_port_envelopes"],
    )
    context = (TC / "generated/context-derived.scad").read_text()
    for key, value in [
        ("ui_inherited_envelopes", inherited),
        ("ui_receiver_outline", outline(tree)),
        ("ui_receiver_holes", actual_bores(tree)),
        ("ui_rear_port_reserves", rp["candidate_port_envelopes"]),
    ]:
        context, count = re.subn(
            "^" + key + r"=.*;$", key + "=" + json.dumps(value) + ";", context, flags=re.M
        )
        assert count == 1
    # Old diagnostic owners are preserved in EI01, not run as new geometry tests.
    context = re.sub(r'^if\(ui_case=="isolate_[^\n]+\n', "", context, flags=re.M)
    context = context.replace("tc_board();", "tc2_board();")
    lines = context.splitlines()
    new = []
    for line in lines:
        if line.startswith("module ui_components("):
            line = "module ui_components(include_trill=true){ui_boxes(ui_native_boxes);ui_cylinders();ui_boxes(ui_inherited_envelopes);ui_rear_bodies();if(include_trill)tc2_components();}"
        elif line.startswith("module ui_contact_filtered_components("):
            line = 'module ui_contact_filtered_components(){ui_boxes([for(b=ui_native_boxes)if(!in_list(b[0],["P03_J24","P03_J23","E28_J10","E28_J11","P03_J20","P03_J21","E28_J7","E28_J8"]))b]);ui_cylinders();ui_boxes(ui_inherited_envelopes);ui_rear_bodies();tc2_components();}'
        elif line.startswith("module ui_trill_mount(){"):
            line = "module ui_trill_mount(){tc2_posts();tc2_heads();}"
        elif line.startswith("module ui_trill_mount_compare(){"):
            line = "module ui_trill_mount_compare(){translate([0,0,-.00002])tc2_posts();translate([0,0,.00002])tc2_heads();}"
        elif line.startswith("module ui_case_shell(){"):
            line = "module ui_case_shell(){ui_shell();tc2_posts();rear_panel();thermal_metal_base();}"
        if line.startswith('if(ui_case=="trill_mount_positive_control")'):
            line = 'if(ui_case=="trill_mount_positive_control")intersection(){tc2_posts();translate([132.9,168.8,10])cube([.2,.2,.2]);}'
        new.append(line)
    context = "\n".join(new) + "\n"
    # Reuse only the frozen TC02 module definitions/data, without a second include or top-level cases.
    tcsource = (TC / "generated/checks.scad").read_text().splitlines()
    tcmodules = "\n".join(l for l in tcsource[1:] if not l.startswith("if(tc2_case==")) + "\n"
    extra = """
module ui_rear_bodies(m=0){for(b=ui_rear_port_reserves)translate([b[1]-m,.00002,b[3]-.2-m])cube([b[4]+2*m,b[5]+m,b[6]+.4+2*m]);}
module ei_native_components(id="all",m=0){ui_boxes([for(b=concat(ui_native_boxes,ui_source_joints))if(id=="all"||substr_id(b[0],id))b],m);for(c=ui_native_cylinders)if(id=="all"||substr_id(c[0],id))translate([c[1],c[2],c[3]-.2-m])cylinder(d=c[4]/cos(180/128)+2*m,h=c[5]+.4+2*m,$fn=128);}
function substr_id(name,id)=len(id)==3?(name[0]==id[0]&&name[1]==id[1]&&name[2]==id[2]):name==id;
module ei_case_obstacles(){ui_environment();lower_shell_fasteners();return_retention();tc2_posts();tc2_heads();ui_h9_head();}
module ei_other_electronics(){ui_receiver();for(b=ui_other_boards)board_reserve(b);ui_boxes(ui_inherited_envelopes);ui_rear_bodies();ui_receiver_joint();tc2_board();tc2_components();tc2_posts();tc2_heads();}
module ei_native_board(id){for(b=ui_native_boards)if(b[0]==id)ui_native_PCB(b);}
if(ui_case=="native_component_case_0p25_collision")intersection(){ei_native_components("all",.25);ei_case_obstacles();}
if(ui_case=="native_component_other_0p25_collision")intersection(){ei_native_components("all",.25);ei_other_electronics();}
if(ui_case=="native_boards_mutual_0p25_collision")intersection(){union(){ei_native_board("P03");ei_native_components("P03",.25);}union(){ei_native_board("E28");ei_native_components("E28",.25);}}
if(ui_case=="rear_body_case_0p25_collision")intersection(){ui_rear_bodies(.25);ui_case_and_lid();}
if(ui_case=="H9_openlid_tool_electronics_collision")intersection(){ui_h9_tool();union(){ui_electronics(true);ui_receiver_joint();tc2_heads();}}
if(ui_case=="H9_openlid_tool_power_case_collision")intersection(){ui_h9_tool();union(){ui_case_shell();ui_power_only();}}
if(ui_case=="trill_frontbay_geometry")tc2_new_material();
module ei_box_margin_witness(){for(b=ui_native_boxes)if(b[0]=="E28_U18")translate([b[1]-.225,b[2]+.25,b[3]+.25])cube([.2,.2,.2]);}
module ei_cylinder_margin_witness(){for(c=ui_native_cylinders)if(c[0]=="E28_C8")translate([c[1]+c[4]/cos(180/128)/2+.025,c[2]-.1,10])cube([.2,.2,.2]);}
if(ui_case=="native_component_clearance_positive_control")intersection(){ei_native_components("E28_U18",.25);ei_box_margin_witness();}
if(ui_case=="native_nominal_strip_negative_control_collision")intersection(){ei_native_components("E28_U18",0);ei_box_margin_witness();}
if(ui_case=="native_cylinder_clearance_positive_control")intersection(){ei_native_components("E28_C8",.25);ei_cylinder_margin_witness();}
if(ui_case=="native_cylinder_nominal_negative_control_collision")intersection(){ei_native_components("E28_C8",0);ei_cylinder_margin_witness();}
"""
    (OUT / "checks.scad").write_text(context + tcmodules + extra)
    hashes = dict(json.loads((TC / "generated/analysis.json").read_text())["source_sha256"])
    files = [
        Path(__file__),
        EI / "handoff.json",
        EI / "generated/verification.json",
        EI / "findings.json",
        TC / "handoff.json",
        TC / "generated/analysis.json",
        TC / "generated/verification.json",
        TC / "generated/checks.scad",
        TC / "generated/context-derived.scad",
        TC / "generated/posts.step",
        TC / "generated/geometry.stl",
        REAR / "analysis.json",
        REAR / "verification.json",
        REAR / "checks.scad",
        RECEIVER / "handoff.json",
        RECEIVER / "generated/native.json",
        RECEIVER / "generated/current-native.json",
        pcb,
        RECEIVER / "components.json",
        A12 / "repaired-integration.scad",
        A12 / "thermal/verify.py",
        A12 / "harness/receiver_support_fit.py",
    ]
    for p in files:
        hashes[str(p.relative_to(REPO))] = sha(p)
    for name, h in hashes.items():
        p = REPO / name
        data = p.read_bytes()
        assert hashlib.sha256(data).hexdigest() == h, name
        target = ROOT / "sources" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    meta.update(
        scope=__doc__,
        source_sha256=hashes,
        receiver_source_pcb_sha256=sha(pcb),
        receiver_source_folder=str(RECEIVER.relative_to(REPO)),
        J29_actual_service_requirement=j29,
        TC02_origin_mm=[82, 158, 20],
        rear_ports=rp["candidate_rear_ports"],
        audio_centres_Z_mm=14,
        EI01_used_as_failed_historical_evidence_only=True,
        native_external_clearance_mm=0.25,
        native_extra_Z_uncertainty_each_mm=0.2,
        native_thicknessrange_already_in_components=True,
        nominal_and_0p25_cases_separate=True,
        rear_mating_face_correlated_Y0=True,
        roof_and_guide_removal_required_for_tool_access=True,
        actual_canonical_boards_modified=False,
        enlarged_thermalbase_implemented=False,
        allphysical_hardware_process_electrical_flags=False,
        physical_qualified=False,
        thermal_qualified=False,
        fabrication_released=False,
    )
    (OUT / "scene.json").write_text(json.dumps(scene, indent=2) + "\n")
    (OUT / "analysis.json").write_text(json.dumps(meta, indent=2) + "\n")
    print(json.dumps(dict(inputs=len(hashes), J29=j29, receiver=sha(pcb))))
    return meta


if __name__ == "__main__":
    stage()
