module ap_source_tray(){$fn=96;difference(){union(){
 translate([0,0,-26.2])linear_extrude(1.5)ap_round(334,188.4,7);
 translate([0,0,-24.7])linear_extrude(18.5)difference(){ap_round(334,188.4,7);translate([2,2])ap_round(330,184.4,5);}
 for(p=ap_feet)translate([p[0],p[1],-24.7])difference(){cylinder(d=24,h=16.5);translate([0,0,-.01])cylinder(d=20.5,h=16.52);}
 for(p=ap_feet)translate([p[0],p[1],-8.2])cylinder(d=26,h=2);
 }
 for(p=ap_feet){translate([p[0],p[1],-26.21])cylinder(d=20.5,h=18.01);translate([p[0],p[1],-8.21])cylinder(d=3.4,h=2.02);}
 for(p=ap_fans){translate([p[0],p[1],-26.21])cylinder(d=37.5,h=1.52);for(x=[-16,16],y=[-16,16])translate([p[0]+x,p[1]+y,-26.21])cylinder(d=4.4,h=1.52);}
 translate([34,-.01,-22.2])cube([266,2.02,14]);
}}
