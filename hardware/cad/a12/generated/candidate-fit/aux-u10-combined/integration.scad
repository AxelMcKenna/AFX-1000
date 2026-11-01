// A12: inherited A11 housing and controls with a new relieved P03 supply bay.
// This conservative reserve is replaced by actual P03 courtyards before release.
include </Users/axelmckrnna/dev/rmx-publish/hardware/cad/a11/generated/layout.scad>
include </Users/axelmckrnna/dev/rmx-publish/hardware/cad/a11/generated/button-fixture.scad>
include </Users/axelmckrnna/dev/rmx-publish/hardware/cad/a11/generated/controls.scad>
include </Users/axelmckrnna/dev/rmx-publish/hardware/cad/a12/generated/candidate-fit/aux-u10-combined/components.scad>
include </Users/axelmckrnna/dev/rmx-publish/hardware/cad/a12/generated/interface.scad>
use </Users/axelmckrnna/dev/rmx-publish/hardware/cad/a11/mechanisms.scad>
include </Users/axelmckrnna/dev/rmx-publish/hardware/cad/a11/housing.scad>
include </Users/axelmckrnna/dev/rmx-publish/hardware/cad/a11/controls.scad>

part="review";
$fn=64;

module a12_chassis() {
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

module p03_outline(unrelieved=false) {
    if(unrelieved) square([160,45]);
    else polygon(p03_outline);
}

module p03_reserve(unrelieved=false, components_only=false, margin=0) {
    dz_min=p03_adjustable_bottom_z_range[0]-p03_datum[2];
    dz_max=p03_adjustable_bottom_z_range[1]-p03_datum[2];
    thickness_min=p03_fabrication_thickness_range[0];
    thickness_max=p03_fabrication_thickness_range[1];
    translate(p03_datum) {
        if(!components_only) difference() {
            linear_extrude(p03_thickness) p03_outline(unrelieved);
            for(p=p03_mounts) translate([p[0],p[1],-0.1]) cylinder(d=p03_mount_drill,h=p03_thickness+0.2);
        }
        translate([0,0,dz_min+thickness_min-margin]) linear_extrude(dz_max-dz_min+thickness_max-thickness_min+p03_top_assembly_height_limit+2*margin)
            offset(delta=margin) p03_outline(unrelieved);
        // Bottom component allocation conservatively covers the whole relieved
        // outline. The native check excludes only the four intended supports.
        translate([0,0,dz_min-p03_bottom_assembly_height_limit-margin])
            linear_extrude(dz_max-dz_min+p03_bottom_assembly_height_limit+margin)
                difference() {
                    offset(delta=margin) p03_outline(unrelieved);
                    for(p=p03_mounts) translate(p) circle(d=7);
                }
    }
}

module a12_switch_electronics() {
    // Strengthen standalone.py's B3F-1000 reserve to the A12 interface
    // allocations, at CURRENT A11 centres and fixture rotations.
    // This does not model the complete loose control wiring or approve its fit.
    for(b=buttons) button_pose(b) {
        translate([-a12_switch_body_xy[0]/2,-a12_switch_body_xy[1]/2,-board_drop])
            cube([a12_switch_body_xy[0],a12_switch_body_xy[1],a12_switch_body_height]);
        translate([-a12_switch_body_xy[0]/2,-a12_switch_body_xy[1]/2,-board_drop-a12_switch_lead_drop])
            cube([a12_switch_body_xy[0],a12_switch_body_xy[1],a12_switch_lead_drop]);
    }
}

module p03_obstacles() {
    a12_chassis(); rear_panel(); lever_bracket(); touch_backer(); lever_sweep();
    translate([0,0,panel_z]) front_panel();
    translate([0,0,panel_z-guide_thick]) guide_plate();
    for(b=buttons) button_pose(b) { switch_holder(b); key_sweep(b); }
    a12_switch_electronics();
    for(b=boards) board_reserve(b);
    for(e=envelopes) translate([e[1],e[2],e[3]]) cube([e[4],e[5],e[6]]);
    for(e=port_envelopes) translate([e[1],e[2],e[3]]) cube([e[4],e[5],e[6]]);
    for(c=disconnect_cylinders) translate([c[1],c[2],c[3]]) cylinder(d=c[4],h=c[5],$fn=96);
}

function is_inlet(e) = [for(i=[0:5]) e[0][i]] == ["i","n","l","e","t","_"];
module inlet_obstacles() {
    a12_chassis(); rear_panel(); lever_bracket(); touch_backer(); lever_sweep();
    translate([0,0,panel_z]) front_panel();
    translate([0,0,panel_z-guide_thick]) guide_plate();
    for(b=buttons) button_pose(b) { switch_holder(b); key_sweep(b); }
    a12_switch_electronics();
    for(b=boards) if(b[0]!="input_power") board_reserve(b);
    for(e=envelopes) if(!is_inlet(e)) translate([e[1],e[2],e[3]]) cube([e[4],e[5],e[6]]);
    p03_reserve();
    for(c=disconnect_cylinders) translate([c[1],c[2],c[3]]) cylinder(d=c[4],h=c[5],$fn=96);
}

if(part=="inlet_collision") intersection() {
    for(e=envelopes) if(is_inlet(e)) translate([e[1]-.25,e[2]-.25,e[3]-.25]) cube([e[4]+.5,e[5]+.5,e[6]+.5]);
    inlet_obstacles();
}
if(part=="inlet_board_collision") intersection() {
    translate([0,0,.00001]) input_pcb();
    inlet_obstacles();
}

if(part=="collision") intersection() {
    p03_reserve(components_only=true,margin=p03_minimum_external_clearance);
    p03_obstacles();
}
if(part=="unrelieved_positive_control") intersection() {
    p03_reserve(unrelieved=true,components_only=true,margin=p03_minimum_external_clearance);
    p03_obstacles();
}
if(part=="board_collision") intersection() {
    translate([0,0,0.00001]) p03_reserve();
    p03_obstacles();
}
if(part=="review") {
    color([0.15,0.2,0.23,0.22]) a12_chassis();
    color([0.12,0.4,0.29,0.7]) for(b=boards) board_reserve(b);
    color([0.7,0.4,0.12,0.5]) p03_reserve();
}
