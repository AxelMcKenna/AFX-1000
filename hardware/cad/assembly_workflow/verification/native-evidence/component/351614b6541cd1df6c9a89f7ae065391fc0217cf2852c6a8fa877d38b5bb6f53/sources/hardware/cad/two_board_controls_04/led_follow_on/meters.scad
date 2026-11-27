// TBH05 follow-on: two 20-emitter meter carriers. No sealed TBH04 changes.
include <../../two_board_print_01/captured.scad>
include <meter-board-data.scad>
use <../../a11/controls.scad>
include <../../a11/generated/button-fixture.scad>
use <../../two_board_print_01/housing.scad>
use <../selectors.scad>
use <button_motion.scad>
$fn=48;part="meter_frame";
module tbh05_meter_shape(sign=-1){polygon(tbh05_meter_outlines[sign<0?0:1]);}
module tbh05_meter_frame(sign=-1){difference(){union(){
 // Opaque cell walls give each emitter a separate path to its lens tooth.
 for(y=[-2,1.6])translate([42.4,y,40.9])cube([60,.4,1.7]);
 for(i=[0:20])translate([42.2+3*i,-2,40.9])cube([.4,4,1.7]);
 for(x=[43.9,100.9]){translate([x,sign*6.5,40.9])cylinder(d=5.6,h=2.7);translate([x-1.4,sign<0?-5:-2,40.9])cube([2.8,7,1.7]);}
 }
 for(x=[43.9,100.9])translate([x,sign*6.5,40.8])cylinder(d=2.4,h=3);
 // Preserve first/last emitter cavity through the mounting neck.
 for(x=[43.9,100.9])translate([x-1.2,-1.6,40.8])cube([2.4,3.2,2]);
}}
module tbh05_meters_frames(){for(i=[0:1])translate([0,21.25+i*14,0])tbh05_meter_frame(i==0?-1:1);}
module tbh05_meters_boards(){for(i=[0:1])translate([0,21.25+i*14,39.3])linear_extrude(1.6)difference(){tbh05_meter_shape(i==0?-1:1);for(x=[43.9,100.9])translate([x,i==0?-6.5:6.5])circle(d=2.4);}}
module tbh05_meters_emitters(){for(y=[21.25,35.25],i=[0:19])translate([43.9+3*i-.45,y-.85,40.9])cube([.9,1.7,.85]);}
module tbh05_meters_solder(){for(y=[21.25,35.25],i=[0:19],dy=[-.825,.825])translate([43.9+3*i-.45,y+dy-.45,40.9])cube([.9,.9,.15]);}
module tbh05_meters_wires(){for(y=[21.25,35.25]){for(i=[0:19])translate([43.9+3*i,y-2.4,36.8])cylinder(d=1.3,h=2.5);translate([72.4,y+2.45,36.8])cylinder(d=1.3,h=2.5);}}
module tbh05_meters_fasteners(guard=0){for(i=[0:1],x=[43.9,100.9])let(y=21.25+i*14+(i==0?-6.5:6.5))translate([x,y,35.6]){cylinder(d=2,h=10);translate([0,0,10])cylinder(d=4.5,h=2.2);translate([0,0,3.2])cylinder(d=4.5,h=.5-guard);translate([0,0,1.6])cylinder(d=4/cos(30),h=1.6,$fn=6);}}
module tbh05_meters_lid(){difference(){tbh04_selectors_lid();for(p=[[43.9,14.75],[100.9,14.75],[43.9,41.75],[100.9,41.75]])translate([p[0],p[1],-2])cylinder(d=2.4,h=5);}}
module tbh05_meters_guide(){difference(){tbh04_selectors_guide();for(i=[0:1])translate([0,21.25+i*14,-.1])linear_extrude(2)offset(delta=.2)tbh05_meter_shape(i==0?-1:1);}}
module tbh05_obstacles(){box_rows(component_boxes);pcbs();shell();rear_plate();holders_installed();lid_bars_installed();board_heads();}
if(part=="meter_frame")translate([-40.9,9.3,-40.9])tbh05_meter_frame(-1);
if(part=="meter_frame_lower")translate([-40.9,3.5,-40.9])tbh05_meter_frame(1);
if(part=="meter_obstacle_clearance")intersection(){union(){tbh05_meters_frames();tbh05_meters_boards();tbh05_meters_fasteners();tbh05_meters_wires();}tbh05_obstacles();}
if(part=="meter_emitter_clearance")intersection(){tbh05_meters_frames();union(){tbh05_meters_emitters();tbh05_meters_solder();}}
if(part=="meter_fastener_clearance")intersection(){union(){tbh05_meters_frames();tbh05_meters_boards();}tbh05_meters_fasteners(.01);}
if(part=="meter_lid_clearance")intersection(){union(){tbh05_meters_frames();tbh05_meters_emitters();}translate([0,0,43.61])tbh05_meters_lid();}
if(part=="meter_guide_clearance")intersection(){union(){tbh05_meters_frames();tbh05_meters_emitters();}translate([0,0,43.6-guide_thick])tbh05_meters_guide();}
if(part=="meter_board_up_retention")intersection(){tbh05_meters_frames();translate([0,0,.3])tbh05_meters_boards();}

module tbh05_meters_lenses(){for(y=[21.25,35.25])translate([43.9,y,42.8])meter_lens();}
if(part=="meter_lens_clearance")intersection(){tbh05_meters_frames();tbh05_meters_lenses();}
if(part=="meter_lens_down_retention")intersection(){tbh05_meters_frames();translate([0,0,-.3])tbh05_meters_lenses();union(){for(y=[21.25,35.25],x=[45,99])translate([x,y-1.9,42.51])cube([.3,.2,.08]);}}

if(part=="meter_button_motion_clearance")intersection(){union(){tbh05_meters_frames();tbh05_meters_boards();tbh05_meters_fasteners();tbh05_meters_wires();}tbh05_button_motion_native();}
