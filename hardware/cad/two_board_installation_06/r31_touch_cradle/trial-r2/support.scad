// Receiving-box cradle study: does not invent JST bearing or latch details.
module touch_cradle(){difference(){union(){
 translate([164,113,9.5])cylinder(d=7.2,h=11,$fn=64);
 translate([161,108.4,9.5])cube([6,4.6,3]);
 // Positive edge key with nominal0.1 mm edge gap; copper keepout unresolved.
 translate([161,107,7.7])cube([6,1.4,4.8]);
 hull(){translate([164,113,18.5])cylinder(d=5,h=2,$fn=32);translate([177.5,116,18.5])cylinder(d=5,h=2,$fn=32);}
 translate([172,113.5,20])cube([11,23,1.5]);
 translate([170.5,113.5,20])cube([1.5,9,4.5]);translate([183,113.5,20])cube([1.5,9,4.5]);
 }
 translate([164,113,9.4])cylinder(d=2.4,h=11.3,$fn=64);
 translate([164,113,12.5])cylinder(d=5.4,h=8.2,$fn=64);
 // Strap passes below body via two vertical slots alongside the box.
 translate([170.7,118.4,19.9])cube([1.3,3.2,4.8]);translate([183,118.4,19.9])cube([1.3,3.2,4.8]);
}}
module touch_cradle_pocket_extension(){translate([164,113,-.1])cylinder(d=4.2/cos(30),h=3.9,$fn=6);}
module touch_cradle_fastener(){translate([164,113,0])union(){translate([0,0,.8])cylinder(d=2,h=12,$fn=64);translate([0,0,12.8])cylinder(d=3.8,h=2,$fn=64);translate([0,0,12.5])difference(){cylinder(d=5,h=.3,$fn=64);translate([0,0,-.01])cylinder(d=2.2,h=.32,$fn=64);}translate([0,0,2.2])difference(){cylinder(d=4/cos(30),h=1.6,$fn=6);translate([0,0,-.01])cylinder(d=1.6,h=1.62,$fn=64);}}}

// Loose T18R receiving reservation only, reusing r9 measured-part conditions.
module touch_cradle_strap(){union(){difference(){translate([170.8,118.75,18.8])cube([13.4,2.5,14.8]);translate([171.9,118.65,19.9])cube([11.2,2.7,12.6]);}translate([180.1,117.25,15.4])cube([5.5,5.5,3.4]);}}
module touch_cradle_candidate(){touch_cradle();touch_cradle_strap();}
