use <../r16_ground_support/support.scad>
use <../../two_board_controls_04/selectors.scad>
include <curve.scad>
$fn=64;
module rs_path(points,r){for(i=[0:len(points)-2])hull(){translate(points[i])sphere(r=r);translate(points[i+1])sphere(r=r);}}
module release_wire_guide(){difference(){union(){
 translate([316,63.5,36.5])cylinder(d=6,h=1.6);
 hull(){translate([317.5,62,36.5])cube([2,3,1.3]);translate([322,62,36.5])cube([2,3,1.3]);}
 translate([322,53,30.7])cube([2,12,7.1]);
 hull(){translate([317,53,30.7])cube([2,3,1]);translate([322,53,30.7])cube([2,3,1]);}
 rs_path(release_guide_outer_points,1.7);
 }translate([316,63.5,36.4])cylinder(d=2.4,h=1.8);rs_path(release_guide_bore_points,.85);}}
module rs_rear_m2x12(){translate([316,63.5,0]){
 translate([0,0,33.6])cylinder(d=2,h=12);translate([0,0,45.6])cylinder(d=4.5,h=2.2);
 translate([0,0,36])difference(){cylinder(d=4.5,h=.5);translate([0,0,-.1])cylinder(d=2.4,h=.7);}
 translate([0,0,34.4])difference(){gs_nut();translate([0,0,-.1])cylinder(d=1.6,h=1.8);}
}}
module release_supported_selectors(){difference(){ground_supported_selectors();translate([313,60.5,33.5])cube([6,6,15]);}
 // Restore only PCB and bracket material removed by the hardware replacement box.
 intersection(){union(){tbh04_selector_pcbs();tbh04_selector_brackets();}translate([313,60.5,33.5])cube([6,6,15]);}
 rs_rear_m2x12();}
module rs_seat_masks(){translate([316,63.5,38.09])cylinder(r=3.1,h=.02);translate([316,63.5,36.49])cylinder(r=2.35,h=.02);}
