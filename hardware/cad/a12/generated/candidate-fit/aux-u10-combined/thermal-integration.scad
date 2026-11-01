// A12-only retained plastic carrier with the external metal thermal candidate.
// Native intersections validate nominal solids, not structural or thermal loads.
include </Users/axelmckrnna/dev/rmx-publish/hardware/cad/a12/generated/candidate-fit/aux-u10-combined/integration.scad>
include </Users/axelmckrnna/dev/rmx-publish/hardware/cad/a12/thermal/generated/thermal-base.scad>
use </Users/axelmckrnna/dev/rmx-publish/hardware/cad/a12/returns/generated/returns.scad>

thermal_part="review";

module retained_thermal_shell() {
    difference() {
        a12_chassis();
        thermal_floor_cut();
        thermal_shell_nut_pockets();
        thermal_shell_nut_slots();
        // The lower attachment is a clearance bolt into a captured nut. The
        // inherited 2.5 mm pilot is not a clearance hole for an M3 shank.
        for(p=thermal_shell_bolts)
            translate([p[0],p[1],-.01]) cylinder(d=3.4,h=10.11,$fn=64);
    }
}

module inherited_electronics() {
    for(b=boards) board_reserve(b);
    for(e=envelopes) translate([e[1],e[2],e[3]]) cube([e[4],e[5],e[6]]);
    for(e=port_envelopes) translate([e[1],e[2],e[3]]) cube([e[4],e[5],e[6]]);
    for(c=disconnect_cylinders)
        translate([c[1],c[2],c[3]]) cylinder(d=c[4],h=c[5],$fn=96);
}

module thermal_controls() {
    rear_panel(); lever_bracket(); touch_backer(); lever_sweep();
    translate([0,0,panel_z]) front_panel();
    translate([0,0,panel_z-guide_thick]) guide_plate();
    for(b=buttons) button_pose(b) {switch_holder(b); key_sweep(b);}
    a12_switch_electronics();
}

module lower_shell_fasteners() {
    // Accu SPK-M3-16-A2: maximum head OD5.6/H1.65, 90degree.
    // https://www.accu.co.uk/pozi-countersunk-screws/9526-SPK-M3-16-A2
    // Preserve the stated height with a conservative .35mm rim followed by
    // a 1.3mm cone. The selected base has OD6.6 countersinks, not OD6.
    // Würth03223/DIN934 nut: maximum5.5AF x2.4mm, unchamfered envelope.
    for(p=thermal_shell_bolts) {
        translate([p[0],p[1],-6.2]) {
            cylinder(d=5.6,h=.35,$fn=64);
            translate([0,0,.35]) cylinder(d1=5.6,d2=3,h=1.3,$fn=64);
            translate([0,0,1.65]) cylinder(d=3,h=16-1.65,$fn=64);
        }
        translate([p[0],p[1],5]) difference() {
            cylinder(d=5.5/cos(30),h=2.4,$fn=6);
            translate([0,0,-.01]) cylinder(d=3.2,h=2.42,$fn=48);
        }
    }
}

if(thermal_part=="shell") retained_thermal_shell();
if(thermal_part=="base_shell_collision") intersection() {
    // Exclude the intended coplanar metal/plastic seating face at Z0. The
    // 0.00001 mm shift does not remove any meaningful solid interference.
    translate([0,0,-.00001]) thermal_metal_base();
    retained_thermal_shell();
}
if(thermal_part=="base_electronics_collision") intersection() {
    union() {thermal_metal_base(); thermal_feet();}
    inherited_electronics();
}
if(thermal_part=="base_controls_collision") intersection() {
    thermal_metal_base();
    thermal_controls();
}
if(thermal_part=="unmodified_shell_positive_control") intersection() {
    thermal_metal_base();
    a12_chassis();
}
if(thermal_part=="returns_shell_collision") intersection() {
    return_assembly();
    retained_thermal_shell();
}
if(thermal_part=="returns_controls_collision") intersection() {
    return_assembly();
    thermal_controls();
}
if(thermal_part=="returns_base_collision") intersection() {
    translate([0,0,.00001]) return_assembly();
    thermal_metal_base();
}
if(thermal_part=="returns_hardware") return_assembly();
if(thermal_part=="returns_positive_control") intersection() {
    return_assembly();
    translate([145,132,12]) cube([1,1,1]);
}
if(thermal_part=="lower_shell_fasteners") lower_shell_fasteners();
if(thermal_part=="lower_fastener_shell_collision") intersection() {
    // Exclude intended nut-bearing contact with the pocket floor at Z5.
    translate([0,0,.00001]) lower_shell_fasteners();
    retained_thermal_shell();
}
if(thermal_part=="lower_fastener_base_collision") intersection() {
    lower_shell_fasteners();
    thermal_metal_base();
}
if(thermal_part=="lower_fastener_electronics_collision") intersection() {
    lower_shell_fasteners();
    inherited_electronics();
}
if(thermal_part=="lower_fastener_controls_collision") intersection() {
    lower_shell_fasteners();
    thermal_controls();
}
if(thermal_part=="undersized_countersink_positive_control") intersection() {
    lower_shell_fasteners();
    difference() {
        translate([4,4,-6.2]) cube([8,8,6.2]);
        translate([8,8,-6.21]) cylinder(d=3.4,h=6.22,$fn=64);
        // Deliberately restore the superseded OD6/1.3mm deep countersink.
        translate([8,8,-6.2]) cylinder(d1=6,d2=3.4,h=1.3,$fn=64);
    }
}
if(thermal_part=="review") {
    color([.2,.3,.35,.25]) retained_thermal_shell();
    thermal_assembly();
    color([.1,.45,.25,.5]) inherited_electronics();
}
