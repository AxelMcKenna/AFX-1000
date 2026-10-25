// All dimensions mm. Control coordinates originate at the front-left corner,
// looking down on the unit. A0 is a fit prototype, not a measured OEM chassis.
include <../generated/panel_geometry.scad>
$fn=64;
part="assembly"; // assembly, panel, tray, or panel_dxf
explode=12;
module outline(w=width,d=depth,r=corner_radius) {
    hull() for(x=[r,w-r],y=[r,d-r]) translate([x,y]) circle(r=r);
}
module panel() {
    linear_extrude(panel_thickness) difference() { outline(); panel_cutouts(); }
}
module tray() {
    difference() {
        linear_extrude(tray_height) outline();
        translate([wall,wall,wall]) linear_extrude(tray_height)
            outline(width-2*wall,depth-2*wall,corner_radius-wall);
        rear_cutouts();
    }
    for(p=posts) translate([p[0],p[1],wall]) difference() {
        cylinder(h=tray_height-wall-1,r=4.5);
        // Pilot for M3 self-tap. Replace with a measured heat-set insert pocket.
        cylinder(h=tray_height,r=1.25);
    }
}
if(part=="panel") panel();
else if(part=="tray") tray();
else if(part=="panel_dxf") difference() { outline(); panel_cutouts(); }
else {
    color("#272c33") tray();
    translate([0,0,tray_height+explode]) color("#25292f") panel();
    // Generic knob envelopes, to assess hand clearance and total height.
    translate([0,0,tray_height+panel_thickness+explode]) knob_envelopes();
}
