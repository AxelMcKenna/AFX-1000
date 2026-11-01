// Individual input-wire route; conditional mated exit/position requirements.
include <../repaired-integration.scad>
include <generated/input-route.scad>
input_route_part="review";

module input_wire(index, margin=0) {
    points=input_wire_paths[index];
    // Circumscribe the low-resolution spheres; an inscribed tessellation
    // would understate wire radius and could conceal a narrow collision.
    diameter=(input_wire_envelope_diameter+2*margin)/pow(cos(180/24),2);
    for(i=[0:len(points)-2]) hull() {
        translate(points[i]) sphere(d=diameter,$fn=24);
        translate(points[i+1]) sphere(d=diameter,$fn=24);
    }
}
module input_wires(margin=0) {for(index=[0:1]) input_wire(index,margin);}

module input_route_electronics() {
    repaired_pcbs();
    // Only the two intended connector housings are excluded. Their wire-exit
    // dimensions remain an explicit approval gate; all other bodies remain.
    for(b=repaired_boxes) if(b[0]!="P03_J101")
        translate([b[1],b[2],b[3]]) cube([b[4],b[5],b[6]]);
    for(c=repaired_cylinders)
        translate([c[1],c[2],c[3]]) cylinder(d=c[4],h=c[5],$fn=96);
    for(b=boards) if(b[0]!="disconnect_carrier") board_reserve(b);
    for(e=envelopes) if(!old_disconnect(e[0]) && e[0]!="inlet_J2")
        translate([e[1],e[2],e[3]]) cube([e[4],e[5],e[6]]);
    for(e=port_envelopes)
        translate([e[1],e[2],e[3]]) cube([e[4],e[5],e[6]]);
    return_assembly();
}

if(input_route_part=="wires") input_wires();
if(input_route_part=="wire_pair_collision") intersection() {
    input_wire(0,.125); input_wire(1,.125);
}
if(input_route_part=="wire_case_collision") intersection() {
    input_wires(.25); physical_case_obstacles();
}
if(input_route_part=="wire_electronics_collision") intersection() {
    input_wires(.25); input_route_electronics();
}
if(input_route_part=="wire_positive_control") intersection() {
    input_wires();
    translate(input_wire_paths[0][100]-[.1,.1,.1]) cube([.2,.2,.2]);
}
if(input_route_part=="review") {
    color([.1,.4,.3,.25]) input_route_electronics();
    color("red") input_wire(0);
    color("black") input_wire(1);
}
