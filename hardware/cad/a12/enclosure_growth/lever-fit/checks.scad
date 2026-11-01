include </Users/axelmckrnna/dev/rmx-publish/hardware/cad/a12/thermal-integration.scad>
lever_sensor_reserves=[["angle_sensor_board", 299.7, 72, 21.6, 1.6, 20, 20, "custom AS5600 board reserve"], ["angle_sensor", 301.3, 79.5, 29.1, 1.7, 5, 5, "SOIC sensor placement reserve"]];

lever_case="geometry";
module lift_bracket(){translate([0,0,7.6])lever_bracket();}
module lift_sweep(){translate([0,0,7.6])lever_sweep();}
module lift_arm(){translate([0,0,7.6])lever_arm(35);}
module lift_panel(){translate([0,0,panel_z])front_panel();}
module lift_sensors(){for(b=lever_sensor_reserves)translate([b[1],b[2],b[3]])cube([b[4],b[5],b[6]]);}
if(lever_case=="geometry"){lift_bracket();lift_sweep();}
if(lever_case=="bracket_geometry")lift_bracket();
if(lever_case=="new_sweep_lid_collision")intersection(){lift_sweep();lift_panel();}
if(lever_case=="new_arm_lid_collision")intersection(){lift_arm();lift_panel();}
if(lever_case=="old_arm_new_lid_blocked_witness")intersection(){lever_arm(35);lift_panel();}
if(lever_case=="bracket_new_posts_collision")intersection(){translate([0,0,.00002])lift_bracket();retained_thermal_shell();}
if(lever_case=="new_sweep_sensor_collision")intersection(){lift_sweep();lift_sensors();}
if(lever_case=="new_bracket_sensor_collision")intersection(){lift_bracket();lift_sensors();}
if(lever_case=="bracket_positive_control")intersection(){lift_bracket();translate([309.9,69.9,15])cube([.2,.2,.2]);}
if(lever_case=="sweep_positive_control")intersection(){lift_sweep();translate([315.9,81.9,35])cube([.2,.2,.2]);}
