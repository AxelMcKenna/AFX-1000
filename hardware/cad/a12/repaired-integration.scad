// Actual repaired board footprints on both faces, conditional assembled heights.
include <thermal-integration.scad>
include <generated/repaired-components.scad>

repaired_part="review";
repaired_e28_dz=0;
repaired_e28_vertical_uncertainty=0;
repaired_p03_vertical_uncertainty=0;
function belongs(name, identity) =
    [for(i=[0:len(identity)-1])name[i]] == [for(i=[0:len(identity)-1])identity[i]];
function board_dz(name) = belongs(name,"E28") ? repaired_e28_dz : 0;
function board_z_uncertainty(name) = belongs(name,"E28") ? repaired_e28_vertical_uncertainty :
    belongs(name,"P03") ? repaired_p03_vertical_uncertainty : 0;

module repaired_pcbs(identity="all") {
    for(b=repaired_boards) if(identity=="all" || b[0]==identity)
        translate([b[1][0],b[1][1],b[1][2]+board_dz(b[0])]) difference() {
            linear_extrude(b[2]) polygon(b[3]);
            for(h=b[4]) translate([h[0],h[1],-.01]) cylinder(d=h[2],h=b[2]+.02,$fn=48);
        }
}

module repaired_components(identity="all", margin=0) {
    for(b=repaired_boxes) if(identity=="all" || belongs(b[0],identity))
        translate([b[1]-margin,b[2]-margin,b[3]-margin+board_dz(b[0])-board_z_uncertainty(b[0])])
            cube([b[4]+2*margin,b[5]+2*margin,b[6]+2*margin+2*board_z_uncertainty(b[0])]);
    for(c=repaired_cylinders) if(identity=="all" || belongs(c[0],identity))
        translate([c[1],c[2],c[3]-margin+board_dz(c[0])-board_z_uncertainty(c[0])])
            cylinder(d=c[4]+2*margin,h=c[5]+2*margin+2*board_z_uncertainty(c[0]),$fn=96);
}

function old_disconnect(name) =
    [for(i=[0:10])name[i]] == ["d","i","s","c","o","n","n","e","c","t","_"];

module other_electronics() {
    for(b=boards) if(b[0]!="disconnect_carrier") board_reserve(b);
    for(e=envelopes) if(!old_disconnect(e[0]))
        translate([e[1],e[2],e[3]]) cube([e[4],e[5],e[6]]);
    for(e=port_envelopes) translate([e[1],e[2],e[3]]) cube([e[4],e[5],e[6]]);
}

module physical_case_obstacles() {
    retained_thermal_shell(); thermal_metal_base(); thermal_controls();
    lower_shell_fasteners(); return_retention();
    // The raised-board trial includes the added material of its taller posts.
    if(repaired_e28_dz>0) for(m=board_mounts) if(m[0]=="disconnect_carrier")
        translate([m[1],m[2],m[3]]) difference() {
            cylinder(d=mount_diameter(m),h=repaired_e28_dz,$fn=64);
            translate([0,0,-.01]) cylinder(d=m[4],h=repaired_e28_dz+.02,$fn=48);
        }
}

if(repaired_part=="pcbs") repaired_pcbs();
if(repaired_part=="components") repaired_components();
if(repaired_part=="switch_electronics") a12_switch_electronics();
if(repaired_part=="switch_lead_positive_control") intersection() {
    a12_switch_electronics();
    button_pose(buttons[0]) translate([-.5,-.5,-board_drop-3]) cube([1,1,1]);
}
if(repaired_part=="pcb_case_collision") intersection() {
    // Exclude only the intended nominal standoff seating planes.
    translate([0,0,.00001]) repaired_pcbs();
    physical_case_obstacles();
}
if(repaired_part=="component_case_collision") intersection() {
    repaired_components(margin=.25);
    physical_case_obstacles();
}
if(repaired_part=="component_other_electronics_collision") intersection() {
    repaired_components(margin=.25);
    other_electronics();
}
if(repaired_part=="boards_mutual_collision") intersection() {
    union() {repaired_pcbs("P03");repaired_components("P03",.25);}
    union() {repaired_pcbs("E28");repaired_components("E28",.25);}
}
if(repaired_part=="component_positive_control") intersection() {
    repaired_components();
    // Derive the witness from actual U18 geometry, including any trial shift.
    for(b=repaired_boxes) if(b[0]=="E28_U18")
        translate([b[1]+.25,b[2]+.25,b[3]+board_dz(b[0])+.25]) cube([.2,.2,.2]);
}
if(repaired_part=="review") {
    color([.15,.3,.35,.15]) retained_thermal_shell();
    thermal_assembly();
    color([.08,.4,.22]) repaired_pcbs();
    color([.5,.5,.55,.7]) repaired_components();
    return_assembly();
}
