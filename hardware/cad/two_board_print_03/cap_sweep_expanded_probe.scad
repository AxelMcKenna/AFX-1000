// Controlled diagnostic: expand swept occupation by an explicit 0.001 mm
// on each outer surface and shrink receiving holes/channels by the same amount.
// This is stricter collision geometry, not an epsilon-volume acceptance rule.
include <retention.scad>
module cap_sweep_constructed(travel=32,e=.001){difference(){union(){
 // Foot pads and the five convex connecting rails.
 for(y=[69,102])hull()for(dx=[0,travel])translate([326+dx,y,17.6-e])cylinder(d=8+2*e,h=2.4+2*e,$fn=48);
 for(pair=[[[326,69],[333.3,69]],[[333.3,69],[333.3,76]],[[326,102],[328.8,102]],[[328.8,102],[328.8,88]],[[328.8,88],[333.3,88]]])
  hull()for(dx=[0,travel],p=pair)translate([p[0]+dx,p[1],17.6-e])cylinder(d=2.6+2*e,h=2.4+2*e,$fn=24);
 for(y=[75,86.6])translate([332.3-e,y-e,19.8-e])cube([2+travel+2*e,2.4+2*e,17.9+2*e]);
 translate([332.3-e,75-e,25.5-e])cube([2+travel+2*e,14+2*e,12.2+2*e]);
 // Right wall: constant through bore on X, retained through entire sweep.
 difference(){translate([324-e,74-e,17.6-e])cube([3+travel+2*e,16+2*e,18+2*e]);translate([323,82,31.6])rotate([0,90,0])cylinder(d=3.2-2*e,h=5+travel,$fn=48);}
 // Right stop-block slice begins beyond the widened tab pocket at X319.2.
 difference(){translate([319.3-e,69-e,17.6-e])cube([1.7+travel+2*e,25+2*e,13+2*e]);translate([318,82,31.6])rotate([0,90,0])cylinder(d=10.4-2*e,h=4+travel,$fn=48);}
 translate([319.3-e,74-e,17.6-e])cube([6.7+travel+2*e,16+2*e,2.4+2*e]);
 translate([323-e,73.6-e,17.6-e])cube([5+travel+2*e,22+2*e,2.4+2*e]);
 }for(y=[75,94])translate([318+e,y-1.3+e,17.59+e])cube([20+travel-2*e,2.6-2*e,1.21-2*e]);}}

if(part=="cap_path_collision")intersection(){cap_sweep_constructed();union(){translate([0,0,-.01])bracket_world();translate([0,0,7.6])lever_arm(0);shims_world();shaft();}}
if(part=="cap_path_containment")difference(){union()for(dx=[0,8,16,24,32])translate([dx,0,0])guard();cap_sweep_constructed();}
