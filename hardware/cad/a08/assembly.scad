// A08 complete printable control family. Open this file in OpenSCAD.
include <generated/layout.scad>
include <generated/components.scad>
include <generated/button-fixture.scad>
include <generated/controls.scad>
use <mechanisms.scad>
include <housing.scad>
include <controls.scad>

part="assembly";
index=0;
press=0;
exploded=0;
show_internals=false;
show_mechanisms=true;
$fn=48;

module chassis() {
    difference() {
        union() {
            base();
            for(x=[20,318],z=[8,28]) translate([x-3.8,wall,z-3.8]) cube([7.6,4.2,7.6]);
        }
        for(x=[20,318],z=[8,28]) {
            translate([x,-2,z]) rotate([-90,0,0]) cylinder(d=3.4,h=10);
            translate([x,wall+1.4,z]) rotate([-90,0,0]) cylinder(d=5.7/cos(30),h=3.2,$fn=6);
        }
    }
}
module electronics_reference() {
    color([0.12,0.4,0.29]) input_pcb();
    for(b=boards) if(b[0]!="input_power") color([0.12,0.4,0.29]) board_reserve(b);
    for(e=envelopes) color([0.55,0.58,0.6,0.5]) translate([e[1],e[2],e[3]]) cube([e[4],e[5],e[6]]);
}
module controls_assembly(p=0) {
    for(k=knobs) translate([k[1],k[2],shell_height+2.8]) {
        color([0.11,0.12,0.13]) knob(k[3],k[4]);
        color([0.9,0.92,0.92]) translate([-0.44,-k[3]/2+1,k[4]-0.49]) cube([0.88,k[3]*0.32,0.05]);
    }
    for(b=buttons) button_pose(b) {
        color(b[1]=="sector"?(b[7]<180?[0.12,0.56,0.53]:[0.88,0.48,0.13]):
            b[0]=="pad_0"||b[0]=="pad_1"||b[0]=="pad_2"||b[0]=="pad_3"?[0.16,0.37,0.68]:[0.24,0.27,0.28])
            translate([0,0,-p]) key(b);
        color([0.85,0.89,0.88]) translate([0,0,cap_under+cap_thick-0.29-p]) linear_extrude(0.03) cap_mark(b);
        if(show_mechanisms) mechanism(b,p);
    }
    for(c=caps) if(c[1]=="switch") color([0.25,0.28,0.29]) translate([c[2],c[3],panel_z]) selector_cap();
    color([0.1,0.12,0.13]) lever_arm(0);
}
module optics() {
    color([0.15,0.7,0.68,0.8]) translate([244,78,shell_height]) ring_lens();
    color([0.16,0.6,0.62,0.7]) translate([74.8,125.8,35.2+panel_z-34]) touch_lens();
    color([0.12,0.22,0.23,0.8]) translate([160,31,35.6+panel_z-34]) display_lens();
    for(y=[21.25,35.25]) color([0.28,0.7,0.35,0.85]) translate([43.9,y,33.2+panel_z-34]) meter_lens();
    for(x=[82,101,120,139]) color([0.22,0.65,0.66,0.85]) translate([x,103,33.2+panel_z-34]) bank_lens();
}
module assembled() {
    color([0.08,0.09,0.1]) chassis();
    color([0.2,0.22,0.23]) rear_panel();
    color([0.14,0.18,0.2]) lever_bracket();
    if(show_internals) electronics_reference();
    translate([0,0,exploded]) {
        color([0.18,0.2,0.21]) translate([0,0,panel_z]) front_panel();
        color([0.42,0.46,0.47]) translate([0,0,panel_z-guide_thick]) guide_plate();
        color([0.22,0.28,0.29]) touch_backer();
        controls_assembly(press);
        optics();
    }
}
module button_section(p=0) {
    b=buttons[13];
    intersection() {
        union() {
            color([0.27,0.46,0.66]) translate([0,0,-p]) key(b);
            mechanism(b,p);
            color([0.6,0.65,0.68]) difference() {
                translate([-17,-14,0]) cube([34,28,2]);
                translate([-(b[2]-1)/2,-(b[3]-1)/2,-0.1]) cube([b[2]-1,b[3]-1,2.2]);
                for(v=b[8]) translate([v[0],v[1],-0.1]) cylinder(d=2.4,h=2.2);
            }
            color([0.4,0.45,0.47]) translate([0,0,-guide_thick]) linear_extrude(guide_thick) difference() {
                square([34,28],center=true);post_profile(stem_d+0.4,stem_flat+0.2);
                for(v=b[8]) translate(v) circle(d=2.4);
            }
        }
        translate([0,-30,-15]) cube([30,60,30]);
    }
}
module moving_collision() {
    intersection() {
        union() { for(b=buttons) button_pose(b) key_sweep(b); }
        union() {
            chassis();
            translate([0,0,panel_z]) front_panel();
            translate([0,0,panel_z-guide_thick]) guide_plate();
            for(b=buttons) button_pose(b) switch_holder(b);
            lever_bracket();touch_backer();
            for(e=envelopes) translate([e[1],e[2],e[3]]) cube([e[4],e[5],e[6]]);
        }
    }
}
module fixed_collision() {
    intersection() {
        union() {
            for(b=buttons) button_pose(b) switch_holder(b);
            translate([0,0,panel_z-guide_thick]) linear_extrude(guide_thick-0.01) guide_plate_2d();
        }
        union() {
            chassis();lever_bracket();touch_backer();
            for(b=boards) board_reserve(b);
            for(e=envelopes) translate([e[1],e[2],e[3]]) cube([e[4],e[5],e[6]]);
            for(e=port_envelopes) translate([e[1],e[2],e[3]]) cube([e[4],e[5],e[6]]);
        }
    }
}
module lever_collision() {
    intersection() {
        lever_sweep();
        union() {
            chassis();lever_bracket();
            translate([0,0,panel_z]) front_panel();
            translate([0,0,panel_z-guide_thick]) guide_plate();
            for(b=buttons) button_pose(b) switch_holder(b);
            for(e=envelopes) translate([e[1],e[2],e[3]]) cube([e[4],e[5],e[6]]);
        }
    }
}
module chassis_collision() {
    intersection() {
        union() { chassis();rear_panel(); }
        union() {
            for(b=boards) board_reserve(b);
            for(e=envelopes) translate([e[1],e[2],e[3]]) cube([e[4],e[5],e[6]]);
        }
    }
}
module optics_collision() {
    intersection() {
        optics();
        union() {
            chassis();
            translate([0,0,panel_z]) front_panel();
            translate([0,0,panel_z-guide_thick]) guide_plate();
            for(b=buttons) button_pose(b) switch_holder(b);
            for(e=envelopes) translate([e[1],e[2],e[3]]) cube([e[4],e[5],e[6]]);
        }
    }
}
module print_layout() {
    color([0.1,0.11,0.12]) chassis();
    color([0.2,0.22,0.23]) translate([0,190,0]) front_panel();
    color([0.4,0.44,0.45]) translate([350,190,0]) guide_plate();
    color([0.28,0.3,0.31]) translate([0,-40,0]) rotate([90,0,0]) rear_panel();
    for(i=[0:len(buttons)-1]) translate([370+(i%10)*25,65+floor(i/10)*27,cap_under+cap_thick])
        rotate([180,0,0]) color(buttons[i][1]=="sector"?[0.17,0.55,0.53]:[0.22,0.37,0.56]) key(buttons[i]);
    for(i=[0:3]) translate([375+42*i,12,0]) color([0.1,0.12,0.13]) knob([16,17,29,32][i],[13,15,18,18][i]);
    for(i=[0,3,13,14]) translate([375+(i==0?0:i==3?1:i==13?2:3)*28,155,board_drop+1.6])
        color([0.26,0.3,0.32]) switch_holder(buttons[i]);
    color([0.25,0.3,0.31]) translate([500,150,0]) translate([-70,-120,-32.6-(panel_z-34)]) touch_backer();
    color([0.12,0.15,0.16]) translate([610,20,0]) translate([-303,-66,-7]) lever_bracket();
    color([0.6,0.35,0.15]) translate([650,20,0]) translate([-305,-78,-14]) lever_arm(0);
    for(i=[0:4]) translate([620+12*i,80,0]) color([0.85,0.5,0.15]) retaining_clip();
    color([0.16,0.63,0.61]) translate([640,135,0.8]) rotate([180,0,0]) ring_lens();
}
// The master print file uses the same geometry as the assembly, in local print poses.
if(part=="base") chassis();
else if(part=="panel") front_panel();
else if(part=="rear_panel") translate([-12,33,1.6]) rotate([90,0,0]) rear_panel();
else if(part=="guide_plate") guide_plate();
else if(part=="button") translate([0,0,cap_under+cap_thick]) rotate([180,0,0]) key(buttons[index]);
else if(part=="holder") translate([0,0,board_drop+1.6]) switch_holder(buttons[index]);
else if(part=="clip") retaining_clip();
else if(part=="knob") knob(knobs[index][3],knobs[index][4]);
else if(part=="selector_cap") rotate([180,0,0]) translate([0,0,-5.2]) selector_cap();
else if(part=="touch_backer") translate([-70,-120,-32.6-(panel_z-34)]) touch_backer();
else if(part=="touch_lens") touch_lens();
else if(part=="ring_lens") rotate([180,0,0]) translate([0,0,-0.8]) ring_lens();
else if(part=="meter_lens") meter_lens();
else if(part=="bank_lens") bank_lens();
else if(part=="display_lens") rotate([180,0,0]) translate([0,0,-0.9]) display_lens();
else if(part=="lever_bracket") translate([-303,-66,-7]) lever_bracket();
else if(part=="lever_arm") translate([-305,-78,-14]) lever_arm(0);
else if(part=="fit_coupon") fit_coupon();
else if(part=="shaft_coupon") shaft_coupon();
else if(part=="button_section") button_section(press);
else if(part=="moving_collision") moving_collision();
else if(part=="fixed_collision") fixed_collision();
else if(part=="lever_collision") lever_collision();
else if(part=="chassis_collision") chassis_collision();
else if(part=="optics_collision") optics_collision();
else if(part=="print_layout") print_layout();
else if(part=="all_holders") for(b=buttons) button_pose(b) switch_holder(b);
else if(part=="all_keys") for(b=buttons) button_pose(b) key(b);
else translate([0,body_depth,0]) mirror([0,1,0]) assembled();
