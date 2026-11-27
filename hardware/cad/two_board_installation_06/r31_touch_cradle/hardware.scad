// Conditional H_NEW5 replacement only. Original nut pocket is unchanged.
module touch_cradle_fastener_nominal(){translate([164,113,0])union(){
 translate([0,0,-1.2])cylinder(d=2,h=14,$fn=64);
 translate([0,0,12.8])cylinder(d=3.8,h=2,$fn=64);
 translate([0,0,12.5])difference(){cylinder(d=5,h=.3,$fn=64);translate([0,0,-.01])cylinder(d=2.2,h=.32,$fn=64);}
 translate([0,0,.2])difference(){cylinder(d=4/cos(30),h=1.6,$fn=6);translate([0,0,-.01])cylinder(d=1.6,h=1.62,$fn=64);}
}}
module touch_cradle_upper_hardware_receiving(){translate([164,113,12.2])cylinder(d=5.4,h=2.95,$fn=64);}
module touch_cradle_tip_receiving(){translate([164,113,-1.9])cylinder(d=2.2,h=4,$fn=64);}
