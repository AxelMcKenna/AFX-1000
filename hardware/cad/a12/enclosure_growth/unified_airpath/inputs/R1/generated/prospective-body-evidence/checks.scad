include </Users/axelmckrnna/dev/rmx-publish/hardware/cad/a12/thermal/enlarged_base/generated/checks.scad>
module r1_candidate(m=0){translate([107.91-m,78.07-m,8.1-m])cube([4.18+2*m,7.86+2*m,1+2*m]);}
module r1_actual_obstacles(){ui_shell();tc2_posts();rear_panel();ui_lid();eb_metal();eb_lower();eb_interfaces();eb_foot_screws();ui_controls();eb_other_hardware();pf_wires(.25);ui_all_joints(.25);ui_components();for(b=ui_native_boards)ui_native_PCB(b);for(b=ui_other_boards)board_reserve(b);tc2_board();}
if(r1_case=="collision")intersection(){r1_candidate(.25);r1_actual_obstacles();}
if(r1_case=="positive")intersection(){r1_candidate();translate([109.9,81.9,8.5])cube([.2,.2,.2]);}
