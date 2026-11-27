use <../removable_handle/parts.scad>
use <../removable_handle/local.scad>
use <../../two_board_sensor_05/workflow_adapter/sensor.scad>
$fn=64;
module cap_handle_body_r2(){service_lever_body();}
module cap_handle_r2(){difference(){
 translate([308,78,53.6])cube([16,8,5.2]);
 translate([313.8,79.8,53.5])cube([4.4,4.4,2.1]);
 translate([316,82,55.59])cylinder(d=2.4,h=3.4);
 translate([316,82,56.3])cylinder(d1=2.4,d2=2.8,h=.2);
 translate([316,82,56.5])cylinder(d=4.2,h=2.4);
}}
// Nominal screw: sourced maximum head, nominal6mm under-head length.
// The small underhead cone is an explicit project receiving requirement.
module cap_handle_screw_r2(){translate([316,82,0])union(){
 translate([0,0,50.5])cylinder(d=2,h=6);
 translate([0,0,56.3])cylinder(d1=2,d2=2.6,h=.2);
 translate([0,0,56.5])cylinder(d=3.8,h=2);
}}
module cap_handle_withdrawal_r2(){minkowski(){cap_handle_r2();cylinder(r=.001,h=8,$fn=8);}}
module cap_handle_driver_r2(){translate([316,82,57.4])cylinder(d=2,h=1.41);translate([316,82,58.81])cylinder(d=10,h=50);}
module cap_handle_local_lift_r2(){service_local_lift();}
// Conservative new handle box with0.11mm padding, including <=0.0011mm
// arc/chord departure at1degree intervals, and inherited±0.5mm X play.
module cap_handle_motion_r2(){for(a=[0:34])hull()for(t=[a,a+1],dx=[-.5,.5])
 translate([316+dx,82,31.6])rotate([-t,0,0])translate([-8.11,-4.11,21.89])cube([16.22,8.22,5.42]);}
