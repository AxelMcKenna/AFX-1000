// Four explicit bank-emitter boards and removable carriers; TBH04 unchanged.
include <../../two_board_print_01/captured.scad>
include <../../a11/generated/button-fixture.scad>
include <bank-board-data.scad>
use <../../two_board_print_01/housing.scad>
use <../../a11/controls.scad>
use <meters.scad>
use <button_motion.scad>
use <../selectors.scad>
$fn=48;part="bank_frame";
module tbh05_bank_frame(){difference(){union(){hull(){for(y=[-6,-1])translate([-6,y,41.2])cylinder(d=5.6,h=2.4);}translate([-6,-1.4,41.2])cube([5,2.8,1.4]);translate([-1.4,-1.8,41.2])cube([2.8,3.6,1.4]);}translate([-1,-1.4,41.1])cube([2,2.8,1.6]);for(y=[-6,-1])translate([-6,y,41.1])cylinder(d=2.4,h=2.6);}}
module tbh05_banks_frames(){for(x=[82,101,120,139])translate([x,103,0])tbh05_bank_frame();}
module tbh05_banks_boards(){for(x=[82,101,120,139])translate([x,103,39.6])linear_extrude(1.6)difference(){polygon(tbh05_bank_outline);for(y=[-6,-1])translate([-6,y])circle(d=2.4);}}
module tbh05_banks_emitters(){for(x=[82,101,120,139])translate([x-.45,102.15,41.2])cube([.9,1.7,.85]);}
module tbh05_banks_solder(){for(x=[82,101,120,139],dy=[-.825,.825])translate([x-.45,103+dy-.45,41.2])cube([.9,.9,.15]);}
module tbh05_banks_wires(){for(x=[82,101,120,139],dy=[-.85,.85])translate([x-2.5,103+dy,37.1])cylinder(d=1.1,h=2.5);}
module tbh05_banks_fasteners(guard=0){for(x=[82,101,120,139],dy=[-6,-1])translate([x-6,103+dy,35.6]){cylinder(d=2,h=10);translate([0,0,10])cylinder(d=4.5,h=2.2);translate([0,0,3.5])cylinder(d=4.5,h=.5-guard);translate([0,0,1.9])cylinder(d=4/cos(30),h=1.6,$fn=6);}}
module tbh05_banks_lenses(){for(x=[82,101,120,139])translate([x,103,42.8])bank_lens();}
module tbh05_banks_lid(){difference(){tbh05_meters_lid();for(x=[82,101,120,139],dy=[-6,-1])translate([x-6,103+dy,-2])cylinder(d=2.4,h=5);}}
module tbh05_banks_guide(){difference(){tbh05_meters_guide();for(x=[82,101,120,139])translate([x,103,-.1])linear_extrude(2)offset(delta=.2)polygon(tbh05_bank_outline);}}
module tbh05_banks_obstacles(){box_rows(component_boxes);pcbs();shell();rear_plate();holders_installed();lid_bars_installed();board_heads();}

if(part=="bank_frame")translate([8.8,8.8,-41.2])tbh05_bank_frame();
if(part=="bank_obstacle_clearance")intersection(){union(){tbh05_banks_frames();tbh05_banks_boards();tbh05_banks_wires();tbh05_banks_fasteners();}tbh05_banks_obstacles();}
if(part=="bank_button_motion_clearance")intersection(){union(){tbh05_banks_frames();tbh05_banks_boards();tbh05_banks_wires();tbh05_banks_fasteners();}tbh05_button_motion_native();}
if(part=="bank_emitter_clearance")intersection(){tbh05_banks_frames();union(){tbh05_banks_emitters();tbh05_banks_solder();}}
if(part=="bank_fastener_clearance")intersection(){union(){tbh05_banks_frames();tbh05_banks_boards();}tbh05_banks_fasteners(.01);}
if(part=="bank_lid_clearance")intersection(){union(){tbh05_banks_frames();tbh05_banks_emitters();}translate([0,0,43.61])tbh05_banks_lid();}
if(part=="bank_guide_clearance")intersection(){union(){tbh05_banks_frames();tbh05_banks_emitters();}translate([0,0,43.6-guide_thick])tbh05_banks_guide();}
if(part=="bank_lens_clearance")intersection(){tbh05_banks_frames();tbh05_banks_lenses();}
if(part=="bank_board_up_retention")intersection(){tbh05_banks_frames();translate([0,0,.3])tbh05_banks_boards();}
if(part=="bank_lens_down_retention")intersection(){tbh05_banks_frames();translate([0,0,-.3])tbh05_banks_lenses();}

module tbh05_bank_meter_installed(){tbh05_meters_frames();tbh05_meters_boards();tbh05_meters_emitters();tbh05_meters_wires();tbh05_meters_fasteners();tbh05_banks_frames();tbh05_banks_boards();tbh05_banks_emitters();tbh05_banks_wires();tbh05_banks_fasteners();}
module tbh05_bank_meter_lid(){tbh05_banks_lid();}
module tbh05_bank_meter_guide(){tbh05_banks_guide();}
module tbh05_bank_meter_split_lid(left=true){difference(){tbh04_selectors_split_lid(left);for(p=[[43.9,14.75],[100.9,14.75],[43.9,41.75],[100.9,41.75]])translate([p[0],p[1],-2])cylinder(d=2.4,h=5);for(x=[82,101,120,139],dy=[-6,-1])translate([x-6,103+dy,-2])cylinder(d=2.4,h=5);}}
if(part=="led_lid")translate([0,192.4,2])rotate([180,0,0])tbh05_banks_lid();
if(part=="led_guide")translate([-10,-10,0])tbh05_banks_guide();
if(part=="led_lid_left")translate([0,192.4,2])rotate([180,0,0])tbh05_bank_meter_split_lid(true);
if(part=="led_lid_right")translate([-169.1,192.4,2])rotate([180,0,0])tbh05_bank_meter_split_lid(false);
if(part=="led_guide_left")translate([-10,-10,0])intersection(){tbh05_banks_guide();cube([168.9,192.4,2]);}
if(part=="led_guide_right")translate([-169.1,-10,0])intersection(){tbh05_banks_guide();translate([169.1,0,0])cube([338,192.4,2]);}
