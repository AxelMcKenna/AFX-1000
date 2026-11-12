use <right.scad>
part="outside";
module port_masks(){for(p=[[280.5,32,29.5],[305.5,31,29.5],[305.5,33,29.5]])translate(p)sphere(r=.62,$fn=64);}
module joint_contact(){intersection(){panel_ground_selector_wires();panel_ground_right_splice();}}
if(part=="outside")difference(){joint_contact();port_masks();}
if(part=="contact_positive")joint_contact();
