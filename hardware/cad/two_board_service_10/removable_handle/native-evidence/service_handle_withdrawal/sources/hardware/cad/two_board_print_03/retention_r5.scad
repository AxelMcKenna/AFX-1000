// TBH03 lever retention add-on. Millimetres. Frozen TBH01/r6 housing is unchanged.
include <../two_board_print_01/housing.scad>
module complete_bracket() {
 difference(){lever_bracket();
  // Only widen the axial stop-pocket. Preserve its angular and radial limits.
  for(a=[-.75:.5:35.75])translate([316,82,24])rotate([-a,0,0])
   translate([-3.2,-1.8,-10.3])cube([6.4,3.6,7.6]);
 }
}
module retained_bracket(){difference(){union(){
 difference(){complete_bracket();translate([319.2,60,10])cube([30,50,50]);}
 // Two rails locate the removable bearing cap across Y while permitting X entry.
 for(y=[75,94])translate([323,y-1.2,10])cube([5,2.4,1]);
 }for(y=[69,102])translate([326,y,6])cylinder(d=3.4,h=8,$fn=48);}}
module bracket_world(){translate([0,0,7.6])retained_bracket();}
module rail(a,b,w=2.6){hull(){translate([a[0],a[1],17.6])cylinder(d=w,h=2.4,$fn=24);translate([b[0],b[1],17.6])cylinder(d=w,h=2.4,$fn=24);}}
module guard_body(){difference(){union(){
 for(y=[69,102])translate([326,y,17.6])cylinder(d=8,h=2.4,$fn=48);
 rail([326,69],[333.3,69]);rail([333.3,69],[333.3,76]);
 rail([326,102],[328.8,102]);rail([328.8,102],[328.8,88]);rail([328.8,88],[333.3,88]);
 for(y=[75,86.6])translate([332.3,y,19.8])cube([2,2.4,17.9]);
 translate([332.3,75,25.5])cube([2,14,12.2]);
 }for(y=[69,102])translate([326,y,17])cylinder(d=3.4,h=4,$fn=48);}}
module bearing_cap(){difference(){union(){
 // Explicit right-side solids avoid slicing the old base at a coincident plane.
 difference(){translate([324,74,17.6])cube([3,16,18]);translate([323,82,31.6])rotate([0,90,0])cylinder(d=3.2,h=6,$fn=48);}
 difference(){translate([319.3,69,17.6])cube([1.7,25,13]);translate([318,82,31.6])rotate([0,90,0])cylinder(d=10.4,h=4,$fn=48);}
 translate([319.3,74,17.6])cube([6.7,16,2.4]);
 translate([323,73.6,17.6])cube([5,22,2.4]);
 }for(y=[75,94])translate([318,y-1.3,17.59])cube([20,2.6,1.21]);}}
module guard(){difference(){union(){guard_body();bearing_cap();}for(y=[75,94])translate([318,y-1.3,17.59])cube([20,2.6,1.21]);}}
module shim(left=true,t=.9){difference(){cylinder(d=left?10:8,h=t,$fn=64);translate([0,0,-.1])cylinder(d=left?8.4:3.4,h=t+.2,$fn=64);}}
module shims_world(){translate([308.05,82,31.6])rotate([0,90,0])shim(true);translate([323.05,82,31.6])rotate([0,90,0])shim(false);}
module shaft(x=315.01,l=15.99){translate([x,82,31.6])rotate([0,90,0])cylinder(d=3,h=l,$fn=64);}
module axial_motion(delta=.5){
 // Convex hull across both axial endpoints and adjacent angular poses covers
 // the entire translated stroke, including between sampled 1-degree poses.
 for(index=[0:5],a=[0:1:34])hull()
  for(dx=[-delta,delta],angle=[a,a+1])translate([dx,0,7.6])lever_occupied_piece(index,angle);
}
module guard_clearance(){union(){bearing_cap();minkowski(){guard_body();cube([.4,.4,.4],center=true);}}}
module screw_heads(){for(y=[69,102])translate([326,y,20]){cylinder(d=7,h=.5,$fn=48);translate([0,0,.5])cylinder(d=5.5,h=3,$fn=48);}}
module receiving_coupon(){difference(){cube([49,17,4]);for(i=[0:2])translate([6+i*10,8,-.1])cylinder(d=3.1+i*.1,h=5,$fn=64);translate([39,8,-.1])cylinder(d=8.3,h=5,$fn=64);}}
if(part=="retained_bracket")translate([-303,-66,-7])retained_bracket();
if(part=="pivot_guard")translate([-322,-65,-17.6])guard();
for(i=[7:11]){if(part==str("left_shim_",i))shim(true,i/10);if(part==str("right_shim_",i))shim(false,i/10);}
if(part=="pivot_coupon")receiving_coupon();
if(part=="guard_shell_clearance")intersection(){guard_clearance();shell();}
if(part=="guard_bracket_clearance")intersection(){guard();translate([0,0,-.01])bracket_world();}
if(part=="guard_component_clearance")intersection(){union(){guard_clearance();screw_heads();}box_rows(component_boxes);}
if(part=="guard_controls_clearance")intersection(){guard_clearance();union(){translate([0,0,H])lid();guide_installed();holders_installed();}}
if(part=="guard_motion_clearance")intersection(){guard_clearance();axial_motion();}
if(part=="motion_shell_clearance")intersection(){axial_motion();shell();}
if(part=="motion_components_clearance")intersection(){axial_motion();box_rows(component_boxes);}
if(part=="motion_controls_clearance")intersection(){axial_motion();union(){translate([0,0,H])lid();guide_installed();holders_installed();}}
if(part=="bracket_motion_clearance")intersection(){bracket_world();axial_motion(.3);}
if(part=="shaft_nominal_clearance")intersection(){shaft();union(){bracket_world();translate([0,0,7.6])lever_arm(0);guard();}}
if(part=="shim_nominal_clearance")intersection(){shims_world();union(){bracket_world();translate([0,0,7.6])lever_arm(0);guard();}}
if(part=="tool_guard_clearance")intersection(){guard();translate([320,88,31.6])rotate([-90,0,0])cylinder(d=1.8,h=22,$fn=32);}
if(part=="shaft_guard_retention_positive")intersection(){guard();shaft(316.5,16);}
if(part=="shaft_blind_retention_positive")intersection(){translate([0,0,7.6])lever_arm(0);shaft(314.8,16);}
if(part=="bracket_stop_positive")intersection(){bracket_world();translate([0,0,7.6])lever_arm(38);}

// Bench assembly: cap absent, rotor + left shim enter from +X. Per-primitive
// hulls include 0.1 mm occupied reserves and the entire 32 mm translation.
module rotor_insertion(){
 for(index=[0:5])hull()for(dx=[0,32])translate([dx,0,7.6])lever_occupied_piece(index,0);
 hull()for(dx=[0,32])translate([308.05+dx,82,31.6])rotate([0,90,0])shim(true);
}
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

module cap_insertion(){cap_sweep_constructed();}
if(part=="rotor_insertion_clearance")intersection(){rotor_insertion();bracket_world();}
if(part=="cap_insertion_clearance")intersection(){cap_insertion();union(){translate([0,0,-.01])bracket_world();translate([0,0,7.6])lever_arm(0);shims_world();shaft();}}

if(part=="cap_sweep_containment")difference(){union()for(dx=[0,8,16,24,32])translate([dx,0,0])guard();cap_sweep_constructed();}

if(part=="bracket_negative_stop_positive")intersection(){bracket_world();translate([0,0,7.6])lever_arm(-3);}
