use <support.scad>
// Positive footprint slice immediately above the seating plane. Raw coplanar
// Boolean output is not guaranteed to contain the whole contact face.
linear_extrude(.1)projection(cut=true)translate([0,0,-9.501])touch_cradle();
