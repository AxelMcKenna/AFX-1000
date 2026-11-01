include <generated/context-derived.scad>
// Same radial point is material below the actual nominal screw tip and a void
// inside its5.8mm engagement. This distinguishes the old10mm abstraction.
if(foot_witness=="below_tip_material")intersection(){eb_feet_assembly();translate([21.3,19.95,-14])cube([.1,.1,.2]);}
if(foot_witness=="engaged_region_void")intersection(){eb_feet_assembly();translate([21.3,19.95,-10])cube([.1,.1,.2]);}
