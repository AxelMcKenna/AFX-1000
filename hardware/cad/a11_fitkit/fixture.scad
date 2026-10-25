// Compact physical-fit stations derived directly from frozen A11 geometry.
include <../a11/generated/layout.scad>
include <../a11/generated/components.scad>
include <../a11/generated/button-fixture.scad>
include <../a11/generated/controls.scad>
include <../a11/housing.scad>
include <../a11/controls.scad>

part="panel";
index=0;
$fn=48;

// The cropped exterior is a bench fixture. Every retained aperture, guide,
// fixing and contact surface is the original A11 model at the original scale.
function fixture_width(b) = b[1]=="sector" ? 38 : 32;
function fixture_depth(b) = b[1]=="sector" ? 30 : 28;
module source_window(all_buttons, center, angle, size, guide=false) {
    // All original aperture geometry remains. Only button fixing/stem cuts
    // provably outside the crop are omitted before expensive 3D subtraction.
    // Largest fixing-centre offset11.5 + countersink radius2.3 is below15 mm.
    radius=norm(size/2)+15;
    buttons=[for(other=all_buttons) if(norm([other[5],other[6]]-center)<=radius) other];
    include <../a11/controls.scad>
    intersection() {
        rotate([0,0,-angle]) translate([-center[0],-center[1],0])
            if(guide) guide_plate(); else front_panel();
        translate([-size[0]/2,-size[1]/2,-0.1])
            cube([size[0],size[1],(guide?guide_thick:panel_thickness)+0.2]);
    }
}
module button_panel(b) {
    source_window(buttons,[b[5],b[6]],b[7],[fixture_width(b),fixture_depth(b)]);
}
module button_guide(b) {
    source_window(buttons,[b[5],b[6]],b[7],[fixture_width(b),fixture_depth(b)],true);
}
module interface_panel(id) {
    c=[for(c=caps) if(c[0]==id) c][0];
    source_window(buttons,[c[2],c[3]],0,[32,20]);
}
module interface_guide(id) {
    c=[for(c=caps) if(c[0]==id) c][0];
    source_window(buttons,[c[2],c[3]],0,[32,20],true);
}
module moving_interference(b) {
    intersection() {
        key_sweep(b);
        union() {
            button_panel(b);
            translate([0,0,-guide_thick]) button_guide(b);
            switch_holder(b);
        }
    }
}
module holder_guide_contact(b) {
    intersection() {
        switch_holder(b);
        translate([0,0,-guide_thick]) button_guide(b);
    }
}
module stop_contact(b) {
    intersection() {
        translate([0,0,-travel]) key(b);
        button_panel(b);
    }
}
module selector_interference() {
    intersection() {
        selector_cap();
        union() {
            interface_panel("settings");
            translate([0,0,-guide_thick]) interface_guide("settings");
        }
    }
}

b=buttons[index];
if(part=="panel") button_panel(b);
else if(part=="guide") button_guide(b);
else if(part=="key") translate([0,0,cap_under+cap_thick]) rotate([180,0,0]) key(b);
else if(part=="holder") translate([0,0,board_drop+1.6]) switch_holder(b);
else if(part=="clip") retaining_clip();
else if(part=="knob") knob(knobs[index][3],knobs[index][4]);
else if(part=="selector_cap") rotate([180,0,0]) translate([0,0,-5.2]) selector_cap();
else if(part=="selector_panel") interface_panel("settings");
else if(part=="selector_guide") interface_guide("settings");
else if(part=="pot_panel") interface_panel("output");
else if(part=="pot_guide") interface_guide("output");
else if(part=="moving_interference") moving_interference(b);
else if(part=="holder_guide_contact") holder_guide_contact(b);
else if(part=="stop_contact") stop_contact(b);
else if(part=="selector_interference") selector_interference();
