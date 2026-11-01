// A real Boolean with known1.5mm^3 volume, not a GUI or an empty placeholder.
intersection() {
    difference() {
        cube([2,1,1]);
        translate([1.5,0,0]) cube([1,1,1]);
    }
    cube([3,2,2]);
}
