// FF02 PRIVATE same-height metal-lid/perimeter-fin feasibility; no adoption.
include <../../fanless_feasibility/sources/context/hardware/cad/a11/generated/layout.scad>
include <../../fanless_feasibility/sources/context/hardware/cad/a11/housing.scad>
part="lid_with_fins";
module cap_projection(c){translate([c[2],c[3]])if(c[1]=="knob")circle(d=c[4],$fn=96);else if(c[1]=="sector")sector(c[4],c[5],c[6],c[7]);else square([c[4],c[5]],center=true);}
module fin_root(){intersection(){panel_2d();difference(){union(){translate([12,3.5])square([310,2]);translate([12,151.5])square([310,2]);translate([3.5,12])square([2,133]);translate([328.5,12])square([2,133]);}
for(c=caps)offset(r=2,$fn=96)cap_projection(c);
for(p=fasteners)translate(p)circle(r=4.2,$fn=96);
}}}
module fins(){translate([0,0,38])linear_extrude(18)fin_root();}
module lid(){translate([0,0,36])linear_extrude(2)panel_2d();}
if(part=="lid_with_fins")union(){lid();fins();}
if(part=="fins")fins();
// No independent credit for all fin radiation; real shadowing/room view must be solved.
