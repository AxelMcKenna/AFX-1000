use <../../two_board_sensor_05/workflow_adapter/sensor.scad>
use <../../two_board_controls_04/workflow_adapter/controls.scad>
$fn=64;
module service_lever_body(){
 difference(){
  union(){
   difference(){sensor_lever_nominal();translate([307.99,77.99,53.6])cube([16.02,8.02,4.1]);}
   // Restore original 4x4 stem through the new separate handle socket.
   translate([314,80,53.59])cube([4,4,2.01]);
  }
  // Tap M2 after printing;6mm pilot depth, nominal screw engagement4mm.
  translate([316,82,49.6])cylinder(d=1.6,h=6.1);
 }
}
module service_handle(){
 difference(){
  translate([308,78,53.6])cube([16,8,4]);
  // Socket roof seats on original stem top atZ55.6;0.2mm side allowance.
  translate([313.8,79.8,53.5])cube([4.4,4.4,2.1]);
  translate([316,82,55.59])cylinder(d=2.2,h=2.2);
  translate([316,82,56.6])cylinder(d1=2.2,d2=4.2,h=1.0);
 }
}
module service_handle_screw_receiving(){
 // Receiving envelope only: proposed M2x6 countersunk screw,4.2mm head.
 translate([316,82,51.6])cylinder(d=2,h=5);
 translate([316,82,56.6])cylinder(d1=2,d2=4.2,h=1);
}
module service_lid_guide_sweep(){
 // Conservative continuous vertical sweep0..16mm;0.001mm radial expansion.
 minkowski(){union(){controls_lid();controls_guide();}cylinder(r=.001,h=16,$fn=8);}
}
module service_handle_withdrawal(){
 // Sweep the removable handle vertically off the4x4 stem.
 minkowski(){service_handle();cylinder(r=.001,h=8,$fn=8);}
}
