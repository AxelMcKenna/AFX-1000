// RMX standalone enclosure A04/E07/E18. Millimetres. Read README.md before fabrication.
// Generated control coordinates come from generate.py; edit that source for layout.
include <generated/layout.scad>
include <generated/components.scad>
use <mechanisms.scad>

part = "assembly"; // [assembly,base,panel,controls,rear_panel,panel_2d,internals,lever_bracket,lever_arm,fit_coupon,strip_backer,lever_collision,output_collision,output_board,control_board,control_collision]
exploded = 0;      // Vertical separation in mm for review.
show_controls = true;
show_internals = false;
show_panel = true;
lever_angle = 0; // [0:35]
$fn = 72;

// A01 design choices, not measurements of the original housing.
wall = 2.8;
floor_thickness = 2.8;
shell_height = 36;
panel_thickness = 2;
panel_z = shell_height - panel_thickness;
corner_radius = 7;
panel_inset = 3.1;
seat_width = 1.8;
seat_depth = 2;
screw_clearance = 3.4;
boss_diameter = 8.4;
pilot_diameter = 2.5; // Placeholder: validate against selected inserts or screws.

assert(wall > 0 && floor_thickness > 0);
assert(panel_inset > wall && panel_inset < wall + seat_width);
assert(panel_thickness == seat_depth);

function mount_diameter(m) = m[0]=="audio_carrier" ? 7.2 : 6;

module rounded_rect(w, d, r) {
    hull() for (x = [r, w-r], y = [r, d-r])
        translate([x,y]) circle(r=r);
}

module sector(ri, ro, a, b) {
    polygon(concat(
        [for (i=[0:24]) [ro*cos(a+(b-a)*i/24),ro*sin(a+(b-a)*i/24)]],
        [for (i=[24:-1:0]) [ri*cos(a+(b-a)*i/24),ri*sin(a+(b-a)*i/24)]]));
}

module aperture(c) {
    // [id,kind,x,y,w,h,angle0,angle1]; sizes are provisional panel openings.
    translate([c[2],c[3]])
        if (c[1] == "knob") circle(d=c[4]);
        else if (c[1] == "sector") sector(c[4],c[5],c[6],c[7]);
        else translate([-c[4]/2,-c[5]/2]) square([c[4],c[5]]);
}

module panel_outline() {
    translate([panel_inset,panel_inset])
        rounded_rect(body_width-2*panel_inset,body_depth-2*panel_inset,
                     corner_radius-panel_inset);
}

module panel_2d() {
    difference() {
        panel_outline();
        for (c = openings) aperture(c);
        for (p = fasteners) translate(p) circle(d=screw_clearance);
    }
}

module base() {
    difference() {
        union() {
            difference() {
                linear_extrude(shell_height)
                    rounded_rect(body_width,body_depth,corner_radius);
                translate([wall,wall,floor_thickness])
                    linear_extrude(shell_height)
                        rounded_rect(body_width-2*wall,body_depth-2*wall,
                                     corner_radius-wall);
            }
            // Continuous lid seat; its top is flush with the screw bosses.
            translate([0,0,panel_z-seat_depth]) linear_extrude(seat_depth)
                difference() {
                    rounded_rect(body_width,body_depth,corner_radius);
                    translate([wall+seat_width,wall+seat_width])
                        rounded_rect(body_width-2*(wall+seat_width),
                                     body_depth-2*(wall+seat_width),
                                     max(1,corner_radius-wall-seat_width));
                }
            for (p = fasteners) translate([p[0],p[1],floor_thickness])
                cylinder(h=panel_z-floor_thickness,d=boss_diameter);
            for (m = board_mounts) translate([m[1],m[2],floor_thickness])
                cylinder(h=m[3]-floor_thickness,d=mount_diameter(m));
            // Front ring-board support clears the power component reserve below.
            translate([244,148,floor_thickness]) cylinder(h=25.6-floor_thickness,d=6);
            translate([238,127,23]) cube([12,21,2.6]);
        }
        // Full removable standalone I/O cassette. Side webs hold its four screws.
        translate([26,-1,3.8]) cube([282,wall+2,27.2]);
        for (x=[20,314],z=[8,28]) translate([x,-1,z]) rotate([-90,0,0])
            cylinder(h=wall+2,d=screw_clearance);
        for (p = fasteners) translate([p[0],p[1],floor_thickness+1])
            cylinder(h=shell_height,d=pilot_diameter);
        for (m = board_mounts)
            if(m[0]=="audio_carrier") translate([m[1],m[2],-0.1])
                cylinder(h=m[3]+0.2,d=m[4]);
            else translate([m[1],m[2],floor_thickness+0.8]) cylinder(h=m[3],d=m[4]);
        // Recess only the internal floor under E06. Through insert bores retain
        // their full boss section; no blind-insert depth is assumed here.
        for(p=floor_pockets) difference() {
            translate([p[1],p[2],p[5]]) linear_extrude(floor_thickness-p[5]+0.01)
                rounded_rect(p[3],p[4],1);
            for(m=board_mounts) if(m[0]=="audio_carrier")
                translate([m[1],m[2],0]) cylinder(h=10,d=mount_diameter(m));
        }
        translate([244,129,22]) cylinder(h=5,d=2);
        // Front ventilation: no parts may project outside their reserved volumes.
        for(x=[215:8:279]) translate([x,body_depth-wall-1,8]) cube([3,wall+2,8]);
    }
}

