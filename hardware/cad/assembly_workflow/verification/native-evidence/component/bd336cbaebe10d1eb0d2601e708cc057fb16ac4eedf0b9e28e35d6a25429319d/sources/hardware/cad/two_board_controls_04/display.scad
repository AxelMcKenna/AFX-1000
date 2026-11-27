// TBH04 BPM carrier: actual SA36-11YWA pin geometry; direct wired prototype.
// Absolute assembly datums. New lid and guide holes are explicit variants.
include <../two_board_print_01/captured.scad>
include <../a11/generated/button-fixture.scad>
use <../two_board_print_01/housing.scad>
$fn=48;
part="tray";
H=43.6; W=338; D=192.4;
mounts_display=[[160,19],[160,43]];
digits=[152,160,168];
module tbh04_nut(af,h){cylinder(d=af/cos(30),h=h,$fn=6);}
module tbh04_plate_shape(){union(){translate([147.3,22])square([25.4,18]);for(p=mounts_display)hull(){translate(p)circle(d=6);translate([p[0],p[1]<31?24:38])circle(d=6);}}}
module tbh04_tray(){difference(){union(){
 translate([0,0,31.8])linear_extrude(2)tbh04_plate_shape();
 // Side rails retain maximum-tolerance bodies but stop short of guide/lens.
 translate([147.3,23.6,33.8])cube([.6,14.8,8.8]);
 translate([172.1,23.6,33.8])cube([.6,14.8,8.8]);
 for(y=[22,38.4])translate([147.3,y,33.8])cube([25.4,1.6,8.8]);
 for(p=mounts_display)translate([p[0],p[1],31.8])cylinder(d=6,h=11);
 // Overlapping necks replace the pillar/wall tangent above the base.
 for(y=[20,38.4])translate([157,y,33.7])cube([6,3.6,9.1]);
 }
 for(p=mounts_display)translate([p[0],p[1],31.7]){cylinder(d=2.4,h=12);tbh04_nut(4.2,1.9);}
 // Each display has two columns at 5.08 mm, five rows at 2.54 mm.
 for(x=digits,dx=[-2.54,2.54],dy=[-5.08,-2.54,0,2.54,5.08])translate([x+dx,31+dy,31.7])cylinder(d=1.3,h=2.2);
}}
module tbh04_bezel(){difference(){translate([0,0,42.8])linear_extrude(.8)tbh04_plate_shape();translate([148.4,24.35,42.7])cube([23.2,13.3,1]);for(p=mounts_display)translate([p[0],p[1],42.7])cylinder(d=2.4,h=1);}}
module tbh04_body_max(){for(x=digits)translate([x-3.875,23.875,33.81])cube([7.75,14.25,8.75]);}
module tbh04_lead_max(){for(x=digits,dx=[-2.54,2.54],dy=[-5.08,-2.54,0,2.54,5.08])translate([x+dx,31+dy,29.3])cylinder(d=1.1,h=4.51);}
module tbh04_wire_reserve(){translate([147.5,23.5,26.5])cube([25,15,3]);}
module tbh04_fasteners(){for(p=mounts_display)translate([p[0],p[1],29.6]){cylinder(d=2,h=16);translate([0,0,16])cylinder(d=4.5,h=2.2);translate([0,0,2.3])tbh04_nut(4,1.6);}}
module tbh04_lid_variant(){difference(){lid();for(p=mounts_display)translate([p[0],p[1],-2])cylinder(d=2.4,h=5);}}
module tbh04_guide_variant(){difference(){guide_current();translate([0,0,-.1])linear_extrude(2)offset(delta=.2)tbh04_plate_shape();}}
module tbh04_obstacles(){box_rows(component_boxes);pcbs();shell();rear_plate();holders_installed();lid_bars_installed();board_heads();}
module tbh04_carrier(){tbh04_tray();tbh04_bezel();}
if(part=="tray")translate([-147.3,-16,-31.8])tbh04_tray();
if(part=="bezel")translate([-147.3,-16,-42.8])tbh04_bezel();
if(part=="lid")translate([0,D,2])rotate([180,0,0])tbh04_lid_variant();
if(part=="guide")translate([-10,-10,0])tbh04_guide_variant();
if(part=="body_clearance")intersection(){tbh04_carrier();tbh04_body_max();}
if(part=="lead_clearance")intersection(){tbh04_carrier();tbh04_lead_max();}
if(part=="obstacle_clearance")intersection(){tbh04_carrier();tbh04_obstacles();}
if(part=="component_wiring_clearance")intersection(){union(){tbh04_wire_reserve();tbh04_lead_max();tbh04_fasteners();}box_rows(component_boxes);}
if(part=="guide_clearance")intersection(){tbh04_carrier();translate([0,0,H-guide_thick])tbh04_guide_variant();}
if(part=="lid_clearance")intersection(){tbh04_carrier();translate([0,0,H+.01])tbh04_lid_variant();}
if(part=="fastener_clearance")intersection(){tbh04_carrier();tbh04_fasteners();}
if(part=="body_up_retention")intersection(){tbh04_bezel();translate([0,0,1.2])tbh04_body_max();}
if(part=="body_down_retention")intersection(){tbh04_tray();translate([0,0,-.5])tbh04_body_max();}
if(part=="assembly") {color("gray")tbh04_tray();color("green")tbh04_body_max();color("orange")tbh04_bezel();color("silver")tbh04_lead_max();}

module tbh04_display_installed(){tbh04_carrier();tbh04_body_max();tbh04_lead_max();}
