// Sensor harness development candidate. Nominal geometry; not assembly release.
include <../../two_board_print_03/retention_r5.scad>
use <../carrier.scad>
use <../spring.scad>
use <../population.scad>
$fn=32;
module legacy_cable_segment(a,b,r=4.5){hull(){translate(a)sphere(r=r);translate(b)sphere(r=r);}}
module legacy_cable_route(){
 legacy_cable_segment([234,55,28],[246,62,28]);
 legacy_cable_segment([246,62,28],[283,76,28]);
 legacy_cable_segment([283,76,28],[293,82,25.1]);
}
module legacy_sensor_fanout(){for(y=[78,80.5,83,85.5])legacy_cable_segment([293,82,25.1],[298.2,y,25.1],.7);}
module legacy_main_mate(){translate([228.63,53.75,10.89])cube([10.36,2.5,14]);}
module legacy_main_fanout(){for(x=[230,232.54,235.08,237.62])legacy_cable_segment([x,55,24.89],[234,55,28],.7);}
module legacy_tbh05_harness_installed(){legacy_cable_route();legacy_sensor_fanout();legacy_main_mate();legacy_main_fanout();}
if(part=="route_components_clearance")intersection(){union(){legacy_cable_route();legacy_sensor_fanout();legacy_main_fanout();}box_rows(component_boxes);}
if(part=="route_controls_clearance")intersection(){legacy_tbh05_harness_installed();union(){translate([0,0,H])lid();guide_installed();holders_installed();}}
if(part=="route_carrier_clearance")intersection(){legacy_tbh05_harness_installed();union(){carrier_complete();sensor_cap();}}
if(part=="route_shell_clearance")intersection(){legacy_tbh05_harness_installed();shell();}
if(part=="route_positive")legacy_tbh05_harness_installed();
// Removable two-piece ribbon clamps. Ribbon width up to 7.874, thickness .889.
module legacy_clamp_pose(sensor=false){
 translate(sensor?[289,79.6,26.26]:[255,65.4054,28])
 rotate([0,sensor?14:0,sensor?30.964:20.725])children();
}
module legacy_ribbon_saddle(sensor=false){difference(){union(){
 // Lower jaw seats ribbon bottom at local Z=-.5; screw bosses are lateral.
 legacy_clamp_pose(sensor)translate([-3,-8,-3.5])cube([6,16,3]);
 translate(sensor?[294,88,8.35]:[250,57,8.35])cylinder(d=4.5,h=sensor?10:15);
 hull(){translate(sensor?[294,88,16.5]:[250,57,21.5])cylinder(d=4.5,h=1.8);
 legacy_clamp_pose(sensor)translate([-2,-2,-2])cube([4,4,1.2]);}
 }translate(sensor?[294,88,8.2]:[250,57,8.2])cylinder(d=2.4,h=17);
 translate(sensor?[294,88,18.35]:[250,57,23.35])cylinder(d=4.8,h=30);
 legacy_clamp_pose(sensor)for(y=[-6.5,6.5])translate([0,y,-3.6])cylinder(d=1.6,h=3.2);
}}
module legacy_ribbon_lid(sensor=false){legacy_clamp_pose(sensor)difference(){union(){translate([-3,-8,.5])cube([6,16,1.5]);for(y=[-8,4.2])translate([-3,y,-.5])cube([6,3.8,1]);}for(y=[-6.5,6.5])translate([0,y,.4])cylinder(d=2.3,h=2);}}
module legacy_harness_supports(){for(s=[false,true]){legacy_ribbon_saddle(s);legacy_ribbon_lid(s);}}
if(part=="supports_components_clearance")intersection(){legacy_harness_supports();box_rows(component_boxes);}
if(part=="supports_controls_clearance")intersection(){legacy_harness_supports();union(){translate([0,0,H])lid();guide_installed();holders_installed();}}
if(part=="supports_carrier_clearance")intersection(){legacy_harness_supports();union(){carrier_complete();sensor_cap();}}
if(part=="supports_shell_clearance")intersection(){legacy_harness_supports();shell();}
if(part=="saddle_main_positive")legacy_ribbon_saddle(false);
if(part=="saddle_sensor_positive")legacy_ribbon_saddle(true);
if(part=="lid_main_positive")legacy_ribbon_lid(false);
if(part=="lid_sensor_positive")legacy_ribbon_lid(true);

module legacy_clamp_fasteners(){for(s=[false,true])legacy_clamp_pose(s)for(y=[-6.5,6.5])translate([0,y,2]){cylinder(d=3.8,h=1.6);translate([0,0,-5])cylinder(d=2,h=5);}}
// Sensor support is10mm tall: M2x20 gives original -1.15mm tip; main15mm/M2x25.
module legacy_mount_heads(){for(s=[false,true])translate(s?[294,88,18.35]:[250,57,23.35]){cylinder(d=4.5,h=.5);translate([0,0,.5])cylinder(d=3.8,h=2);}}
module legacy_tbh05_harness_complete(){legacy_tbh05_harness_installed();legacy_harness_supports();legacy_clamp_fasteners();legacy_mount_heads();}
if(part=="hardware_controls_clearance")intersection(){union(){legacy_clamp_fasteners();legacy_mount_heads();}union(){translate([0,0,H])lid();guide_installed();holders_installed();carrier_complete();sensor_cap();box_rows(component_boxes);}}
// Exclude only the intended washer seating plane from empty-intersection test.
module legacy_mount_heads_above_seat(){difference(){legacy_mount_heads();for(p=[[250,57,23.35],[294,88,18.35]])translate([p[0]-3,p[1]-3,p[2]-.01])cube([6,6,.02]);}}
if(part=="mount_heads_supports_clearance")intersection(){legacy_mount_heads_above_seat();legacy_harness_supports();}
if(part=="mount_seat_contact_positive")intersection(){translate([0,0,-.01])legacy_mount_heads();legacy_harness_supports();}
module legacy_components_except_J1010(){for(b=component_boxes)if(!(b[0][0]==228.23 && b[0][1]==53.23 && b[0][2]==239.39 && b[0][3]==56.77))box_rows([b]);}
if(part=="mate_components_clearance")intersection(){legacy_main_mate();legacy_components_except_J1010();}
if(part=="harness_motion_clearance")intersection(){legacy_tbh05_harness_complete();union(){spring_arm_sweep(.5);spring_bracket_world();spring_installed_envelope();}}
