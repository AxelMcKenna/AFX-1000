include </Users/axelmckrnna/dev/rmx-publish/hardware/cad/a12/harness/generated/receiver-ear/checks.scad>
access_outline=[[0.0, 0.0], [150.0, 0.0], [150.0, 48.0], [164.0, 48.0], [164.0, 65.0], [0.0, 65.0]];
access_J13=[[188.0, 100.0, 8.1], [188.0, 104.0, 8.1]];

module ax_post(m=0){difference(){translate([182,92.2,2.7-m])cylinder(d=7.2+2*m,h=3.8+2*m,$fn=128);translate([182,92.2,3.2])cylinder(d=3.2,h=3.31+m,$fn=128);}}
module ax_head(m=0){translate([182,92.2,8.1-m])cylinder(d=5.6+2*m,h=2.31+2*m,$fn=128);}
module ax_shaft(){translate([182,92.2,4.1])cylinder(d=2.05,h=4,$fn=128);}
module ax_tool(old=false){translate([182,old?97.2:92.2,8.1])cylinder(d=6.5,h=52,$fn=128);}
module ax_ear(){difference(){translate([30,42,6.5])linear_extrude(1.6)polygon(access_outline);translate([29,41,6.49])cube([151,67,1.62]);for(p=access_J13)translate([p[0],p[1],6.49])cylinder(d=2.2,h=1.62,$fn=128);translate([182,92.2,6.49])cylinder(d=2.4,h=1.62,$fn=128);}}
module ax_ear_reserve(){translate([179.55,89.55,6.05])cube([14.9,17.9,2.5]);}
module ax_seats(){guarded_inherited_support();translate([182,92.2,2.79998])cylinder(d=7.20004,h=3.70004,$fn=128);}
module ax_nonseating_ear(){difference(){ax_ear_reserve();ax_seats();}}
module ax_open_case(){retained_thermal_shell();thermal_metal_base();lower_shell_fasteners();ax_post();}
module ax_dual_component_reserves(){electronics();translate([0,0,7.6])electronics();}
module ax_relative_board(){translate([30,42,6.3])difference(){linear_extrude(2.16)polygon(access_outline);translate([152,50.2,-.01])cylinder(d=2.3,h=2.18,$fn=128);}}
if(trial=="access_geometry"){ax_ear();ax_post();ax_head();ax_shaft();joint();}
if(trial=="access_tool_geometry")ax_tool();
if(trial=="access_ear_material")ax_ear();
if(trial=="access_nominal_ear_case_collision")intersection(){translate([0,0,.00002])ax_ear();ax_open_case();}
if(trial=="access_ear_case_collision")intersection(){ax_nonseating_ear();ax_open_case();}
if(trial=="access_ear_hardware_collision")intersection(){union(){ax_ear_reserve();joint(.45);}hardware();}
if(trial=="access_ear_electronics_collision")intersection(){union(){ax_ear_reserve();joint(.45);}ax_dual_component_reserves();}
if(trial=="access_post_joint_collision")intersection(){union(){ax_post(.45);ax_head(.45);}joint();}
if(trial=="access_post_electronics_collision")intersection(){union(){ax_post(.45);ax_head(.45);}ax_dual_component_reserves();}
if(trial=="access_post_hardware_collision")intersection(){union(){ax_post(.45);ax_head(.45);}hardware();}
if(trial=="access_tool_hardware_collision")intersection(){ax_tool();hardware();}
if(trial=="access_tool_electronics_collision")intersection(){ax_tool();ax_dual_component_reserves();}
if(trial=="access_tool_open_case_collision")intersection(){ax_tool();ax_open_case();}
if(trial=="access_shaft_bore_collision")intersection(){translate([182,92.2,4.1])cylinder(d=2.26,h=7,$fn=128);ax_relative_board();}
if(trial=="access_floor_bond")intersection(){ax_post();retained_thermal_shell();}
if(trial=="access_old_axis_blocked_witness")intersection(){ax_tool(true);hardware();}
if(trial=="access_post_positive_control")intersection(){ax_post();translate([184.9,92.1,4])cube([.2,.2,.2]);}
if(trial=="access_ear_positive_control")intersection(){ax_ear();translate([189.9,91.9,7])cube([.2,.2,.2]);}
if(trial=="access_tool_positive_control")intersection(){ax_tool();translate([181.9,92.1,30])cube([.2,.2,.2]);}