module rear_panel() {
    difference() {
        translate([12,-1.6,3]) cube([310,1.6,30]);
        for (x=[20,314],z=[8,28]) translate([x,-2,z]) rotate([-90,0,0])
            cylinder(h=3,d=screw_clearance);
        for(p=rear_ports)
            if(p[1]=="round") translate([p[2],-2,p[3]]) rotate([-90,0,0]) cylinder(h=3,d=p[4]);
            else translate([p[2]-p[4]/2,-2,p[3]-p[5]/2]) cube([p[4],3,p[5]]);
    }
}

module controls() {
    // Most caps are visual envelopes; functional switch plungers need fit coupons.
    for (c = caps) translate([c[2],c[3],shell_height]) {
        if (c[1] == "knob") {
            color([0.10,0.11,0.12]) cylinder(h=c[6],d=c[4]);
            color("white") translate([-0.5,-c[4]/2+2,c[6]])
                cube([1,c[4]*0.32,0.3]);
        } else if (c[1] == "sector") {
            color(c[6] < 180 ? [0.12,0.50,0.48] : [0.74,0.42,0.12])
                linear_extrude(2.4) sector(c[4],c[5],c[6],c[7]);
        } else if(c[1]!="lever") {
            color(c[1] == "strip" ? [0.15,0.42,0.43] : [0.22,0.24,0.25])
                translate([-c[4]/2,-c[5]/2,0]) cube([c[4],c[5],c[6]]);
        }
    }
    // Decorative lens envelope; optical mounting and panel apertures remain open.
    color([0.15,0.8,0.75,0.5]) translate([244,78,shell_height])
        linear_extrude(1) difference() { circle(r=26); circle(r=22); }
    color([0.12,0.13,0.14]) lever_arm(lever_angle);
}

module internals() {
    for(b=boards) color([0.12,0.40,0.29]) difference() {
        translate([b[1],b[2],b[3]]) cube([b[4],b[5],b[6]]);
        for(m=board_mounts) if(m[0]==b[0]) translate([m[1],m[2],b[3]-1]) cylinder(h=4,d=2.4);
        for(m=daughterboard_mounts) if(b[0]==m[0] || b[0]=="dsp_carrier")
            translate([m[1],m[2],b[3]-1]) cylinder(h=4,d=m[5]);
    }
    color([0.12,0.40,0.29]) translate([244,78,25.6]) linear_extrude(1.6) difference() {
        circle(r=54); circle(r=18);
        for(m=board_mounts) if(m[0]=="scene_board") translate([m[1]-244,m[2]-78]) circle(d=2.4);
        translate([0,51]) circle(d=2.4);
    }
    for(e=envelopes) color(e[0]=="seed3"?[0.75,0.55,0.18,0.9]:[0.55,0.58,0.60,0.65])
        translate([e[1],e[2],e[3]]) cube([e[4],e[5],e[6]]);
    color([0.35,0.37,0.40]) lever_bracket();
    color([0.15,0.18,0.20]) strip_backer();
}

