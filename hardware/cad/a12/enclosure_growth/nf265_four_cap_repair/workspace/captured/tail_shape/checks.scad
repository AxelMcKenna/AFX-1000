// NEW actual NF265 + FPC91 receiving scene; captured parents only.
include <context/hardware/cad/a12/enclosure_growth/front_bay_receiving/mount_variant5/checks.scad>
include <context/hardware/qualification/boards/nf_connector_receiving265/mechanical-v2/geometry.scad>
nf_case="none";
module nf_components(id="all",m=0){fr_boxes(fr_boxes,id,m);}
module nf_tails(id="all",m=0){fr_boxes(fr_tails,id,m);}
module nf_mates(id="all",m=0){fr_boxes(fr_mates,id,m);}
module nf_body(id="all",m=0){nf_components(id,m);nf_tails(id,m);nf_mates(id,m);}
module nf_strain(m=0){if(m==0)nc265_strain_receiving_world();else minkowski(){nc265_strain_receiving_world();cube([2*m,2*m,2*m],center=true);}}
module nf_environment_case(){fr_case_environment();}
module nf_environment_electronics(){ui_electronics(false,false);tc2_posts();}
module nf_environment_power(){fr_power_environment();}
module nf_environment_wires(){pf_wires(.65);ui_all_joints(.25);}
for(id=["NF265","FPC91"]){
 if(nf_case==str(id,"_PCB_geometry"))intersection(){fr_PCB(id);fr_PCB(id,.01);}
 if(nf_case==str(id,"_components_geometry"))intersection(){nf_components(id);nf_components(id,.01);}
 if(nf_case==str(id,"_tails_geometry"))intersection(){nf_tails(id);nf_tails(id,.01);}
 if(nf_case==str(id,"_mates_geometry"))intersection(){nf_mates(id);nf_mates(id,.01);}
 if(nf_case==str(id,"_body_case_collision"))intersection(){fr_all_material(id,.45);nf_environment_case();}
 if(nf_case==str(id,"_body_electronics_collision"))intersection(){fr_all_material(id,.45);nf_environment_electronics();}
 if(nf_case==str(id,"_body_controls_collision"))intersection(){fr_all_material(id,.45);ua_all_controls();}
 if(nf_case==str(id,"_body_power_collision"))intersection(){fr_all_material(id,.45);nf_environment_power();}
 if(nf_case==str(id,"_body_wires_collision"))intersection(){fr_all_material(id,.45);nf_environment_wires();}
 if(nf_case==str(id,"_mate_other_components_collision"))for(a=fr_mates)if(fr_matches(a[0],id))for(b=fr_boxes)if(fr_matches(b[0],id)&&a[0]!=b[0])intersection(){fr_boxes([a],"all",.25);fr_boxes([b]);}
 if(nf_case==str(id,"_mate_mutual_collision"))for(i=[0:len(fr_mates)-1],j=[0:len(fr_mates)-1])if(i<j&&fr_matches(fr_mates[i][0],id)&&fr_matches(fr_mates[j][0],id))intersection(){fr_boxes([fr_mates[i]],"all",.25);fr_boxes([fr_mates[j]]);}
 if(nf_case==str(id,"_rear_tail_component_collision"))intersection(){nf_tails(id,.25);for(r=fr_boxes)if(fr_matches(r[0],id)&&r[2]>180.5)fr_boxes([r]);}
 if(nf_case==str(id,"_PCB_positive_control"))intersection(){fr_PCB(id);translate([id=="NF265"?180:30,181,10])cube([.2,.2,.2]);}
}
if(nf_case=="boards_and_receivers_mutual_collision")intersection(){fr_all_material("NF265",.65);fr_all_material("FPC91");}
if(nf_case=="strain_geometry")intersection(){nc265_strain_world();nc265_strain_receiving_world();}
if(nf_case=="strain_case_collision")intersection(){nf_strain(.45);nf_environment_case();}
if(nf_case=="strain_electronics_collision")intersection(){nf_strain(.45);nf_environment_electronics();}
if(nf_case=="strain_controls_collision")intersection(){nf_strain(.45);ua_all_controls();}
if(nf_case=="strain_power_collision")intersection(){nf_strain(.45);nf_environment_power();}
if(nf_case=="strain_wires_collision")intersection(){nf_strain(.45);nf_environment_wires();}
if(nf_case=="strain_other_board_collision")intersection(){nf_strain(.45);fr_all_material("FPC91");}
if(nf_case=="strain_NF_components_collision")intersection(){nf_strain(.25);nf_components("NF265");}
if(nf_case=="strain_NF_rear_tails_collision")intersection(){nf_strain(.25);nf_tails("NF265");}
if(nf_case=="strain_NF_mates_collision")intersection(){nf_strain(.25);nf_mates("NF265");}
if(nf_case=="new_mount_components_collision")intersection(){mr_new();nf_components("all",.45);}
if(nf_case=="new_mount_rear_tails_collision")intersection(){mr_new();nf_tails("all",.45);}
if(nf_case=="new_mount_mates_collision")intersection(){mr_new();nf_mates("all",.45);}
if(nf_case=="new_mount_strain_collision")intersection(){mr_new();nf_strain(.45);}
if(nf_case=="new_mount_own_PCB_seats_collision")intersection(){mr_new();mr_PCB_seat_interior();}
if(nf_case=="stripped_force_min_bore_collision")nc265_world()intersection(){nc265_force_gauges();nc265_pcb(true);}
if(nf_case=="strain_mount_min_bore_collision")nc265_world()intersection(){nc265_mount_gauges();nc265_pcb();}
if(nf_case=="strain_positive_control")intersection(){nc265_strain_world();nc265_world()translate([59,18.5,6])cube([.2,.2,.2]);}
if(nf_case=="new_mount_positive_control")intersection(){mr_new();translate([209.9,180.2,3])cube([.2,.2,.2]);}
if(nf_case=="FPC_U401_positive_control")intersection(){nf_components("FPC91");translate([26.4,179.8,21.4])cube([.2,.2,.2]);}
if(nf_case=="new_receiving_inlet_shadow")linear_extrude(.1)intersection(){projection()union(){fr_all_material();nc265_strain_receiving_world();mr_new();}ap_ports_2d();}
if(nf_case=="assembly_review"){mr_carrier();mr_lid();mr_keepers();mr_screws();rear_panel();thermal_metal_base();ap_everything_added();eb_feet_assembly();eb_foot_screws();eb_lower();ui_electronics(false,false);ua_all_controls();fr_power_environment();pf_wires();ui_all_joints();fr_PCB();nf_body();nc265_strain_world();}
