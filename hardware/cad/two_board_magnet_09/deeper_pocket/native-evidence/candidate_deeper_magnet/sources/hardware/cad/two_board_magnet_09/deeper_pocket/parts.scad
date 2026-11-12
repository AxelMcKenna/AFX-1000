use <../../two_board_sensor_05/workflow_adapter/sensor.scad>
use <../parts.scad>
$fn=64;
module magnet_deeper_nominal(){
 translate([305.2,82,31.6])rotate([0,90,0])cylinder(d=6,h=2);
}
module magnet_deeper_receiving(){
 // Floor307.3 - film0.2 - thickness2.1 - axialplay0.5 =304.5.
 translate([304.5,82,31.6])rotate([0,90,0])cylinder(d=6.1,h=3.3);
}
module lever_deeper_pocket(){
 difference(){
  sensor_lever_nominal();
  // Continue existing48facet pocket through floor by0.2mm only.
  translate([304.9,82,31.6])rotate([0,90,0])cylinder(d=6.2,h=2.4,$fn=48);
 }
}
