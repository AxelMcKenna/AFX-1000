include </Users/axelmckrnna/dev/rmx-publish/hardware/cad/a12/enclosure_growth/r1_local/captured/hardware/cad/a12/thermal/enlarged_base_pot/generated/context-derived.scad>
r1_row=["new_selected_R1", 107.91, 78.07, 8.1, 4.180000000000007, 7.860000000000014, 1.0];
r1_old_row=["e19_R1", 94.07, 83.17, 8.1, 3.86, 7.66, 1.21, "Header/harness<=11mm and XY courtyard+.5; SMD class height limit plus PCB/seat .31mm. Exact parts and physical fit unqualified"];

module r1_body(m=0,zsweep=0){translate([r1_row[1]-m,r1_row[2]-m,r1_row[3]-m-zsweep])cube([r1_row[4]+2*m,r1_row[5]+2*m,r1_row[6]+2*m+2*zsweep]);}
module r1_other_electronics(){for(b=ui_native_boards)ui_native_PCB(b);for(b=ui_other_boards)board_reserve(b);tc2_board();ui_components();}
module r1_margin(){r1_body(.25,.2);}
module r1_mounts_tools(){ui_h9_tool();tc2_tool();ui_h9_head();tc2_posts();tc2_heads();eb_lower();eb_foot_screws();}
if(r1_case=="receiving_geometry")r1_body();
if(r1_case=="external_electronics_collision")intersection(){r1_margin();r1_other_electronics();}
if(r1_case=="controls_collision")intersection(){r1_margin();union(){ui_controls();cp_pot_hardware();}}
if(r1_case=="case_base_interfaces_collision")intersection(){r1_margin();union(){eb_case_and_lid();eb_metal();eb_interfaces();eb_lower();eb_foot_screws();}}
if(r1_case=="power_collision")intersection(){r1_margin();ui_power_only();}
if(r1_case=="wire_joints_collision")intersection(){r1_margin();union(){pf_wires(.25);ui_all_joints(.25);}}
if(r1_case=="mount_tool_collision")intersection(){r1_margin();r1_mounts_tools();}
for(i=[0:2])if(r1_case==str("own_PCB_correlated_seat_",i))intersection(){translate([0,0,[-.2,0,.2][i]])r1_body();translate([0,0,[-.2,0,.2][i]])ui_receiver();}
if(r1_case=="new_R1_positive_control")intersection(){r1_body();translate([109.9,81.9,8.3])cube([.2,.2,.2]);}
if(r1_case=="retained_other_component_positive_control")intersection(){r1_other_electronics();translate([99.9,89.9,8.3])cube([.2,.2,.2]);}
if(r1_case=="old_R1_presence_positive_control")intersection(){ui_boxes([r1_old_row]);translate([95.9,86.9,8.3])cube([.2,.2,.2]);}
if(r1_case=="only_old_R1_exclusion_control")intersection(){r1_other_electronics();translate([95.9,86.9,8.3])cube([.2,.2,.2]);}
if(r1_case=="uncorrelated_seat_shift_positive_control")intersection(){translate([0,0,-.2])r1_body();ui_receiver();translate([109.9,81.9,7.9])cube([.2,.2,.2]);}
