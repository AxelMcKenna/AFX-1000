// Explicit PTV09A-6, 25mm shaft receiving alternative; detent procurement gate remains.
include <../../two_board_print_01/captured.scad>
use <../../a11/controls.scad>
$fn=96;part="knob16";
module tbh04_pot_knob(d,h){difference(){
 cylinder(d=d,h=max(h,15.5));
 for(a=[0:360/32:359])rotate([0,0,a])translate([d/2,0,.8])cylinder(d=.8,h=max(h,15.5)-1.6,$fn=12);
 translate([0,0,-.1])cylinder(d=6.2,h=13.1);
 translate([0,0,-.1])cylinder(d=10,h=1.1);
 // M3 tapped pilot engages the flat on the selected25mm shaft.
 translate([0,0,6])rotate([0,90,0])cylinder(d=2.5,h=d/2+1);
 translate([6,0,6])rotate([0,90,0])cylinder(d=4,h=d/2);
 translate([-.45,-d/2+1,max(h,15.5)-.5])cube([.9,d*.32,.6]);
}}
module tbh04_pot_knobs_installed(){for(k=knobs)translate([k[1],k[2],48.4])tbh04_pot_knob(k[3],k[4]);}
// Datasheet page3: L measured from rear datum; bushing shoulder is8.4 forward.
module tbh04_pot_shafts_max(){for(k=knobs)translate([k[1],k[2],43.6]){cylinder(d=9,h=5);cylinder(d=6,h=17.1);}}
module tbh04_pot_panel_hardware(){for(k=knobs)translate([k[1],k[2],45.6]){difference(){cylinder(d=16,h=.4);translate([0,0,-.1])cylinder(d=9.1,h=.6);}translate([0,0,.4])difference(){cylinder(d=11.5/cos(30),h=2.2,$fn=6);translate([0,0,-.1])cylinder(d=9,h=2.4);}}}
if(part=="pot_knob_clearance")intersection(){tbh04_pot_knobs_installed();union(){tbh04_pot_shafts_max();tbh04_pot_panel_hardware();}}
if(part=="knob16")tbh04_pot_knob(16,13);
if(part=="knob17")tbh04_pot_knob(17,15);
if(part=="knob29")tbh04_pot_knob(29,18);
if(part=="knob32")tbh04_pot_knob(32,18);