module lever_collision() {
    intersection() {
        lever_sweep();
        union() {
            base();
            translate([0,0,panel_z]) linear_extrude(panel_thickness) panel_2d();
            lever_bracket();
            for(e=envelopes) translate([e[1],e[2],e[3]]) cube([e[4],e[5],e[6]]);
        }
    }
}

module output_board() {
    for(b=boards) if(b[0]=="audio_carrier") color([0.12,0.40,0.29]) difference() {
        translate([b[1],b[2],b[3]]) cube([b[4],b[5],b[6]]);
        for(m=board_mounts) if(m[0]==b[0]) translate([m[1],m[2],b[3]-1]) cylinder(h=4,d=2.4);
    }
    for(e=output_envelopes) color([0.70,0.30,0.20,0.8])
        translate([e[1],e[2],e[3]]) cube([e[4],e[5],e[6]]);
}

module output_collision() {
    intersection() {
        output_board();
        union() {
            base();
            translate([0,0,panel_z]) linear_extrude(panel_thickness) panel_2d();
            lever_bracket();
            for(b=boards) if(b[0]!="audio_carrier")
                translate([b[1],b[2],b[3]]) cube([b[4],b[5],b[6]]);
            // Scene control PCB and the conservative switch/lead reserves.
            translate([244,78,25.4]) linear_extrude(2.0) difference() {circle(r=54);circle(r=18);}
            for(e=stationary_envelopes) translate([e[1],e[2],e[3]]) cube([e[4],e[5],e[6]]);
            for(p=port_envelopes) translate([p[1],p[2],p[3]]) cube([p[4],p[5],p[6]]);
        }
    }
}

module control_board() {
    for(b=boards) if(b[0]=="control_input_hub") color([0.12,0.40,0.29]) difference() {
        translate([b[1],b[2],b[3]]) cube([b[4],b[5],b[6]]);
        for(m=daughterboard_mounts) translate([m[1],m[2],b[3]-1]) cylinder(h=4,d=m[5]);
    }
    for(e=control_envelopes) color([0.35,0.50,0.75,0.8])
        translate([e[1],e[2],e[3]]) cube([e[4],e[5],e[6]]);
}

module control_collision() {
    intersection() {
        control_board();
        union() {
            base();
            translate([0,0,panel_z]) linear_extrude(panel_thickness) panel_2d();
            lever_bracket();
            for(b=boards) if(b[0]!="control_input_hub")
                translate([b[1],b[2],b[3]]) cube([b[4],b[5],b[6]]);
            translate([244,78,25.4]) linear_extrude(2.0) difference() {circle(r=54);circle(r=18);}
            for(e=concat(control_obstacles,output_envelopes,port_envelopes))
                translate([e[1],e[2],e[3]]) cube([e[4],e[5],e[6]]);
        }
    }
}

// Layout coordinates use SVG-style +Y toward the performer. Exported Cartesian
// geometry uses +Y toward the rear, keeping the top view consistent with the SVG.
module cad_orientation() { translate([0,body_depth,0]) mirror([0,1,0]) children(); }

cad_orientation() {
if (part == "base") base();
else if (part == "panel") linear_extrude(panel_thickness) panel_2d();
else if (part == "panel_2d") panel_2d();
else if (part == "controls") controls();
else if (part == "rear_panel") rear_panel();
else if (part == "internals") internals();
else if (part == "lever_bracket") translate([-303,-66,-7]) lever_bracket();
else if (part == "lever_arm") translate([-305,-78,-14]) lever_arm(0);
else if (part == "lever_collision") lever_collision();
else if (part == "output_collision") output_collision();
else if (part == "output_board") output_board();
else if (part == "control_board") control_board();
else if (part == "control_collision") control_collision();
else if (part == "fit_coupon") fit_coupon();
else if (part == "strip_backer") translate([-72,-122,-31.8]) strip_backer();
else {
    color([0.08,0.09,0.10]) base();
    if (show_panel) color([0.18,0.19,0.20]) translate([0,0,panel_z+exploded])
        linear_extrude(panel_thickness) panel_2d();
    color([0.12,0.13,0.14]) rear_panel();
    if (show_internals) internals();
    if (show_controls) translate([0,0,exploded]) controls();
}
}
