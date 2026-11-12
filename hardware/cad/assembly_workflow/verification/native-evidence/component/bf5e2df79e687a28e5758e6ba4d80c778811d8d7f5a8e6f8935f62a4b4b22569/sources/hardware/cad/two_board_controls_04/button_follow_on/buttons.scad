include <../../two_board_print_01/captured.scad>
include <../../a11/generated/button-fixture.scad>
include <board-data.scad>
use <../../two_board_print_01/housing.scad>
use <../ring_follow_on/ring.scad>
use <../led_follow_on/banks.scad>
use <../led_follow_on/button_motion.scad>
use <../display.scad>
use <../selectors.scad>
use <caps.scad>
$fn=48;part="buttons_guide";
module tbh07_pose(i){translate([i[2],i[3],0])rotate([0,0,i[4]])children();}
module tbh07_shape(n){difference(){polygon(tbh07_boards[n][0]);for(h=tbh07_boards[n][1])polygon(h);}}
module tbh07_board(n){translate([0,0,42.9])linear_extrude(.6)difference(){tbh07_shape(n);for(p=tbh07_boards[n][2])translate(p)circle(d=2.4);}}
module tbh07_boards_installed(){for(i=tbh07_instances)tbh07_pose(i)tbh07_board(i[1]);}
module tbh07_emitters(){for(i=tbh07_instances)tbh07_pose(i)translate([4.35,-.85,43.5])cube([.9,1.7,.85]);}
module tbh07_solder(){for(i=tbh07_instances)tbh07_pose(i)for(y=[-.825,.825])translate([4.35,y-.45,43.5])cube([.9,.9,.15]);}
module tbh07_wires(){for(i=tbh07_instances)tbh07_pose(i)for(p=tbh07_boards[i[1]][3])translate([p[0],p[1],40.4])cylinder(d=1.5,h=2.5);}
// Custom 0.1mm insulating PET washers close the nominal remaining clamping gap.
module tbh07_shims(){for(i=tbh07_instances)tbh07_pose(i)for(p=tbh07_boards[i[1]][2])translate([p[0],p[1],43.5])linear_extrude(.1)difference(){circle(d=4.2);circle(d=2.4);}}
module tbh07_fasteners(){for(i=tbh07_instances)tbh07_pose(i)for(p=tbh07_boards[i[1]][2])translate([p[0],p[1],37.6]){cylinder(d=2,h=7);translate([0,0,7])cylinder(d1=2,d2=4,h=1);}}
module tbh07_installed(){tbh07_boards_installed();tbh07_emitters();tbh07_solder();tbh07_wires();tbh07_shims();tbh07_fasteners();}
module tbh07_guide_variant(){difference(){tbh06_guide_variant();for(i=tbh07_instances)tbh07_pose(i){translate([0,0,.7])linear_extrude(1)offset(delta=.2)tbh07_shape(i[1]);for(p=tbh07_boards[i[1]][3])translate([p[0],p[1],-.1])cylinder(d=2,h=2);}}}
module tbh07_lid_variant(){tbh06_lid_variant();}
module tbh07_obstacles(){box_rows(component_boxes);pcbs();shell();rear_plate();holders_installed();lid_bars_installed();board_heads();}
module tbh07_others(){tbh06_ring_installed();tbh05_bank_meter_installed();tbh04_display_installed();tbh04_selector_brackets();tbh04_selector_pcbs();tbh04_selector_bodies();tbh04_selector_leads();tbh04_selector_wiring();tbh04_selector_fasteners();}
module tbh07_light_columns(z,h){for(i=tbh07_instances)tbh07_pose(i)translate([4.35,-.85,z])cube([.9,1.7,h]);}
if(part=="buttons_obstacle_clearance")intersection(){union(){tbh07_boards_installed();tbh07_emitters();tbh07_wires();tbh07_shims();}tbh07_obstacles();}
if(part=="buttons_motion_clearance")intersection(){tbh07_installed();tbh05_button_motion_native();}
if(part=="buttons_existing_carrier_clearance")intersection(){tbh07_installed();tbh07_others();}
if(part=="buttons_fastener_clearance")intersection(){union(){tbh07_boards_installed();tbh07_emitters();tbh07_solder();tbh07_shims();}tbh07_fasteners();}
if(part=="buttons_lid_clearance")intersection(){union(){tbh07_boards_installed();tbh07_emitters();tbh07_solder();}translate([0,0,43.6])tbh07_lid_variant();}
// Ignore only the intended PCB-to-pocket seating plane; positive probes below verify support.
if(part=="buttons_guide_clearance")intersection(){union(){translate([0,0,.01])tbh07_boards_installed();tbh07_emitters();tbh07_wires();}translate([0,0,42.2])tbh07_guide_variant();}
if(part=="buttons_light_path")intersection(){tbh07_light_columns(43.61,1.98);translate([0,0,43.6])tbh07_lid_variant();}
if(part=="buttons_light_cap_rest")intersection(){tbh07_light_columns(46.81,.1);tbh07_caps_at(0);}
if(part=="buttons_light_cap_pressed")intersection(){tbh07_light_columns(45.61,.1);tbh07_caps_at(1.2);}
if(part=="buttons_guide")translate([-10,-10,0])tbh07_guide_variant();
if(part=="buttons_guide_left")translate([-10,-10,0])intersection(){tbh07_guide_variant();cube([168.9,192.4,2]);}
if(part=="buttons_guide_right")translate([-169.1,-10,0])intersection(){tbh07_guide_variant();translate([169.1,0,0])cube([338,192.4,2]);}

module tbh07_seat_probes(z){for(i=tbh07_instances)tbh07_pose(i)for(p=tbh07_boards[i[1]][2])translate([p[0]+1.6,p[1]-.15,z])cube([.3,.3,.1]);}
if(part=="buttons_down_retention")intersection(){translate([0,0,-.2])tbh07_boards_installed();translate([0,0,42.2])tbh07_guide_variant();tbh07_seat_probes(42.75);}
if(part=="buttons_up_retention")intersection(){translate([0,0,.3])tbh07_boards_installed();translate([0,0,43.6])tbh07_lid_variant();tbh07_seat_probes(43.65);}
module tbh07_guide_change_mask(){for(i=tbh07_instances)tbh07_pose(i){translate([0,0,.69])linear_extrude(1)offset(delta=.21)tbh07_shape(i[1]);for(p=tbh07_boards[i[1]][3])translate([p[0],p[1],-.1])cylinder(d=2.02,h=2);}}
if(part=="buttons_guide_preservation")difference(){union(){difference(){tbh07_guide_variant();tbh06_guide_variant();}difference(){tbh06_guide_variant();tbh07_guide_variant();}}tbh07_guide_change_mask();}

module tbh07_preservation_section(z){linear_extrude(1)difference(){union(){difference(){projection(cut=true)translate([0,0,-z])tbh07_guide_variant();projection(cut=true)translate([0,0,-z])tbh06_guide_variant();}difference(){projection(cut=true)translate([0,0,-z])tbh06_guide_variant();projection(cut=true)translate([0,0,-z])tbh07_guide_variant();}}projection(cut=true)translate([0,0,-z])tbh07_guide_change_mask();}}
if(part=="buttons_guide_preservation_low")tbh07_preservation_section(.35);
if(part=="buttons_guide_preservation_high")tbh07_preservation_section(1.05);
