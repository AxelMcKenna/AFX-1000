// Exact selected switches on explicit new breakout PCBs. Installed datums.
include <../two_board_print_01/captured.scad>
include <../a11/generated/button-fixture.scad>
use <../two_board_print_01/housing.scad>
use <display.scad>
$fn=48;part="settings_bracket";
selector_centres=[[307,27],[316,54]];
module tbh04_selector_bracket(){difference(){union(){for(y=[-9.5,9.5])translate([0,y,39.7])cylinder(d=5.6,h=3.9);translate([-9.8,-10.9,42])cube([2.8,21.8,1.6]);for(y=[-10.9,8.1])translate([-9.8,y,42])cube([9.9,2.8,1.6]);}for(y=[-9.5,9.5])translate([0,y,39.6])cylinder(d=2.4,h=4.1);}}
module tbh04_selector_brackets(){for(p=selector_centres)translate([p[0],p[1],0])tbh04_selector_bracket();}
module tbh04_selector_pcbs(){for(p=selector_centres)translate([p[0],p[1],38.1])linear_extrude(1.6)difference(){translate([-8,-11.5])square([16,23]);for(y=[-9.5,9.5])translate([0,y])circle(d=2.4);}}
module tbh04_selector_bodies(){for(i=[0:1])let(p=selector_centres[i],w=i==0?9.4:13.4)translate([p[0]-w/2,p[1]-2,39.7])cube([w,4,3.7]);}
module tbh04_selector_leads(){for(i=[0:1])let(p=selector_centres[i])translate([p[0]-6.8,p[1]-4.2,i==0?36.1:39.65])cube([13.6,8.4,i==0?3.6:.5]);}
module tbh04_selector_wiring(){for(p=selector_centres)for(y=[-5.5,5.5])translate([p[0]-5,p[1]+y-1,34.6])cube([10,2,3.5]);}
module tbh04_selector_fasteners(seat_guard=0){for(p=selector_centres,y=[-9.5,9.5])translate([p[0],p[1]+y,35.6]){cylinder(d=2,h=10);translate([0,0,10])cylinder(d=4.5,h=2.2);translate([0,0,2])cylinder(d=4.5,h=.5-seat_guard);translate([0,0,.4])cylinder(d=4/cos(30),h=1.6,$fn=6);}}
module tbh04_selector_motion(){for(i=[0:1])let(p=selector_centres[i],travel=i==0?2:4)translate([p[0]-travel/2-1.85,p[1]-1.85,43.6])cube([travel+3.7,3.7,2.2]);}
module tbh04_selectors_lid(){difference(){tbh04_lid_variant();for(p=selector_centres,y=[-9.5,9.5])translate([p[0],p[1]+y,-2])cylinder(d=2.4,h=5);}}
module tbh04_selectors_guide(){difference(){tbh04_guide_variant();for(p=selector_centres)translate([p[0]-10.1,p[1]-12.5,-.1])cube([19.1,25,2]);}}
module tbh04_selector_obstacles(){box_rows(component_boxes);pcbs();shell();rear_plate();holders_installed();lid_bars_installed();board_heads();}
if(part=="settings_bracket"||part=="release_bracket")translate([9.8,12.3,-39.7])tbh04_selector_bracket();
if(part=="selector_obstacle_clearance")intersection(){union(){tbh04_selector_brackets();tbh04_selector_pcbs();tbh04_selector_fasteners();tbh04_selector_wiring();tbh04_selector_leads();}tbh04_selector_obstacles();}
if(part=="selector_body_clearance")intersection(){tbh04_selector_brackets();tbh04_selector_bodies();}
if(part=="selector_lead_clearance")intersection(){tbh04_selector_brackets();tbh04_selector_leads();}
if(part=="selector_fastener_clearance")intersection(){union(){tbh04_selector_brackets();tbh04_selector_pcbs();}tbh04_selector_fasteners(.01);}
if(part=="selector_guide_clearance")intersection(){union(){tbh04_selector_brackets();tbh04_selector_pcbs();tbh04_selector_bodies();}translate([0,0,43.6-guide_thick])tbh04_selectors_guide();}
if(part=="selector_lid_clearance")intersection(){union(){tbh04_selector_brackets();tbh04_selector_pcbs();tbh04_selector_bodies();tbh04_selector_motion();}translate([0,0,43.61])tbh04_selectors_lid();}
if(part=="selector_board_up_retention")intersection(){tbh04_selector_brackets();translate([0,0,.5])tbh04_selector_pcbs();}
if(part=="selector_lid")translate([0,192.4,2])rotate([180,0,0])tbh04_selectors_lid();
if(part=="selector_guide")translate([-10,-10,0])tbh04_selectors_guide();
// Split manufacturing variants retain the r6 seam and joint-hole geometry.
module tbh04_selectors_split_lid(left=true){difference(){split_lid(left);for(p=[[160,19],[160,43],[307,17.5],[307,36.5],[316,44.5],[316,63.5]])translate([p[0],p[1],-2])cylinder(d=2.4,h=5);}}
if(part=="selector_lid_left")translate([0,192.4,2])rotate([180,0,0])tbh04_selectors_split_lid(true);
if(part=="selector_lid_right")translate([-169.1,192.4,2])rotate([180,0,0])tbh04_selectors_split_lid(false);
if(part=="selector_guide_left")translate([-10,-10,0])intersection(){tbh04_selectors_guide();cube([168.9,192.4,2]);}
if(part=="selector_guide_right")translate([-169.1,-10,0])intersection(){tbh04_selectors_guide();translate([169.1,0,0])cube([338,192.4,2]);}
