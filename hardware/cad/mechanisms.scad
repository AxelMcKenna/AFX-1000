// Standalone release mechanism and mechanical test coupon. Millimetres.
// Design dimensions, not measured stock parts. 3 mm pivot + diametric magnet.

module lever_bracket() {
    difference() {
        union() {
            translate([303,66,7]) cube([26,39,3]);
            for (x=[305,324]) translate([x,74,10]) cube([3,16,18]);
            // Lower hub tab sweeps through a cut pocket with physical end stops.
            difference() {
                translate([311,69,10]) cube([10,25,13]);
                translate([310,82,24]) rotate([0,90,0]) cylinder(h=12,d=10.4,$fn=48);
                for(a=[-0.75:0.5:35.75]) translate([316,82,24]) rotate([-a,0,0])
                    translate([-2.3,-1.8,-10.3]) cube([4.6,3.6,7.6]);
            }
            // Rear extension-spring anchor; eye is cross-drilled along X.
            translate([313,68,10]) cube([6,4,20]);
        }
        for (x=[306,326],y=[69,102]) translate([x,y,6]) cylinder(h=5,d=3.4,$fn=32);
        translate([304,82,24]) rotate([0,90,0]) cylinder(h=5,d=8.3,$fn=48);
        translate([323,82,24]) rotate([0,90,0]) cylinder(h=6,d=3.2,$fn=48);
        translate([312,70,28]) rotate([0,90,0]) cylinder(h=8,d=2.2,$fn=32);
    }
}

module lever_arm(angle=0) {
    // Pull toward front (+Y); 0..35 degrees. Sensor magnet is on the left end.
    translate([316,82,24]) rotate([-angle,0,0]) {
        difference() {
            union() {
                rotate([0,90,0]) cylinder(h=14,d=10,center=true,$fn=48);
                translate([-11,0,0]) rotate([0,90,0]) cylinder(h=4,d=8,$fn=48);
                translate([-2,-2,0]) cube([4,4,22]);
                translate([-8,-4,20]) cube([16,8,4]);
                translate([-2,-1.5,-10]) cube([4,3,7]);
                translate([-3,-2,8]) cube([6,4,4]);
            }
            translate([-1,0,0]) rotate([0,90,0]) cylinder(h=10,d=3.2,$fn=48);
            // Tap M3 after printing for a radial grub screw clamping the pivot.
            translate([4,6,0]) rotate([90,0,0]) cylinder(h=7,d=2.5,$fn=32);
            // Captive diametric magnet socket. Retention/adhesive tested on coupon.
            translate([-11.1,0,0]) rotate([0,90,0]) cylinder(h=2.2,d=6.2,$fn=48);
            translate([-4,0,10]) rotate([0,90,0]) cylinder(h=8,d=2.2,$fn=32);
        }
    }
}

module lever_occupied_piece(index,angle) {
    // Filled, expanded versions of the rotor's convex primitives. Filling blind
    // bores is conservative. Each external surface gets >=0.1 mm extra reserve.
    translate([316,82,24]) rotate([-angle,0,0]) {
        if(index==0) rotate([0,90,0]) cylinder(h=14.2,d=10.2,center=true,$fn=48);
        else if(index==1) translate([-11.1,0,0]) rotate([0,90,0]) cylinder(h=4.2,d=8.2,$fn=48);
        else if(index==2) translate([-2.1,-2.1,-0.1]) cube([4.2,4.2,22.2]);
        else if(index==3) translate([-8.1,-4.1,19.9]) cube([16.2,8.2,4.2]);
        else if(index==4) translate([-2.1,-1.6,-10.1]) cube([4.2,3.2,7.2]);
        else translate([-3.1,-2.1,7.9]) cube([6.2,4.2,4.2]);
    }
}

module lever_sweep() {
    // Hull adjacent poses separately per convex primitive. At 1-degree intervals,
    // maximum chord error at R25 is <0.001 mm, below the 0.1 mm expansion above.
    // This covers the whole motion, rather than testing just isolated positions.
    for(index=[0:5],a=[0:1:34]) hull() {
        lever_occupied_piece(index,a);
        lever_occupied_piece(index,a+1);
    }
}

module fit_coupon() {
    // 90 x 60 mm: pot mounting, a button, strip lens, and pivot bore samples.
    // Print flat; trial coupons precede the full enclosure and mechanism.
    difference() {
        cube([90,60,2]);
        translate([16,16,-1]) cylinder(h=4,d=9.3,$fn=64);
        translate([39,12,-1]) cube([14,7,4]);
        translate([10,35,-1]) cube([67,17,4]);
        for(i=[0:3]) translate([63+6*i,16,-1])
            cylinder(h=4,d=3.0+0.1*i,$fn=48);
    }
}

module strip_backer() {
    // Supports a 0.8 mm nonconductive cover + eight foil electrodes; no metal lid
    // material between the electrodes and the performer's fingers.
    difference() {
        translate([72,122,31.8]) cube([72,24,2.2]);
        translate([74.5,125.5,33]) cube([67,17,2]);
        for(x=[75,141],y=[124,144]) translate([x,y,31]) cylinder(h=4,d=2.2,$fn=32);
    }
}
