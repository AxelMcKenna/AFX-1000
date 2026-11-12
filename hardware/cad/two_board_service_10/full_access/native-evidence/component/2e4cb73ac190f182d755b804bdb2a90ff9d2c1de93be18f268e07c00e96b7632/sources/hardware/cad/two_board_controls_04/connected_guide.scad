// Follow-on correction: remove the unretained center island left by ring relief.
// The potentiometer is independently panel-mounted; this island has no fasteners.
use <ring_follow_on/ring.scad>
use <button_follow_on/buttons.scad>
$fn=96;part="buttons_guide_final";
module tbh04_center_island_mask(){translate([244,78,-.1])cylinder(r=17.8,h=2);}
module tbh06_connected_guide_variant(){difference(){tbh06_guide_variant();tbh04_center_island_mask();}}
module tbh07_connected_guide_variant(){difference(){tbh07_guide_variant();tbh04_center_island_mask();}}
module tbh04_guide_section_preserved(z,buttons=true){linear_extrude(1)difference(){union(){difference(){projection(cut=true)translate([0,0,-z])if(buttons)tbh07_connected_guide_variant();else tbh06_connected_guide_variant();projection(cut=true)translate([0,0,-z])if(buttons)tbh07_guide_variant();else tbh06_guide_variant();}difference(){projection(cut=true)translate([0,0,-z])if(buttons)tbh07_guide_variant();else tbh06_guide_variant();projection(cut=true)translate([0,0,-z])if(buttons)tbh07_connected_guide_variant();else tbh06_connected_guide_variant();}}translate([244,78])circle(r=17.81);}}
if(part=="ring_guide_preservation_final")tbh04_guide_section_preserved(.7,false);
if(part=="buttons_guide_preservation_low_final")tbh04_guide_section_preserved(.35,true);
if(part=="buttons_guide_preservation_high_final")tbh04_guide_section_preserved(1.05,true);
if(part=="buttons_guide_clearance_final")intersection(){union(){translate([0,0,.01])tbh07_boards_installed();tbh07_emitters();tbh07_wires();}translate([0,0,42.2])tbh07_connected_guide_variant();}
if(part=="buttons_down_retention_final")intersection(){translate([0,0,-.2])tbh07_boards_installed();translate([0,0,42.2])tbh07_connected_guide_variant();tbh07_seat_probes(42.75);}
if(part=="ring_guide_final")translate([-10,-10,0])tbh06_connected_guide_variant();
if(part=="buttons_guide_final")translate([-10,-10,0])tbh07_connected_guide_variant();
if(part=="ring_guide_left_final")translate([-10,-10,0])intersection(){tbh06_connected_guide_variant();cube([168.9,192.4,2]);}
if(part=="ring_guide_right_final")translate([-169.1,-10,0])intersection(){tbh06_connected_guide_variant();translate([169.1,0,0])cube([338,192.4,2]);}
if(part=="buttons_guide_left_final")translate([-10,-10,0])intersection(){tbh07_connected_guide_variant();cube([168.9,192.4,2]);}
if(part=="buttons_guide_right_final")translate([-169.1,-10,0])intersection(){tbh07_connected_guide_variant();translate([169.1,0,0])cube([338,192.4,2]);}
