// Additive candidate: apply cuts to current selected shell; never edits frozen shell.
r26_centres=[[130.0871,168.922],[93.0871,168.9352]];
module touch_nut_pocket_extension(){for(p=r26_centres)translate([p[0],p[1],-.1])cylinder(d=4.2/cos(30),h=4.9,$fn=6);}
module touch_fastener_nominal(){for(p=r26_centres)translate([p[0],p[1],0])union(){
 translate([0,0,1.9])cylinder(d=2,h=20,$fn=64);
 translate([0,0,21.9])cylinder(d=3.8,h=2,$fn=64);
 translate([0,0,21.6])difference(){cylinder(d=5,h=.3,$fn=64);translate([0,0,-.01])cylinder(d=2.2,h=.32,$fn=64);}
 translate([0,0,3.2])difference(){cylinder(d=4/cos(30),h=1.6,$fn=6);translate([0,0,-.01])cylinder(d=1.6,h=1.62,$fn=64);}
}}
// Upper hardware receiving envelope includes controlled0.2mm radial registration.
module touch_upper_fastener_receiving(){for(p=r26_centres)translate([p[0],p[1],21.4])cylinder(d=5.4,h=2.75,$fn=64);}
