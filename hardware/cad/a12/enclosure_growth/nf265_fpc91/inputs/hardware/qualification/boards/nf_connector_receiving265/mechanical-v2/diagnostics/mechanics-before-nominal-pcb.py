"""Source-bound local strain prototype, receiving gauges and source errata."""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def build():
    out = ROOT / "mechanical-v2"
    if (out / "geometry.scad").exists():
        raise RuntimeError("Do not rewrite consumed geometry")
    plan = json.loads((ROOT / "ports-v2.json").read_text())
    native = json.loads((ROOT / "prototype-v1/native-ports.json").read_text())
    holes = []
    for port in plan["ports"]:
        delta = 1 if port["ref"] == "J4" else 0
        for p in native["actual"][port["ref"]]["pads"].values():
            holes.append([p["at_mm"][0] + delta, p["at_mm"][1], p["drill_mm"]])
    boxes = []
    for port in plan["ports"]:
        u, v = port["anchor_mm"]
        a, b, c, d = port["receiving_body_uv_bounds_mm"]
        boxes.append([u + a, v + b, 0, c - a, d - b, port["receiving_body_front_normal_mm"]])
    text = """// NC265 source-bound LOCAL interface prototype; no full265 board/harness fit.
case_name="none";
module nc265_box(b,g=0){translate([b[0]-g,b[1]-g,b[2]-g])cube([b[3]+2*g,b[4]+2*g,b[5]+2*g]);}
module nc265_world(){multmatrix([[1,0,0,172],[0,0,-1,180.5],[0,1,0,3.5],[0,0,0,1]])children();}
module nc265_post(maximum=false){for(u=[61,90])translate([u,21,0])cylinder(d=maximum?6.1:6,h=5,$fn=128);}
module nc265_channels(){for(u=[68,73,79,84])translate([u,21,4.7])cylinder(d=1.65,h=8.5,$fn=128);}
module nc265_base(assembly=false){difference(){union(){nc265_box([58,17.5,4.8,35,3.5,8.2]);nc265_post();}nc265_channels();
 for(u=[61,90]){translate([u,21,-.01])cylinder(d=1.6,h=4.11,$fn=96);
 if(assembly)translate([u,21,-.01])cylinder(d=2.04,h=3.06,$fn=96);
 translate([u,21.01,9])rotate([90,0,0])cylinder(d=1.6,h=3.01,$fn=96);
 if(assembly)translate([u,21.01,9])rotate([90,0,0])cylinder(d=2.04,h=2.16,$fn=96);}}}
module nc265_cap(){difference(){nc265_box([58,21,5.3,35,3.5,7.7]);nc265_channels();for(u=[61,90])translate([u,24.6,9])rotate([90,0,0])cylinder(d=2.6,h=3.7,$fn=96);}}
module nc265_hardware(){for(u=[61,90]){
 translate([u,21,-1.95]){cylinder(d=2,h=5,$fn=96);translate([0,0,-1.72])cylinder(d=4,h=1.72,$fn=96);}
 translate([u,21,-1.95])difference(){cylinder(d=5,h=.35,$fn=96);translate([0,0,-.01])cylinder(d=2.2,h=.37,$fn=96);}
 translate([u,24.85,9])rotate([90,0,0]){cylinder(d=2,h=6,$fn=96);translate([0,0,-1.72])cylinder(d=4,h=1.72,$fn=96);}
 translate([u,24.85,9])rotate([90,0,0])difference(){cylinder(d=5,h=.35,$fn=96);translate([0,0,-.01])cylinder(d=2.2,h=.37,$fn=96);}}}
module nc265_strain_world(){nc265_world(){nc265_base(true);nc265_cap();nc265_hardware();}}
module nc265_strain_receiving_world(){nc265_world(){nc265_post(true);nc265_box([58,17.5,4.8,35,3.5,8.2]);nc265_box([58,21,5.3,35,3.5,7.7]);
 for(u=[61,90]){translate([u,21,-3.83])cylinder(d=5,h=2.39,$fn=128);translate([u,26.57,9])rotate([90,0,0])cylinder(d=5,h=3.57,$fn=128);}}}
module nc265_pcb(minimum_force_bore=false){difference(){nc265_box([0,0,-1.76,149,39,1.76]);
 for(h=NC265_HOLES)translate([h[0],h[1],-1.8])cylinder(d=(minimum_force_bore&&h[2]>2)?2.1:h[2],h=1.9,$fn=128);
 for(u=[61,90])translate([u,21,-1.8])cylinder(d=2.5,h=1.9,$fn=128);}}
module nc265_port_receivers(g=0){for(b=NC265_BOXES)nc265_box(b,g);}
module nc265_interface_receivers_world(){nc265_world()nc265_port_receivers();}
module nc265_force_gauges(){for(u=[68,73,79,84])translate([u,21,-1.8])cylinder(d=2.01,h=1.9,$fn=128);}
module nc265_mount_gauges(){for(u=[61,90])translate([u,21,-1.8])cylinder(d=2.41,h=1.9,$fn=128);}
module nc265_wire_prototype(){for(u=[68,73,79,84])translate([u,21,3.1])cylinder(d=1.7,h=12.9,$fn=128);}
module nc265_grip_contact_mask(){for(u=[68,73,79,84])translate([u,21,4.8])cylinder(d=1.9,h=8.2,$fn=128);}
if(case_name=="base_part")nc265_base();
if(case_name=="cap_part")nc265_cap();
if(case_name=="assembly_review"){nc265_pcb();nc265_port_receivers();nc265_base(true);nc265_cap();nc265_hardware();nc265_wire_prototype();}
if(case_name=="ports_pair_margin")for(i=[0:4])for(j=[i+1:5])intersection(){nc265_box(NC265_BOXES[i],.25);nc265_box(NC265_BOXES[j]);}
if(case_name=="force_solder_post_margin")intersection(){for(i=[1,3])nc265_box(NC265_BOXES[i],.45);nc265_post(true);}
if(case_name=="force_solder_bridge_margin")intersection(){for(i=[1,3])nc265_box(NC265_BOXES[i],.45);union(){nc265_base();nc265_cap();}}
if(case_name=="ports_other_strain_margin")intersection(){for(i=[0,2,4,5])nc265_box(NC265_BOXES[i],.45);union(){nc265_base();nc265_cap();nc265_hardware();}}
if(case_name=="own_PCB_seats")intersection(){nc265_pcb();union(){nc265_base();nc265_cap();nc265_port_receivers();}}
if(case_name=="mount_gauge_min_bores")intersection(){nc265_mount_gauges();nc265_pcb();}
if(case_name=="force_gauge_min_bores")intersection(){nc265_force_gauges();nc265_pcb(true);}
if(case_name=="old_mount_bore_witness")intersection(){translate([90,21,-1.76])cylinder(d=2.41,h=1.76,$fn=128);difference(){nc265_box([87,18,-1.76,6,6,1.76]);translate([90,21,-1.8])cylinder(d=2.3,h=1.9,$fn=128);}}
if(case_name=="old_force_bore_witness")intersection(){translate([68,21,-1.76])cylinder(d=2.01,h=1.76,$fn=128);difference(){nc265_box([65,18,-1.76,6,6,1.76]);translate([68,21,-1.8])cylinder(d=1,h=1.9,$fn=128);}}
if(case_name=="wire_outside_grip_collision")difference(){intersection(){nc265_wire_prototype();union(){nc265_base();nc265_cap();}}nc265_grip_contact_mask();}
if(case_name=="intentional_grip_contact_witness")intersection(){nc265_wire_prototype();union(){nc265_base();nc265_cap();}}
if(case_name=="hardware_receiving_threads")intersection(){nc265_hardware();union(){nc265_base(true);nc265_cap();}}
if(case_name=="uncut_thread_pilots_witness")intersection(){nc265_hardware();nc265_base(false);}
if(case_name=="base_cap_nonseat_overlap")intersection(){nc265_base();nc265_cap();}
if(case_name=="control_contact_point")intersection(){nc265_base();nc265_box([59,18.5,6, .2,.2,.2]);}
"""
    prefix = "NC265_HOLES=" + json.dumps(holes) + ";\nNC265_BOXES=" + json.dumps(boxes) + ";\n"
    (out / "geometry.scad").write_text(prefix + text)
    dims = dict(
        revision="NC265-actual-strain-datums-v2",
        source_ports_sha256=sha(ROOT / "ports-v2.json"),
        source_initial_ports_sha256=sha(ROOT / "ports.json"),
        actual_source_bores=holes,
        post=dict(
            centres=[[61, 21], [90, 21]], nominal_OD_mm=6, maximum_receiving_OD_mm=6.1, normal_mm=[0, 5]
        ),
        base_bridge_bounds_uv_w_mm=[58, 17.5, 4.8, 93, 21, 13],
        cap_bounds_uv_w_mm=[58, 21, 5.3, 93, 24.5, 13],
        posts_overlap_lower_bridge_mm=0.2,
        post_end_to_cap_normal_gap_mm=0.3,
        post_to_J4_solder_box_gap_receiving_mm=0.55,
        combined_relative_and_clearance_mm=0.45,
        physical_load_path="Gripping matched channels -> PEEK base/posts -> H101/H102 -> actual PCB/carrier mounts (strength unqualified)",
        matched_channel_trial=dict(
            prototype_wire_diameter_mm=1.7,
            prototype_channel_diameter_mm=1.65,
            production_rule="Measure EACH wire and machine its paired semicircular channel to measuredOD minus0.05mm trial",
            wire_measurement_expanded_uncertainty_max_trial_mm=0.01,
            channel_machine_tolerance_trial_mm=0.02,
            resulting_diametric_interference_trial_mm=[0.02, 0.08],
            trial_is_NOT_approved_insulation_compression_or_pull_requirement=True,
            channels_u_mm=[68, 73, 79, 84],
            centre_v_mm=21,
            normal_contact_interval_mm=[4.8, 13],
        ),
        material=dict(
            grade="MCAM Ketron1000 natural unfilled PEEK",
            indicative_properties_NOT_guaranteed_allowables=True,
            original_pdf="inputs/references/primary/mcam-ketron1000-peek.pdf",
            supplier_material_lot_and_threads_approved=False,
        ),
        hardware=dict(
            mount_screw="Accu SPP-M2-5-A2",
            cap_screw="Accu SPP-M2-6-A2",
            washer="Accu HPW-M2-A2-BL",
            screw_head_diameter_max_catalog_mm=4,
            screw_head_height_max_catalog_mm=1.72,
            washer_OD_max_catalog_mm=5,
            washer_thickness_catalog_mm=[0.25, 0.35],
            washer_ID_catalog_mm=[2.2, 2.34],
            mount_screw_length_receiving_mm=[4.9, 5.1],
            cap_screw_length_receiving_mm=[5.9, 6.1],
            length_tolerances_are_incoming_PROJECT_requirements_NOT_catalog_guarantees=True,
            PCB_thickness_receiving_mm=[1.44, 1.76],
            nominal_mount_thread_engagement_mm=3.05,
            mount_engagement_receiving_mm=[2.79, 3.41],
            cap_thickness_receiving_mm=[3.45, 3.55],
            nominal_cap_thread_engagement_mm=2.15,
            cap_engagement_receiving_mm=[2.0, 2.4],
            rear_mount_max_normal_w_mm=-3.83,
            assembled_cap_hardware_max_v_mm=26.57,
            blind_M2_pilot_diameter_drawing_mm=1.6,
            mount_pilot_depth_mm=4.1,
            cap_base_pilot_depth_mm=3,
            assembly_thread_abstraction="ONLY actual nominal3.05/2.15mm overlap is voided to2.04diam; manufacturing parts retain1.6tap pilots",
            received_thread_engagement_torque_creep_and_repeated_service_qualified=False,
        ),
        manufacturing_sources=dict(
            mount_screw="https://www.accu.co.uk/pozi-pan-head-screws/9241-SPP-M2-5-A2",
            cap_screw="https://www.accu.co.uk/pozi-pan-head-screws/9242-SPP-M2-6-A2",
            washer="https://www.accu.co.uk/metric-flat-washers/179343-HPW-M2-A2-BL",
            PEEK="https://www.mcam.com/mam/52982/AEP-Ketron%C2%AE%201000%20PEEK_en_US.pdf",
        ),
        bare_force_board_bore_min_mm=2.1,
        bare_wire_envelope_with_centering_and_reserve_mm=2.01,
        force_wire_hard_bend_radius_receiving_mm=9.6393,
        chosen_future_bend_radius_mm=9.7,
        complete_force_routes_and_remote_ends_not_designed=True,
        physical_qualified=False,
        fabrication_released=False,
        full_board_fit_certified=False,
        source_sha256={
            str(p): sha(p)
            for p in [Path(__file__), ROOT / "ports-v2.json", ROOT / "prototype-v1/native-ports.json"]
        },
    )
    (out / "datums.json").write_text(json.dumps(dims, indent=2) + "\n")
    erratum = dict(
        parent_seal="bce8bfb8154395f2480742a1f37f3ecccc29d9fef96cdbb40567a20e4067845a",
        original_NP01_edited=False,
        correction="NP01 primary-facts KEMET_X7R page index only: actual PDF pages5/9, not listed1/3/6/8 for these facts",
        part="C0603C104K5RACTU",
        source_pdf_sha256=sha(ROOT / "inputs/references/primary/kemet-X7R-2026.pdf"),
        source_revision="2026-09-01",
        Table1A_pdf_page=5,
        Table2A_pdf_page=9,
        thickness_code="CJ",
        nominal_thickness_mm=0.8,
        tolerance_mm=0.15,
        maximum_body_thickness_mm=0.95,
        project_seat_mm=0.1,
        original_numeric_projection_mm=1.05,
        numeric_projection_changed=False,
    )
    (out / "NP01-primary-page-index-erratum.json").write_text(json.dumps(erratum, indent=2) + "\n")
    print(
        json.dumps(
            dict(
                actual_CAD_parts=2,
                prototypes_only=True,
                force_mount_min_diameter_mm=2.5,
                receiving_post_OD_max_mm=6.1,
            )
        )
    )


if __name__ == "__main__":
    build()
