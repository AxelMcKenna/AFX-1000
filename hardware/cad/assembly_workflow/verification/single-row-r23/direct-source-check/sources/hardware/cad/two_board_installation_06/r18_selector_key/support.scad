// Positive antirotation fence, additive to frozen r17 guide.
use <../r17_selector_support/support.scad>
$fn=64;
module release_keyed_guide(){union(){release_wire_guide();
 // Rear fence crosses both sides of mounting axis X316. PCB rear edge is Y65.5.
 translate([309,65.7,36.5])cube([16.5,1.3,3.0]);
 // East fence; PCB edge is X324. Nominal side clearance is 0.2 mm.
 translate([324.2,60.5,36.5])cube([1.3,6.5,3.0]);
 // Join original stem to fences below PCB; top37.8 leaves0.3 mm gap.
 translate([309,64.7,36.5])cube([16.5,2.3,1.3]);
 translate([323,60.5,36.5])cube([2.5,6.5,1.3]);
}}
