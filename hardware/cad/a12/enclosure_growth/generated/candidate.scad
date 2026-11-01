include </Users/axelmckrnna/dev/rmx-publish/hardware/cad/a12/thermal-integration.scad>

// Reproduce with generate.py: explicit -D body_depth/shell_height/fasteners
// are part of every native command and are bound in verification.json.
growth_case="shell";
module growth_shell(){retained_thermal_shell();}
module growth_lid(){translate([0,0,panel_z])front_panel();}
module growth_outer_controls(){
 for(k=knobs)translate([k[1],k[2],shell_height+2.8])knob(k[3],k[4]);
 for(b=buttons)button_pose(b)key_sweep(b);
 for(c=caps)if(c[1]=="switch")translate([c[2],c[3],panel_z])selector_cap();
 translate([0,0,shell_height-38])lever_sweep();
}
if(growth_case=="shell")growth_shell();
if(growth_case=="lid")growth_lid();
if(growth_case=="outer_reference"){growth_shell();rear_panel();growth_outer_controls();thermal_feet();}
// Only the intended coplanar lid-seating interface is separated numerically.
if(growth_case=="lid_collision")intersection(){growth_shell();translate([0,0,.00002])growth_lid();}
if(growth_case=="front_floor_positive_control")intersection(){growth_shell();translate([166.9,174.9,1])cube([.2,.2,.2]);}
if(growth_case=="high_wall_positive_control")intersection(){growth_shell();translate([166.9,187,41.9])cube([.2,.2,.2]);}
if(growth_case=="front_boss_positive_control")intersection(){growth_shell();translate([10,180.3,10])cube([.2,.2,.2]);}
if(growth_case=="front_pilot_empty_control")intersection(){growth_shell();translate([7.9,180.3,10])cube([.2,.2,.2]);}
