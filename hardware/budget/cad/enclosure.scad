// B1 5V fit prototype. Generated geometry; dimensions still need purchased-part checks.
include <../generated/panel_geometry.scad>
$fn=64;
part="assembly"; // panel_left/right, tray_left/right, joiner, knob, button, lever, assembly
explode=12;
module outline(w=width,d=depth,r=corner_radius) {
    hull() for(x=[r,w-r],y=[r,d-r]) translate([x,y]) circle(r=r);
}
module panel() {
    linear_extrude(panel_thickness) difference() {
        outline(); panel_cutouts();
    }
}
module tray() {
    difference() {
        union() {
            difference() {
                linear_extrude(tray_height) outline();
                translate([wall,wall,wall]) linear_extrude(tray_height)
                    outline(width-2*wall,depth-2*wall,corner_radius-wall);
            }
            for(p=posts) translate([p[0],p[1],wall]) difference() {
                cylinder(h=tray_height-wall-1,r=4.5); cylinder(h=tray_height,r=1.25);
            }
            // Carrier mounting holes match the 100x100 PCB's four 4mm-inset holes.
            for(x=[198,290],y=[12,104]) translate([x,y,wall]) difference() {
                cylinder(h=3,r=3.4); cylinder(h=4,d=2.5);
            }
            // Slotted utility mounts for hand-wired control / Seed assemblies.
            for(x=[24,150,206,226],y=[48,112]) translate([x,y,wall]) difference() {
                cylinder(h=3,r=3.4); cylinder(h=4,d=2.5);
            }
        }
        rear_cutouts();
        for(x=[159,175],y=[20,137]) translate([x,y,-1]) cylinder(h=wall+2,d=3.4);
    }
}
module joiner() { // Four joiners: two under panel, two over the tray floor.
    linear_extrude(2) difference() {
        offset(r=2) square([22,8],center=true);
        for(x=[-8,8]) translate([x,0]) circle(d=3.4);
    }
}
module knob(d=18,bore=6.2) {
    difference() {
        cylinder(h=14,d=d);
        translate([0,0,-.1]) cylinder(h=11,d=bore);
        translate([-.5,d/2-5,13.4]) cube([1,5.5,1]);
        // M3 grub screw pilot; fit the shaft coupon before printing the full set.
        translate([0,-d/2-1,5]) rotate([-90,0,0]) cylinder(h=d/2,d=2.5);
    }
}
module button(w=8,h=8) { // Print face down; stem length is a fit parameter.
    translate([0,0,1]) cube([w-.4,h-.4,2],center=true);
    translate([0,0,2.5]) cube([w+1.2,h+1.2,1],center=true);
    translate([0,0,5]) cube([3.5,3.5,4],center=true);
}
module lever() { // Printed handle; separate shaft hub, return spring and stops are required.
    difference() {
        hull() {cylinder(h=6,d=12);translate([0,23,0]) cylinder(h=6,d=9);}
        translate([0,0,-1]) cylinder(h=8,d=6.2);
    }
}
module half(side=0) {
    intersection() {
        children();
        translate([side?167:-1,-1,-1]) cube([side?168:168,depth+2,100]);
    }
}
if(part=="panel_left") half(0) panel();
else if(part=="panel_right") translate([-167,0,0]) half(1) panel();
else if(part=="tray_left") half(0) tray();
else if(part=="tray_right") translate([-167,0,0]) half(1) tray();
else if(part=="joiner") joiner();
else if(part=="knob") knob();
else if(part=="button") button();
else if(part=="lever") lever();
else {
    color("#272c33") tray();
    translate([0,0,tray_height+explode]) color("#25292f") panel();
    translate([0,0,tray_height+panel_thickness+explode]) knob_envelopes();
    color([.1,.6,.5,.6]) translate([194,8,wall+3]) cube([100,100,1.6]);
    color([.9,.7,.1,.6]) translate([202,106,wall+3]) cube([25,46,13]);
}
