// Single controlled probe replacing failed Nef/Minkowski operation.
// All moving geometry is swept along +X. Bore and rail-channel cuts are
// invariant along X. Screw holes may be filled: this only enlarges occupation.
include <retention.scad>
module cap_sweep_constructed(travel=32){difference(){union(){
 // Foot pads and the five convex connecting rails.
 for(y=[69,102])hull()for(dx=[0,travel])translate([326+dx,y,17.6])cylinder(d=8,h=2.4,$fn=48);
 for(pair=[[[326,69],[333.3,69]],[[333.3,69],[333.3,76]],[[326,102],[328.8,102]],[[328.8,102],[328.8,88]],[[328.8,88],[333.3,88]]])
  hull()for(dx=[0,travel])translate([dx,0,0])rail(pair[0],pair[1]);
 for(y=[75,86.6])translate([332.3,y,19.8])cube([2+travel,2.4,17.9]);
 translate([332.3,75,25.5])cube([2+travel,14,12.2]);
 // Right wall: constant through bore on X, retained through entire sweep.
 difference(){translate([324,74,17.6])cube([3+travel,16,18]);translate([323,82,31.6])rotate([0,90,0])cylinder(d=3.2,h=5+travel,$fn=48);}
 // Right stop-block slice begins beyond the widened tab pocket at X319.2.
 difference(){translate([319.3,69,17.6])cube([1.7+travel,25,13]);translate([318,82,31.6])rotate([0,90,0])cylinder(d=10.4,h=4+travel,$fn=48);}
 translate([319.3,74,17.6])cube([6.7+travel,16,2.4]);
 translate([323,73.6,17.6])cube([5+travel,22,2.4]);
 }for(y=[75,94])translate([318,y-1.3,17.59])cube([20+travel,2.6,1.21]);}}
if(part=="cap_insertion_probe")union(){
 intersection(){cap_sweep_constructed();union(){translate([0,0,-.01])bracket_world();translate([0,0,7.6])lever_arm(0);shims_world();shaft();}}
 // Containment checks detect transcription errors at intermediate/end poses.
 difference(){union()for(dx=[0,8,16,24,32])translate([dx,0,0])guard();cap_sweep_constructed();}
}
