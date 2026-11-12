// Eight physically populated RGB locations; coordinates use the housing datum.
include <../../two_board_print_01/captured.scad>
include <board-data.scad>
include <../../a11/generated/button-fixture.scad>
use <../../two_board_print_01/housing.scad>
use <../../a11/controls.scad>
use <../led_follow_on/banks.scad>
use <../led_follow_on/button_motion.scad>
$fn=96;part="ring_frame";
module tbh06_pose(){translate([244,78,0])children();}
module tbh06_mounts(){for(a=[22.5,157.5,286])rotate([0,0,a])translate([28.5,0,0])children();}
module tbh06_frame(){difference(){union(){translate([0,0,40.9])linear_extrude(1.6)difference(){circle(r=21.5);circle(r=20.5);}tbh06_mounts()translate([0,0,40.9])cylinder(d=5.6,h=2.7);for(a=[22.5,157.5,286])rotate([0,0,a])translate([20.8,-1.2,40.9])cube([7.7,2.4,1.6]);}tbh06_mounts()translate([0,0,40.8])cylinder(d=2.4,h=3);}}
module tbh06_board(){translate([0,0,39.3])linear_extrude(1.6)difference(){polygon(tbh06_outline);circle(r=17.8);tbh06_mounts()circle(d=2.4);}}
module tbh06_emitters(){for(a=[0:45:315])rotate([0,0,a])translate([23,-1,40.9])cube([2,2,.9]);}
module tbh06_resistors(){for(a=[0:45:315],p=[[22.5,3],[22.5,-3],[25.5,-5.5]])rotate([0,0,a])translate([p[0]-.45,p[1]-.85,40.9])cube([.9,1.7,.55]);}
module tbh06_solder(){for(a=[0:45:315])rotate([0,0,a]){for(x=[-.875,.875],y=[-.5,.5])translate([24+x-.475,y-.3,40.9])cube([.95,.6,.15]);for(p=[[22.5,3],[22.5,-3],[25.5,-5.5]],dy=[-.825,.825])translate([p[0]-.525,p[1]+dy-.45,40.9])cube([1.05,.9,.15]);}}
module tbh06_wires(){for(p=[[26.5,10],[19,15],[20,27],[21,19]])rotate([0,0,p[1]])translate([p[0],0,36.8])cylinder(d=1.1,h=2.5);}
module tbh06_fasteners(guard=0){tbh06_mounts()translate([0,0,35.6]){cylinder(d=2,h=12);translate([0,0,12+guard])cylinder(d=4.5,h=2.2-guard);translate([0,0,3.2])cylinder(d=4.5,h=.5-guard);translate([0,0,1.6])cylinder(d=4/cos(30),h=1.6,$fn=6);}}
module tbh06_lens(){difference(){union(){translate([0,0,45.6])ring_lens();tbh06_mounts()translate([0,0,45.6])cylinder(d=5.6,h=2);for(a=[22.5,157.5,286])rotate([0,0,a])translate([25,-1.4,45.6])cube([3.5,2.8,2]);}tbh06_mounts()translate([0,0,45.5])cylinder(d=2.4,h=2.2);}}
module tbh06_ring_installed(){tbh06_pose(){tbh06_frame();tbh06_board();tbh06_emitters();tbh06_resistors();tbh06_wires();tbh06_fasteners();tbh06_lens();}}
module tbh06_lid_variant(){difference(){union(){tbh05_bank_meter_lid();tbh06_pose()linear_extrude(2)difference(){circle(r=29);circle(r=19);}}tbh06_pose(){tbh06_mounts()translate([0,0,-2])cylinder(d=2.4,h=5);for(a=[0:45:315])rotate([0,0,a])translate([24,0,-2])cylinder(d=3,h=5);}}}
module tbh06_guide_variant(){difference(){tbh05_bank_meter_guide();tbh06_pose()translate([0,0,-.1])linear_extrude(2)difference(){offset(delta=.2)polygon(tbh06_outline);circle(r=17.6);}}}
module tbh06_obstacles(){box_rows(component_boxes);pcbs();shell();rear_plate();holders_installed();lid_bars_installed();board_heads();}
if(part=="ring_frame")translate([31.3,31.3,-40.9])tbh06_frame();
if(part=="ring_lens")translate([31.3,31.3,-42])tbh06_lens();
if(part=="ring_obstacle_clearance")intersection(){tbh06_pose(){tbh06_frame();tbh06_board();tbh06_fasteners();tbh06_wires();}tbh06_obstacles();}
if(part=="ring_button_clearance")intersection(){tbh06_ring_installed();tbh05_button_motion_native();}
if(part=="ring_component_clearance")intersection(){tbh06_frame();union(){tbh06_emitters();tbh06_resistors();tbh06_solder();}}
if(part=="ring_fastener_clearance")intersection(){union(){tbh06_frame();tbh06_board();tbh06_lens();}tbh06_fasteners(.01);}
if(part=="ring_lid_clearance")intersection(){tbh06_pose(){tbh06_frame();tbh06_lens();tbh06_emitters();}intersection(){translate([0,0,43.6])tbh06_lid_variant();translate([0,0,43.61])cube([338,192.4,1.98]);}}
if(part=="ring_guide_clearance")intersection(){tbh06_pose(){tbh06_frame();tbh06_lens();tbh06_emitters();}translate([0,0,42.2])tbh06_guide_variant();}
if(part=="ring_lens_emitter_clearance")intersection(){tbh06_lens();tbh06_emitters();}
if(part=="ring_board_retention")intersection(){tbh06_frame();translate([0,0,.3])tbh06_board();tbh06_mounts()translate([1.6,-.25,40.95])cube([.5,.5,.15]);}
if(part=="ring_lens_retention")intersection(){tbh06_fasteners();translate([0,0,.3])tbh06_lens();}

