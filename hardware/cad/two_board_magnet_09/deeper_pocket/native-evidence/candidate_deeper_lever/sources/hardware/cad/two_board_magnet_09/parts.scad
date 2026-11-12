// Nominal candidates; exact supplier tolerances and adhesive remain unqualified.
// Dimensions in mm, existing housing frame, rotor axis X at Y82/Z31.6.
$fn=64;
module magnet_nominal(){
 // Pocket floor X307.1 minus proposed 0.1 bond film; 2 mm magnet.
 translate([305,82,31.6])rotate([0,90,0])cylinder(d=6,h=2);
}
module magnet_receiving(){
 // Allocated diameter <=6.1, thickness <=2.1, film 0..0.2,
 // axial movement +/-0.5. Requirements, not supplier guarantees.
 translate([304.3,82,31.6])rotate([0,90,0])cylinder(d=6.1,h=3.3);
}
module grub_nominal(){
 // Proposed M3x3 flat-end envelope; thread/socket intentionally unresolved.
 // Tip tangent to nominal 3 mm shaft at Y83.5; recessed below hub surface.
 translate([320,83.5,31.6])rotate([-90,0,0])cylinder(d=3,h=3);
}
module grub_receiving(){
 // Conservative full rotation envelope, including +/-0.5 axial play.
 translate([318,82,31.6])rotate([0,90,0])cylinder(d=9.6,h=4);
}
