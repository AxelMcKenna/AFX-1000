include <../../../thermal-integration.scad>
module outer_controls(){
 for(k=knobs)translate([k[1],k[2],shell_height+2.8])knob(k[3],k[4]);
 for(b=buttons)button_pose(b)key_sweep(b);
 for(c=caps)if(c[1]=="switch")translate([c[2],c[3],panel_z])selector_cap();
 translate([0,0,shell_height-38])lever_sweep();
}
// Include the actual shell and rear panel to avoid confusing a controls-only
// bounding box with an assembled mechanical envelope. Internal material and
// lower base fins stay between these extrema; they are not a collision audit.
retained_thermal_shell();rear_panel();outer_controls();thermal_feet();
