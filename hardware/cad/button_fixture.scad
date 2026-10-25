// B01 button fit fixture. Dimensions in mm; this is a prototype, not a release.
// Panel underside is Z=0; a full housing would place this datum at Z=34.
include <generated/button-fixture.scad>

part="assembly"; // [assembly,section,pressed,key_pad,key_nudge,guide,clip,panel_pad,panel_nudge,collision]
sample="pad"; // [pad,nudge]
press=0; // [0:0.05:1.2]
guide_clearance=0.4; // total diametral clearance, fit must be measured
$fn=64;

module post_profile(d=stem_d,flat=stem_flat) {
    intersection() {
        circle(d=d);
        translate([-d,-d]) square([d+flat,2*d]);
    }
}

module key(w,h) {
    difference() {
        union() {
            translate([-w/2,-h/2,cap_under]) cube([w,h,cap_thick]);
            translate([0,0,stem_bottom]) linear_extrude(cap_under+0.2-stem_bottom) post_profile();
        }
        // A captive C clip bears against the groove's lower shoulder at rest.
        translate([0,0,clip_bottom]) linear_extrude(clip_thick+0.2)
            difference() { square([8,8],center=true); circle(d=groove_d); }
        // Punch the compliant contact from 2 mm soft silicone sheet. The blind
        // interference pocket retains it; no rigid plastic rests on the switch.
        translate([0,0,stem_bottom-0.01]) cylinder(d=puck_pocket_d,h=puck_insert+0.01);
    }
}

module clip() {
    difference() {
        translate([-4.5,-4.5,0]) cube([9,9,clip_thick]);
        translate([0,0,-0.1]) cylinder(d=groove_d+0.2,h=clip_thick+0.2);
        // A slightly narrower mouth snaps around the groove. Prototype fatigue
        // and removal force must be checked in the actual print material.
        translate([0,-(groove_d-0.2)/2,-0.1]) cube([5,groove_d-0.2,clip_thick+0.2]);
    }
}

module guide() {
    difference() {
        union() {
            translate([-15,-6,-guide_thick]) cube([30,12,guide_thick]);
            for(x=[-mount_pitch/2,mount_pitch/2])
                translate([x,0,-board_drop]) cylinder(d=6,h=board_drop);
        }
        translate([0,0,-guide_thick-0.1]) linear_extrude(guide_thick+0.2)
            post_profile(stem_d+guide_clearance,stem_flat+guide_clearance/2);
        for(x=[-mount_pitch/2,mount_pitch/2])
            translate([x,0,-board_drop-0.1]) cylinder(d=2.4,h=board_drop+0.2);
    }
}

module panel(w,h) {
    difference() {
        translate([-20,-12,0]) cube([40,24,panel_thick]);
        translate([-(w-1)/2,-(h-1)/2,-0.1]) cube([w-1,h-1,panel_thick+0.2]);
        for(x=[-mount_pitch/2,mount_pitch/2]) translate([x,0,-0.1]) cylinder(d=2.4,h=panel_thick+0.2);
    }
}

module switch_reference(displacement=0) {
    color([0.38,0.40,0.42]) translate([-3,-3,-board_drop]) cube([6,6,switch_case]);
    color([0.77,0.73,0.61]) translate([0,0,-board_drop+switch_case])
        cylinder(d=3.5,h=switch_height-switch_case-displacement);
}

module pcb_reference() {
    color([0.10,0.40,0.28]) difference() {
        translate([-16,-8,-board_drop-1.6]) cube([32,16,1.6]);
        for(x=[-mount_pitch/2,mount_pitch/2]) translate([x,0,-board_drop-1.7]) cylinder(d=2.4,h=1.8);
    }
}

module spring_reference(compressed_height) {
    // Envelope ONLY. Exact spring has not been selected or force-validated.
    // Closed-end bearing against switch metal cover is also a physical gate.
    color([0.65,0.69,0.73,0.5]) translate([0,0,-board_drop+switch_case])
        difference() {
            cylinder(d=spring_od,h=compressed_height);
            translate([0,0,-0.1]) cylinder(d=spring_id,h=compressed_height+0.2);
        }
}

module fixture(w,h,p=0) {
    assert(p>=0 && p<=travel);
    color([0.60,0.64,0.68]) panel(w,h);
    color([0.15,0.22,0.26]) guide();
    color([0.15,0.57,0.55]) translate([0,0,-p]) key(w,h);
    // The groove permits 0.2 axial clip play during depression; this pose is one
    // allowed position. The clearance sweep includes its whole lower extent.
    clip_depression=max(0,p-0.2); // return spring holds clip against upper groove face
    color([0.86,0.54,0.20]) translate([0,0,clip_bottom-clip_depression]) clip();
    pcb_reference();
    // Nominal geometric illustration, not a force/material simulation.
    displacement=min(switch_pt,max(0,p-nominal_gap));
    switch_reference(displacement);
    puck_top=stem_bottom+puck_insert-p;
    puck_bottom=max(stem_bottom+puck_insert-puck_height-p,-board_drop+switch_height-displacement);
    color([0.85,0.37,0.25]) translate([0,0,puck_bottom]) cylinder(d=puck_d,h=puck_top-puck_bottom);
    spring_reference(clip_bottom-clip_depression+board_drop-switch_case);
}

module section(w,h,p=0) {
    intersection() {
        fixture(w,h,p);
        translate([0,-25,-15]) cube([25,50,30]);
    }
}

module motion_collision(w,h) {
    // Continuous vertical sweep, separately per convex rigid primitive. Exclude
    // 0.01 mm at each intentional stop face; include cap/stem/clip lateral bounds.
    intersection() {
        union() {
            translate([-w/2,-h/2,cap_under-travel+0.01]) cube([w,h,cap_thick+travel-0.02]);
            translate([0,0,stem_bottom-travel+0.01]) linear_extrude(cap_under+0.2-stem_bottom+travel-0.02) post_profile();
            translate([-4.5,-4.5,clip_bottom-travel+0.01]) cube([9,9,clip_thick+travel-0.02]);
        }
        union() { guide(); panel(w,h); }
    }
}

w=sample=="nudge"?nudge_width:pad_width;
h=sample=="nudge"?nudge_depth:pad_depth;
if(part=="key_pad") translate([0,0,cap_under+cap_thick]) rotate([180,0,0]) key(pad_width,pad_depth);
else if(part=="key_nudge") translate([0,0,cap_under+cap_thick]) rotate([180,0,0]) key(nudge_width,nudge_depth);
else if(part=="guide") rotate([180,0,0]) guide();
else if(part=="clip") clip();
else if(part=="panel_pad") panel(pad_width,pad_depth);
else if(part=="panel_nudge") panel(nudge_width,nudge_depth);
else if(part=="collision") motion_collision(w,h);
else if(part=="section") section(w,h,press);
else if(part=="pressed") section(w,h,travel);
else fixture(w,h,press);
