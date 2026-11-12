use <parts.scad>
use <../../two_board_controls_04/workflow_adapter/controls.scad>
module service_handle_nonseat(){
 difference(){service_handle();translate([313.99,79.99,55.59])cube([4.02,4.02,.02]);}
}
module service_local_lift(){
 // The entire fixed lever body is inside X300..335/Y65..110.
 // Other XY regions cannot intersect it during a pure vertical translation.
 minkowski(){
  intersection(){union(){controls_lid();controls_guide();}translate([300,65,40])cube([35,45,10]);}
  cylinder(r=.001,h=16,$fn=8);
 }
}
