// A11 printable controls. All dimensions are millimetres.
// Button datum Z=0 is the underside of the 2 mm lid (Z=34 in the housing).
function button_x(b) = b[5];
function button_y(b) = b[6];
module button_pose(b,z=panel_z) {
    translate([b[5],b[6],z]) rotate([0,0,b[7]]) children();
}
module post_profile(d=stem_d,flat=stem_flat) {
    intersection() { circle(d=d); translate([-d,-d]) square([d+flat,2*d]); }
}
module cap_profile(b) {
    if(b[1]=="sector") translate([-43.5,0]) sector(35,52,-b[4]/2,b[4]/2);
    else offset(r=0.7) square([b[2]-1.4,b[3]-1.4],center=true);
}
module cap_mark(b) {
    size=min(1.55,(b[1]=="sector"?13:b[2]-1.5)/(max(1,len(b[9]))*0.64));
    mirror([0,1,0]) text(b[9],size=size,font="Arial:style=Bold",halign="center",valign="center");
}
module key(b) {
    difference() {
        union() {
            translate([0,0,cap_under]) linear_extrude(cap_thick) cap_profile(b);
            translate([0,0,stem_bottom]) linear_extrude(cap_under+0.2-stem_bottom) post_profile();
        }
        translate([0,0,clip_bottom]) linear_extrude(clip_thick+0.2)
            difference() { square([8,8],center=true); circle(d=groove_d); }
        translate([0,0,stem_bottom-0.01]) cylinder(d=puck_pocket_d,h=puck_insert+0.01);
        translate([0,0,cap_under+cap_thick-0.3]) linear_extrude(0.4) cap_mark(b);
    }
}
module retaining_clip() {
    difference() {
        translate([-4.5,-4.5,0]) cube([9,9,clip_thick]);
        translate([0,0,-0.1]) cylinder(d=groove_d+0.2,h=clip_thick+0.2);
        translate([0,-(groove_d-0.2)/2,-0.1]) cube([5,groove_d-0.2,clip_thick+0.2]);
    }
}
module holder_footprint(b) {
    hull() {
        offset(r=0.6) square([7.6,7.6],center=true);
        for(p=b[8]) translate(p) circle(d=4.2);
    }
}
module switch_holder(b) {
    difference() {
        union() {
            translate([0,0,-board_drop-1.6]) linear_extrude(1.6) holder_footprint(b);
            for(p=b[8]) translate([p[0],p[1],-board_drop-1.6])
                cylinder(d=4.2,h=board_drop+1.6-guide_thick);
            // Pocket walls retain the switch case, leaving the centre cover free.
            translate([0,0,-board_drop]) linear_extrude(3.6) difference() {
                offset(r=0.4) square([7.6,7.6],center=true);
                square([6.4,6.4],center=true);
            }
            // Four small corner lips clear the circular return-spring bearing.
            for(x=[-1,1],y=[-1,1]) translate([x*3.15,y*3.15,-board_drop+3.4])
                cube([0.8,0.8,0.35],center=true);
        }
        for(p=b[8]) translate([p[0],p[1],-board_drop-0.3]) cylinder(d=1.6,h=10);
        // B3F-1000 lead pattern: 6.5 x 4.5. This is an insulating wire carrier,
        // not a PCB. Solder/wire the switch separately; printed plastic is not copper.
        for(x=[-3.25,3.25],y=[-2.25,2.25])
            translate([x,y,-board_drop-1.7]) cylinder(d=1.2,h=1.8);
        // Lead reliefs through the case-pocket walls (body width is 6 mm).
        for(x=[-4.5,2.8],y=[-2.25,2.25]) translate([x,y-0.75,-board_drop-0.01]) cube([1.7,1.5,1.6]);
    }
}
module mounting_holes(countersunk=false) {
    for(b=buttons) button_pose(b,0) for(p=b[8]) translate([p[0],p[1],-0.1]) {
        cylinder(d=2.4,h=2.2);
        if(countersunk) translate([0,0,0.9]) cylinder(d1=2.4,d2=4.6,h=1.2);
    }
    for(x=[73,143],y=[123,145]) translate([x,y,-0.1]) cylinder(d=2.4,h=2.2);
}
module guide_plate_2d() {
    difference() {
        // C24 maximum body plus 2mm vent air clears the guide, under the intact lid.
        translate([10,10]) rounded_rect(body_width-20,body_depth-20,4);
        for(p=fasteners) translate(p) circle(d=9.2);
        translate([disconnect_guide_relief[0],disconnect_guide_relief[1]]) circle(d=disconnect_guide_relief[2],$fn=96);
        for(b=buttons) button_pose(b,0) post_profile(stem_d+0.4,stem_flat+0.2);
        for(b=buttons) button_pose(b,0) for(p=b[8]) translate(p) circle(d=2.4);
        for(c=caps) if(c[1]=="knob") translate([c[2],c[3]]) square([16.8,16.8],center=true);
        for(c=openings) if(c[1]!="button" && c[1]!="sector" && c[1]!="knob") aperture(c);
        translate([146.5,22]) square([27,18]);
        translate([70-0.2,120-0.2]) square([76.4,28.4]);
        for(y=[21.25,35.25]) translate([42.5,y-2.2]) square([61,4.4]);
        for(x=[82,101,120,139]) translate([x,103]) circle(d=4.4);
        for(a=[0:45:315]) translate([244+24*cos(a),78+24*sin(a)]) circle(d=3.2);
        for(c=caps) if(c[1]=="switch") translate([c[2],c[3]]) square([c[4]+3,c[5]+3],center=true);
    }
}
module guide_plate() { linear_extrude(guide_thick) guide_plate_2d(); }
module front_panel() {
    difference() {
        linear_extrude(panel_thickness) panel_2d();
        mounting_holes(true);
    }
}
module knob(d,h,bore=6.2) {
    difference() {
        cylinder(d=d,h=h);
        for(a=[0:360/32:359]) rotate([0,0,a]) translate([d/2,0,0.8]) cylinder(d=0.8,h=h-1.6,$fn=12);
        translate([0,0,-0.1]) cylinder(d=bore,h=min(10,h-2)+0.1);
        translate([0,0,-0.1]) cylinder(d1=bore+0.8,d2=bore,h=0.7);
        translate([0,0,6]) rotate([0,90,0]) cylinder(d=2.5,h=d/2+1);
        translate([6,0,6]) rotate([0,90,0]) cylinder(d=4,h=d/2);
        translate([-0.45,-d/2+1,h-0.5]) cube([0.9,d*0.32,0.6]);
    }
}
module selector_cap() {
    difference() {
        union() {
            translate([-3.5,-2.5,2.2]) cube([7,5,3]);
            translate([-1.65,-1.65,0.1]) cube([3.3,3.3,2.3]);
        }
        translate([-0.85,-0.85,0]) cube([1.7,1.7,3.6]);
        for(x=[-2,0,2]) translate([x-0.25,-2.6,4.8]) cube([0.5,5.2,0.5]);
    }
}
module touch_backer() {
    translate([0,0,panel_z-34]) difference() {
        union() {
            translate([70,120,32.6]) cube([76,28,1.4]);
            translate([74.7,125.7,34]) cube([66.6,16.6,1.2]);
        }
        translate([75.5,126.5,32.5]) cube([65,15,3]);
        for(x=[73,143],y=[123,145]) translate([x,y,32.5]) cylinder(d=1.6,h=1.6);
    }
}
module touch_lens() { cube([66.4,16.4,0.8]); }
module ring_lens() {
    linear_extrude(0.8) difference() { circle(r=26); circle(r=22); }
    for(a=[0:45:315]) translate([24*cos(a),24*sin(a),-3.6]) cylinder(d=2.6,h=3.7);
}
module meter_lens() {
    translate([-1.3,-2,0]) cube([59.6,4,0.8]);
    for(i=[0:19]) translate([i*3-0.75,-1.1,0.7]) cube([1.5,2.2,2.1]);
}
module bank_lens() {
    cylinder(d=4,h=0.8);
    translate([0,0,0.7]) cylinder(d=1.9,h=2.1);
}
module display_lens() {
    translate([-12.8,-8.3,0.4]) cube([25.6,16.6,0.5]);
    translate([-11.8,-7.3,0]) cube([23.6,14.6,0.6]);
}
module shaft_coupon() {
    difference() {
        cube([50,22,4]);
        for(i=[0:2]) translate([9+16*i,11,-0.1]) cylinder(d=6+0.2*i,h=4.2);
    }
}
module switch_reference(p=0) {
    color([0.35,0.38,0.4]) translate([-3,-3,-board_drop]) cube([6,6,switch_case]);
    color([0.8,0.76,0.65]) translate([0,0,-board_drop+switch_case]) cylinder(d=3.5,h=switch_height-switch_case-min(switch_pt,max(0,p-nominal_gap)));
}
module mechanism(b,p=0) {
    color([0.18,0.22,0.25]) switch_holder(b);
    color([0.87,0.55,0.21]) translate([0,0,clip_bottom-max(0,p-0.2)]) retaining_clip();
    switch_reference(p);
    color([0.75,0.78,0.82,0.45]) translate([0,0,-board_drop+switch_case]) linear_extrude(3-max(0,p-0.2))
        difference() {circle(d=spring_od);circle(d=spring_id);}
    top=stem_bottom+puck_insert-p;
    bottom=max(top-puck_height,-board_drop+switch_height-min(switch_pt,max(0,p-nominal_gap)));
    color([0.82,0.37,0.25]) translate([0,0,bottom]) cylinder(d=puck_d,h=top-bottom);
}
module key_sweep(b) {
    // Sweep each convex moving part; remove only intentional stop-face contact.
    translate([0,0,cap_under-travel+0.01]) linear_extrude(cap_thick+travel-0.01) cap_profile(b);
    translate([0,0,stem_bottom-travel]) linear_extrude(cap_under+0.2-stem_bottom+travel) post_profile();
    translate([-4.5,-4.5,clip_bottom-travel]) cube([9,9,clip_thick+travel-0.01]);
}
