// FF01 PRIVATE feasibility prototype; not a fabricated or adopted enclosure.
// Changes only owned artifacts. Kept nominal external footprint334x157 and baseZ-6.2..0.
include <../sources/context/hardware/cad/a11/generated/layout.scad>
include <../sources/context/hardware/cad/a11/housing.scad>
part="bottom";
module exclusions(){
 for(p=[[20, 20], [314, 20], [20, 137], [314, 137]])translate(p)circle(r=12,$fn=96);
 for(p=[[8, 8], [8, 149], [167, 8], [167, 149], [326, 8], [326, 149]])translate(p)circle(r=6,$fn=96);
 for(p=[[166, 113], [166, 133.125]])translate(p)circle(r=5,$fn=96);
}
module fin_footprints(){difference(){union(){for(i=[0:11])translate([12,12+i*(133-3)/11])square([310,3]);}exclusions();}}
module plate_shape(){rounded_rect(334,157,7);}
module bottom(){difference(){union(){translate([0,0,-6.2])linear_extrude(6.2)plate_shape();translate([0,0,-26.2])linear_extrude(20)fin_footprints();}
for(p=[[20, 20], [314, 20], [20, 137], [314, 137]]){translate([p[0],p[1],-6.21])cylinder(d=3.4,h=6.22,$fn=64);translate([p[0],p[1],-1.6])cylinder(d1=3.4,d2=6.6,h=1.61,$fn=64);}
for(p=[[8, 8], [8, 149], [167, 8], [167, 149], [326, 8], [326, 149]]){translate([p[0],p[1],-6.21])cylinder(d=3.4,h=6.22,$fn=64);translate([p[0],p[1],-6.21])cylinder(d1=6.6,d2=3.4,h=1.61,$fn=64);}
for(p=[[166, 113], [166, 133.125]]){translate([p[0],p[1],-6.21])cylinder(d=2.4,h=6.22,$fn=64);translate([p[0],p[1],-6.21])cylinder(d1=4.8,d2=2.4,h=1.21,$fn=64);}
}}
// Exact inherited panel apertures; no new structural/electrical/seam proof.
module lid(){translate([0,0,36])linear_extrude(2)panel_2d();}
if(part=="bottom")bottom();
if(part=="lid")render()lid();
if(part=="assembly"){bottom();lid();}
