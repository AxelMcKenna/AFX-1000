// New integral wall-column + removable keeper receiving proposal.
// Every original board/part pose remains fixed; no fabrication approval.
include <../robust_rear_variant/checks.scad>
mount_case="none";
mounts=[["NF233",210,42.5],["NF233",310,42.5],["FPC84",31,41.5],["FPC84",68.5,41.5]];
module mr_thread(p,major=false){translate([p[1],184.0,35.79])cylinder(d=major?2.12:1.6,h=p[2]-.95-35.79+.02,$fn=64);}
module mr_column(p,assembly=false){difference(){union(){
 // Real0.1mmwall overlap bonds the column to retained2.8mmfrontwall.
 translate([p[1]-3,184.3,2.8])cube([6,1.9,p[2]-.95-2.8]);
 translate([p[1]-3,179.9,2.8])cube([6,5.8,1.9]);
 translate([p[1]-2,182.5,35.5])cube([4,3.7,p[2]-.95-35.5]);
 }translate([p[1]-3.01,180.5,3.5])cube([6.02,2.0,1.21]);mr_thread(p,assembly);}}
module mr_keeper(p){difference(){
 // OneexactYZprofile eliminates separatecuboids' 7e-15mm join mismatch.
 translate([p[1]-3,0,0])rotate([90,0,90])linear_extrude(6)polygon([
 [179.9,p[2]-1.2],[180.5,p[2]-1.2],[180.5,p[2]+.2],
 [182.5,p[2]+.2],[182.5,p[2]-.95],[185.7,p[2]-.95],
 [185.7,43.6],[179.9,43.6]]);
 translate([p[1],184.0,p[2]-1])cylinder(d=2.4,h=7,$fn=64);
 }}

module mr_pockets(){for(p=mounts)translate([p[1]-3.15,183.6,p[2]-.97])cube([6.3,2.2,43.62-(p[2]-.97)]);}
module mr_lidholes(){for(p=mounts)translate([p[1],184.0,43.59])cylinder(d=2.4,h=2.02,$fn=64);}
module mr_carrier(assembly=false){difference(){union(){ui_shell();for(p=mounts)mr_column(p,assembly);}mr_pockets();for(p=mounts){mr_thread(p,assembly);translate([p[1],184.0,p[2]-.96])cylinder(d=2.4,h=7,$fn=64);}}}
module mr_lid(){difference(){ui_lid();mr_lidholes();}}
module mr_keepers(){for(p=mounts)mr_keeper(p);}
module mr_screws(){for(p=mounts){translate([p[1],184.0,35.8])cylinder(d=2.1,h=10.2,$fn=64);translate([p[1],184.0,46])cylinder(d=4,h=2.1,$fn=64);difference(){translate([p[1],184.0,45.6])cylinder(d=5,h=.4,$fn=64);translate([p[1],184.0,45.59])cylinder(d=2.2,h=.42,$fn=64);}}}
module mr_new(){for(p=mounts)mr_column(p,true);mr_keepers();mr_screws();}
if(mount_case=="new_carrier_geometry")mr_carrier();
if(mount_case=="new_lid_geometry")mr_lid();
for(i=[0:3]){
 if(mount_case==str("keeper_",i))mr_keeper(mounts[i]);
 if(mount_case==str("column_",i))mr_column(mounts[i]);
}
if(mount_case=="screw_receiving_geometry")mr_screws();
if(mount_case=="new_parts_components_collision")intersection(){mr_new();fr_boxes(fr_boxes,"all",.45);}
if(mount_case=="new_parts_rear_tails_collision")intersection(){mr_new();fr_boxes(fr_tails,"all",.45);}
if(mount_case=="new_parts_mates_collision")intersection(){mr_new();fr_boxes(fr_mates,"all",.45);}
if(mount_case=="own_PCB_seats_collision")intersection(){mr_new();mr_PCB_seat_interior();}
if(mount_case=="keeper_carrier_collision")intersection(){translate([0,0,.00002])mr_keepers();mr_carrier(true);}
if(mount_case=="screw_carrier_receiving_collision")intersection(){translate([0,0,.00002])mr_screws();mr_carrier(true);}
if(mount_case=="screw_keeper_receiving_collision")intersection(){mr_screws();mr_keepers();}
if(mount_case=="screw_lid_bore_collision")intersection(){translate([0,0,.00002])mr_screws();mr_lid();}
if(mount_case=="new_parts_existing_electronics_collision")intersection(){mr_new();ui_electronics(false,false);}
if(mount_case=="new_parts_existing_controls_collision")intersection(){mr_new();ua_all_controls();}
if(mount_case=="new_parts_power_wire_collision")intersection(){mr_new();union(){fr_power_environment();pf_wires(.25);ui_all_joints(.25);}}
if(mount_case=="keeper_head_positive_control")intersection(){mr_screws();translate([30.9,183.9,46.4])cube([.2,.2,.2]);}
if(mount_case=="toe_positive_control")intersection(){mr_new();translate([209.9,180.2,3])cube([.2,.2,.2]);}
// Source-material receiver witnesses: required cuts are deliberate material
// changes, not blanket own-case/board exclusions.
if(mount_case=="uncut_seat_keeper_core_control")intersection(){mr_keepers();ui_shell();translate([212.4,185.2,42])cube([.2,.2,.2]);}

if(mount_case=="unbored_lid_screw_failure")intersection(){for(p=mounts)translate([p[1],184.0,35.8])cylinder(d=2.1,h=10.2,$fn=64);ui_lid();}

// Named TEST-ONLYinterior guards, grounded in all726rawcontacttriangles.
// These are NOMINALcorrelatedseats, not physical factory/Ztol approval.
module mr_PCB_seat_interior(){difference(){fr_PCB();for(p=mounts){
 translate([p[1]-3.00002,180.49998,3.49998])cube([6.00004,1.76004,.00004]);
 translate([p[1]-3.00002,180.49998,3.49998])cube([6.00004,.00004,1.20004]);
 translate([p[1]-3.00002,180.49998,p[2]-1.20002])cube([6.00004,.00004,1.20004]);
}}}
if(mount_case=="PCB_guard_exceeded_control")intersection(){translate([0,.05,0])mr_new();mr_PCB_seat_interior();translate([209.8,180.505,3.6])cube([.4,.04,.4]);}
if(mount_case=="keeper_guard_exceeded_control")intersection(){translate([0,0,-.05+.00002])mr_keepers();mr_carrier(true);translate([211.4,183,41.51])cube([.4,.4,.03]);}
if(mount_case=="screw_carrier_guard_exceeded_control")intersection(){translate([0,0,-.05+.00002])mr_screws();mr_carrier(true);translate([209.8,185.9,45.56])cube([.4,.4,.03]);}
if(mount_case=="screw_lid_guard_exceeded_control")intersection(){translate([0,0,-.05+.00002])mr_screws();mr_lid();translate([211.8,183.8,45.56])cube([.4,.4,.03]);}
