// TBH05 mechanical interface for NEW custom 20x18x1.6 AS5600 PCB.
// Not a purchased-board adaptation. Fixed board datum matches TBH01 reserve.
include <../two_board_print_03/retention_r5.scad>
module sensor_board(){translate([299.7,72,21.6])cube([1.6,20,18]);}
module sensor_package(){translate([301.3,78.8,28.4])cube([1.75,6.4,6.4]);}
module sensor_carrier(){difference(){union(){
 // Two feet share existing LEFT lever bolts; no new case holes.
 for(y=[69,102])hull(){translate([306,y,17.6])cylinder(d=7,h=2);translate([298.5,y,17.6])cylinder(d=3,h=2);}
 translate([297,69,17.6])cube([2.5,33,4]);
 // Edge rails grip only allocated component/copper-free 1mm PCB margins.
 for(y=[70,91])translate([297,y,19.6])cube([6,3,20]);
 translate([297,70,19.6])cube([6,24,2]);
 for(y=[70,91])translate([295.8,y,35.6])cube([3.7,3,4]);
 }for(y=[69,102])translate([306,y,17.5])cylinder(d=3.4,h=2.2);
 translate([299.5,72,21.6])cube([2,20,21]);
 // Top cap screws, tap M2 in pilots after printing.
 translate([298.2,69,38.3])rotate([-90,0,0])cylinder(d=1.6,h=5);
 translate([298.2,95,38.3])rotate([90,0,0])cylinder(d=1.6,h=5);
}}
module sensor_cap(){difference(){union(){translate([295.8,68,39.8])cube([7.2,28,1.2]);for(y=[68,94.2])translate([295.8,y,35.6])cube([4.8,1.8,5.4]);}
 for(y=[67.9,94.1])translate([298.2,y,38.3])rotate([-90,0,0])cylinder(d=2.3,h=2);}}
// Positive magnet escape barrier. Non-magnetic polymer, separate from rotor.
// Adhesive remains required for rotational coupling; this only limits escape.
module magnet_guard(){union(){
 translate([303.5,82,31.6])rotate([0,90,0])difference(){cylinder(d=10,h=.8);translate([0,0,-.1])cylinder(d=4,h=1);}
 for(y=[71.5,92.5])hull(){translate([301.8,y,37.5])cube([1.2,1,2]);translate([303.5, y<82?77.5:85.5,31.1])cube([.8,1,2]);}
}}
module carrier_complete(){union(){sensor_carrier();magnet_guard();}}
module sensor_wiring_envelope(){translate([293.7,76,23])cube([6,12,5]);translate([298.2,73.1,22.7])cube([1.5,17.8,15.8]);}
module board_keepouts(){union(){sensor_board();sensor_package();sensor_wiring_envelope();}}
module tbh05_installed(){installed();}
module installed(){carrier_complete();sensor_cap();board_keepouts();sensor_screws();cap_screws();}
module cap_screws(){translate([298.2,68,38.3])rotate([90,0,0])cylinder(d=3.8,h=2);translate([298.2,96,38.3])rotate([-90,0,0])cylinder(d=3.8,h=2);}
module magnet_escape(){translate([303.4,82,31.6])rotate([0,90,0])cylinder(d=6,h=2);}
module sensor_screws(){for(y=[69,102])translate([306,y,19.6]){cylinder(d=7,h=.5);translate([0,0,.5])cylinder(d=5.5,h=3);}}
if(part=="sensor_carrier")translate([-295.8,-65.5,-17.6])carrier_complete();
if(part=="sensor_cap")translate([0,0,7.2])rotate([0,90,0])translate([-295.8,-68,-35.6])sensor_cap();
if(part=="carrier_shell_clearance")intersection(){installed();shell();}
if(part=="carrier_components_clearance")intersection(){installed();box_rows(component_boxes);}
if(part=="carrier_controls_clearance")intersection(){installed();union(){translate([0,0,H])lid();guide_installed();holders_installed();}}
if(part=="carrier_lever_clearance")intersection(){installed();union(){translate([0,0,-.01])bracket_world();guard();axial_motion(.5);}}
if(part=="carrier_board_clearance")intersection(){union(){carrier_complete();sensor_cap();}translate([0,0,.01])board_keepouts();}
if(part=="magnet_retention_positive")intersection(){magnet_guard();magnet_escape();}
// Conservative diameter-4 spring corridor over all intermediate angles.
module spring_corridor(){for(a=[0:1:34])hull(){translate([316,70,35.6])sphere(d=4.02,$fn=24);for(t=[a,a+1])translate([316,82+10*sin(t),31.6+10*cos(t)])sphere(d=4.02,$fn=24);}}
if(part=="spring_controls_clearance")intersection(){spring_corridor();union(){translate([0,0,H])lid();guide_installed();holders_installed();}}
if(part=="spring_carrier_clearance")intersection(){spring_corridor();installed();}
if(part=="spring_components_clearance")intersection(){spring_corridor();box_rows(component_boxes);}
if(part=="spring_shell_clearance")intersection(){spring_corridor();shell();}