module tbh06_lid_change_mask(){tbh06_pose(){for(a=[0:45:315])rotate([0,0,a])translate([24,0,-2])cylinder(d=10,h=5);tbh06_mounts()translate([0,0,-2])cylinder(d=2.6,h=5);}}
module tbh06_guide_change_mask(){tbh06_pose()translate([0,0,-.2])linear_extrude(2)difference(){offset(delta=.21)polygon(tbh06_outline);circle(r=17.59);}}
if(part=="ring_lid_preservation")difference(){union(){difference(){tbh06_lid_variant();tbh05_bank_meter_lid();}difference(){tbh05_bank_meter_lid();tbh06_lid_variant();}}tbh06_lid_change_mask();}
if(part=="ring_guide_preservation")difference(){union(){difference(){tbh06_guide_variant();tbh05_bank_meter_guide();}difference(){tbh05_bank_meter_guide();tbh06_guide_variant();}}tbh06_guide_change_mask();}
if(part=="ring_lid_restored_material")intersection(){tbh06_lid_variant();tbh06_pose()for(a=[0:45:315])rotate([0,0,a])translate([24,0,.2])linear_extrude(1.6)difference(){circle(r=4.6);circle(r=1.51);}}
module tbh06_split_lid(left=true){difference(){union(){tbh05_bank_meter_split_lid(left);if(!left)tbh06_pose()linear_extrude(2)difference(){circle(r=29);circle(r=19);}}tbh06_pose(){tbh06_mounts()translate([0,0,-2])cylinder(d=2.4,h=5);for(a=[0:45:315])rotate([0,0,a])translate([24,0,-2])cylinder(d=3,h=5);}}}
if(part=="ring_lid")translate([0,192.4,2])rotate([180,0,0])tbh06_lid_variant();
if(part=="ring_guide")translate([-10,-10,0])tbh06_guide_variant();
if(part=="ring_lid_left")translate([0,192.4,2])rotate([180,0,0])tbh06_split_lid(true);
if(part=="ring_lid_right")translate([-169.1,192.4,2])rotate([180,0,0])tbh06_split_lid(false);
if(part=="ring_guide_left")translate([-10,-10,0])intersection(){tbh06_guide_variant();cube([168.9,192.4,2]);}
if(part=="ring_guide_right")translate([-169.1,-10,0])intersection(){tbh06_guide_variant();translate([169.1,0,0])cube([338,192.4,2]);}
