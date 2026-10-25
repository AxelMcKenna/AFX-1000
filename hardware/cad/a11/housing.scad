// A11 retains the A07 enclosure dimensions; units are millimetres.
wall = 2.8;
floor_thickness = 2.8;
shell_height = 38;
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

function mount_diameter(m) = (m[0]=="audio_carrier" || m[0]=="dsp_carrier" || m[0]=="led_driver" || m[0]=="input_power") ? 7.2 : 6;



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
            for (m = board_mounts) if(m[0]!="scene_board") translate([m[1],m[2],floor_thickness])
                cylinder(h=m[3]-floor_thickness,d=mount_diameter(m));

        }
        // Full removable standalone I/O cassette. Side webs hold its four screws.
        translate([26,-1,3.8]) cube([282,wall+2,27.2]);
        for (x=[20,318],z=[8,28]) translate([x,-1,z]) rotate([-90,0,0])
            cylinder(h=wall+2,d=screw_clearance);
        for (p = fasteners) translate([p[0],p[1],floor_thickness+1])
            cylinder(h=shell_height,d=pilot_diameter);
        for (m = board_mounts) if(m[0]!="scene_board")
            if(m[0]=="audio_carrier" || m[0]=="dsp_carrier" || m[0]=="led_driver" || m[0]=="input_power" || m[0]=="power_carrier" || m[0]=="disconnect_carrier") translate([m[1],m[2],-0.1])
                cylinder(h=m[3]+0.2,d=m[4]);
            else translate([m[1],m[2],floor_thickness+0.8]) cylinder(h=m[3],d=m[4]);
        // Preserve C24 vent space through the local inner lid ledge.
        // The outer wall and lid remain intact.
        translate([disconnect_guide_relief[0],disconnect_guide_relief[1],panel_z-seat_depth-0.1])
            cylinder(d=disconnect_guide_relief[2],h=seat_depth+0.2,$fn=96);
        // Recess only the internal floor under E06. Through insert bores retain
        // their full boss section; no blind-insert depth is assumed here.
        for(p=floor_pockets) difference() {
            translate([p[1],p[2],p[5]]) linear_extrude(floor_thickness-p[5]+0.01)
                rounded_rect(p[3],p[4],1);
            for(m=board_mounts) if(m[0]=="audio_carrier")
                translate([m[1],m[2],0]) cylinder(h=10,d=mount_diameter(m));
        }

        // Front ventilation: no parts may project outside their reserved volumes.
        for(x=[215:8:279]) translate([x,body_depth-wall-1,8]) cube([3,wall+2,8]);
    }
}

module rear_panel() {
    difference() {
        translate([12,-1.6,3]) cube([310,1.6,30]);
        for (x=[20,318],z=[8,28]) translate([x,-2,z]) rotate([-90,0,0])
            cylinder(h=3,d=screw_clearance);
        for(p=rear_ports)
            if(p[1]=="round") translate([p[2],-2,p[3]]) rotate([-90,0,0]) cylinder(h=3,d=p[4]);
            else translate([p[2]-p[4]/2,-2,p[3]-p[5]/2]) cube([p[4],3,p[5]]);
    }
}

module input_pcb() {
    for(b=boards) if(b[0]=="input_power") difference() {
        translate([b[1],b[2],b[3]]) linear_extrude(b[6]) polygon(input_outline);
        for(m=board_mounts) if(m[0]==b[0]) translate([m[1],m[2],b[3]-1]) cylinder(h=4,d=2.2);
    }
}

module board_reserve(b) {
    if(b[0]=="disconnect_carrier") translate([b[1],b[2],b[3]]) linear_extrude(b[6]) polygon(disconnect_outline);
    else
    if(b[0]=="input_power") input_pcb();
    else translate([b[1],b[2],b[3]]) cube([b[4],b[5],b[6]]);
}
