// TBH01 — current two-board unpowered fit housing. All coordinates in mm.
include <captured.scad>
include <../a11/generated/button-fixture.scad>
include <../a11/controls.scad>
use <../a11/mechanisms.scad>
$fn=64;
part="shell";
W=338; D=192.4; H=43.6; wall=2.8; floor_t=2.8;
body_width=W;body_depth=D;panel_z=H;panel_thickness=2;
fasteners=lid_fasteners;
disconnect_guide_relief=[151,147.5,24];
module rounded_rect(w,d,r) { hull() for(x=[r,w-r],y=[r,d-r]) translate([x,y]) circle(r=r); }
module sector(ri,ro,a,b) { polygon(concat([for(i=[0:32]) [ro*cos(a+(b-a)*i/32),ro*sin(a+(b-a)*i/32)]],[for(i=[32:-1:0]) [ri*cos(a+(b-a)*i/32),ri*sin(a+(b-a)*i/32)]])); }
module aperture(c) { translate([c[2],c[3]]) if(c[1]=="knob") circle(d=9.5); else if(c[1]=="sector") sector(c[4],c[5],c[6],c[7]); else square([c[4],c[5]],center=true); }
module nut(af,h) { cylinder(d=af/cos(30),h=h,$fn=6); }
module pcb_posts() { for(m=mounts) translate([m[1],m[2],floor_t-.1]) cylinder(d=6.4,h=m[3]-floor_t+.1); }
module touch_posts() { for(m=touch_mounts) translate([m[0],m[1],floor_t-.1]) cylinder(d=7.2,h=m[2]-floor_t+.1); }
module lid_posts() { for(p=lid_fasteners) translate([p[0],p[1],0]) cylinder(d=7,h=H); }
function nut_angle(p)=p[0]==169?30:0;
function nut_entry(p)=p[0]<10?[6,p[1]>180?-6:0]:p[0]>330?[-6,p[1]>180?-6:0]:[0,-6];
module lid_nut_slot(p) {
 translate([p[0],p[1],40.6]) {
  // Front corners enter diagonally, clear of BOTH adjoining case walls.
  hull(){rotate([0,0,nut_angle(p)])nut(4.2,1.8);translate(nut_entry(p))rotate([0,0,nut_angle(p)])nut(4.2,1.8);}
 }
}
module lever_posts(){for(x=[306,326],y=[69,102])translate([x,y,floor_t-.1])cylinder(d=9.4,h=14.6-floor_t+.1);}
module lever_installed(){translate([0,0,7.6])lever_bracket();}
module lever_motion(){translate([0,0,7.6])lever_sweep();}
module shell() {
 difference() {
  union() {
   difference() {
    linear_extrude(H) rounded_rect(W,D,7);
    translate([wall,wall,floor_t]) linear_extrude(H) rounded_rect(W-2*wall,D-2*wall,7-wall);
   }
   pcb_posts();touch_posts();lid_posts();lever_posts();
   for(x=[20,318],z=[8,28]) translate([x-3.8,0,z-3.8]) cube([7.6,7,7.6]);
  }
  // Top-open cassette avoids an unsupported 282 mm roof bridge.
  translate([26,-1,3.8]) cube([282,wall+2,H]);
  // Preserve the original connector face at Y=-1.6 with a 2.4 mm plate.
  translate([12,-1,3]) cube([310,1.8,H]);
  for(x=[20,318],z=[8,28]) {
   translate([x,-1,z]) rotate([-90,0,0]) cylinder(d=3.4,h=10);
   translate([x,4.4,z]) rotate([-90,0,0]) nut(5.7,3);
  }
  for(m=mounts) translate([m[1],m[2],-.1]) { cylinder(d=2.4,h=m[3]+.2);nut(4.2,1.9); }
  for(m=touch_mounts) translate([m[0],m[1],-.1]) { cylinder(d=2.4,h=m[2]+.2);nut(4.2,1.9); }
  for(x=[306,326],y=[69,102])translate([x,y,-.1]){cylinder(d=3.4,h=15);nut(5.7,2.5);}
  // Side-loaded nuts have a 1.2 mm retaining roof; they cannot lift with lid.
  for(p=lid_fasteners) {translate([p[0],p[1],35])cylinder(d=2.4,h=10);lid_nut_slot(p);}
 }
}
module lid() {
 difference() {
  union() {
   linear_extrude(2) rounded_rect(W,D,7);
   translate([0,0,-1.2]) linear_extrude(1.3) difference() {
    translate([3.1,3.1]) rounded_rect(W-6.2,D-6.2,3.9);
    translate([4.3,4.3]) rounded_rect(W-8.6,D-8.6,2.7);
    for(p=lid_fasteners) translate(p) circle(d=7.6);
    // Rear plate seats directly under the lid at the original mating plane.
    translate([26,-1]) square([282,6]);
   }
  }
  translate([0,0,-2]) linear_extrude(5) for(c=openings) aperture(c);
  for(p=lid_fasteners) translate([p[0],p[1],-2]) cylinder(d=2.6,h=5);
  mounting_holes(true);
 }
}
module rear_plate() {
 difference() {
  translate([12,-1.6,3]) cube([310,2.4,H-3]);
  for(x=[20,318],z=[8,28]) translate([x,-3,z]) rotate([-90,0,0]) cylinder(d=3.4,h=4);
  for(p=rear_ports) translate([p[2],-3,p[3]]) rotate([-90,0,0])
   if(p[1]=="round") cylinder(d=p[4],h=4);else translate([-p[4]/2,-p[5]/2,0]) cube([p[4],p[5],4]);
  // Wide switch body is behind the smaller actuator; retain 1.9 mm face skin.
  translate([296.8,.3,8.8])cube([10.4,1,5.8]);
 }
}
module box_rows(rows) { for(b=rows) translate([b[0][0],b[0][1],b[1][0]]) cube([b[0][2]-b[0][0],b[0][3]-b[0][1],b[1][1]-b[1][0]]); }
module pcbs(seat_guard=0) { for(b=board_profiles) translate([0,0,b[1]+seat_guard]) linear_extrude(1.6-seat_guard) difference() { polygon(b[0]); for(h=b[2]) translate([h[0],h[1]]) circle(d=h[2]); } }
module coupon() {
 difference() {
  cube([56,24,6]);
  for(i=[0:3]) translate([8+i*13,8,-.1]) {cylinder(d=2.2+i*.1,h=7);nut(4+i*.1,2);}
  for(i=[0:3]) translate([8+i*13,18,2]) nut(4+i*.1,5);
 }
}
module rear_coupon() {
 difference(){cube([110,25,2.4]);
  for(p=[[12,8.2],[29,9.8]])translate([p[0],12,-.1])cylinder(d=p[1],h=3);
  translate([44,5,-.1])cube([10.4,14.2,3]);translate([65,9,-.1])cube([7.2,5.5,3]);
  translate([83,6,-.1])cube([12,8,3]);
 }
}
module lid_nut_coupon(){difference(){union(){cube([18,14,2]);translate([7,7,2])cylinder(d=7,h=10);}translate([7,7,1])cylinder(d=2.4,h=12);translate([7,7,9]){nut(4.2,1.8);translate([0,-2.1,0])cube([6,4.2,1.8]);}}}
// 0.2 mm split seam. Three floor laps register Z; removable plates carry load.
join_ys=[20,90,186];
module shell_join_holes() { for(y=join_ys,x=[159,179]) translate([x,y,-1]) {cylinder(d=3.4,h=3.9);translate([0,0,2])cylinder(d1=3.4,d2=6.8,h=1.8);} }
module floor_laps(clearance=0) {for(y=join_ys)translate([168.8-clearance,y-6-clearance,0])cube([6.2+2*clearance,12+2*clearance,1.2+clearance]);}
module split_shell(left=true) {
 difference(){
  union(){intersection(){shell();translate([left?-1:169.1,-1,-1])cube([left?169.9:170,D+2,H+2]);}if(left)floor_laps();}
  if(!left)floor_laps(.2);shell_join_holes();
 }
}
module floor_join_plate() {
 difference(){translate([-18,-6,0])cube([36,12,4]);for(x=[-10,10])translate([x,0,-.1]){cylinder(d=3.4,h=5);nut(5.7,2.5);}}
}
// Lid bridge locations avoid controls, PCB parts and rear connector bodies.
lid_join_ys=[8,156];
module lid_join_holes() {for(y=lid_join_ys,x=[154,184])translate([x,y,-5])cylinder(d=2.4,h=9);}
module lid_join_bar() {
 difference(){translate([-22,-6,0])cube([44,12,3.6]);for(x=[-15,15])translate([x,0,-.1]){cylinder(d=2.4,h=5);nut(4.2,1.9);}}
}
module guide_current() {
 difference(){guide_plate();for(y=lid_join_ys)translate([146.7,y-6.3,-.1])cube([44.6,12.6,2]);}
}
module split_lid(left=true) {difference(){intersection(){lid();translate([left?-1:169.1,-1,-2])cube([left?169.9:170,D+2,5]);}lid_join_holes();}}
module split_rear(left=true) {difference(){intersection(){rear_plate();translate([left?0:169.1,-3,0])cube([left?168.9:170,5,H+1]);}for(x=[162,174])translate([x,-3,35])rotate([-90,0,0])cylinder(d=2.4,h=5);}}
module rear_join_bar() {difference(){translate([-16,-5,0])cube([32,10,3]);for(x=[-7,5])translate([x,0,-.1]){cylinder(d=2.4,h=4);translate([0,0,1.2])nut(4.2,2);}}}
module holders_installed() {for(b=buttons)button_pose(b) switch_holder(b);}
module guide_installed() {translate([0,0,H-guide_thick])guide_current();}
module lid_bars_installed(){for(y=lid_join_ys)translate([169,y,H-3.6])lid_join_bar();}
module board_heads(){for(m=mounts)translate([m[1],m[2],m[3]+1.6])cylinder(d=4.5,h=2.5);for(m=touch_mounts)translate([m[0],m[1],21.6])cylinder(d=4.5,h=2.5);}
module rear_bar_installed(){translate([169,.8,35])rotate([-90,0,0])rear_join_bar();}
// Printing transforms put the broadest flat face at Z=0.
if(part=="shell") shell();
if(part=="lid") translate([0,D,2]) rotate([180,0,0]) lid();
if(part=="rear_plate") translate([-12, H,1.6]) rotate([90,0,0]) rear_plate();
if(part=="guide") translate([-10,-10,0])guide_current();
if(part=="touch_backer") translate([-70,-120,-(H-1.4)]) touch_backer();
if(part=="coupon") coupon();
if(part=="rear_coupon")rear_coupon();
if(part=="lid_nut_coupon")lid_nut_coupon();
if(part=="lever_bracket")translate([-303,-66,-7])lever_bracket();
if(part=="lever_arm")translate([-305,-78,-14])lever_arm(0);
if(part=="shell_left")split_shell(true);
if(part=="shell_right")translate([-169.1,0,0])split_shell(false);
if(part=="lid_left")translate([0,D,2])rotate([180,0,0])split_lid(true);
if(part=="lid_right")translate([-169.1,D,2])rotate([180,0,0])split_lid(false);
if(part=="guide_left")translate([-10,-10,0])intersection(){guide_current();cube([168.9,D,2]);}
if(part=="guide_right")translate([-169.1,-10,0])intersection(){guide_current();translate([169.1,0,0])cube([W,D,2]);}
if(part=="rear_left")translate([-12,H,1.6])rotate([90,0,0])split_rear(true);
if(part=="rear_right")translate([-169.1,H,1.6])rotate([90,0,0])split_rear(false);
if(part=="floor_join_plate")translate([18,6,0])floor_join_plate();
if(part=="lid_join_bar")translate([22,6,0])lid_join_bar();
if(part=="rear_join_bar")translate([16,5,0])rear_join_bar();
if(part=="pcb_shell_collision") intersection(){shell();pcbs(.01);}
if(part=="component_shell_collision") intersection(){shell();box_rows(component_boxes);}
if(part=="component_lid_collision") intersection(){translate([0,0,H])lid();box_rows(component_boxes);}
if(part=="component_guide_collision")intersection(){guide_installed();box_rows(component_boxes);}
if(part=="component_holder_collision")intersection(){holders_installed();box_rows(component_boxes);}
if(part=="component_join_collision")intersection(){lid_bars_installed();box_rows(component_boxes);}
// At the rear face only, use the retained jack body and switch body/actuator
// plus .2 XY/.36 Z tolerance instead of their larger soldering courtyards.
if(part=="component_rear_collision")intersection(){rear_plate();box_rows(rear_component_boxes);}
if(part=="component_rear_bar_collision")intersection(){rear_bar_installed();box_rows(component_boxes);}
if(part=="component_head_collision")intersection(){board_heads();box_rows(component_boxes);}
if(part=="component_split_collision")intersection(){union(){split_shell(true);split_shell(false);}box_rows(component_boxes);}
if(part=="split_pcb_collision")intersection(){union(){split_shell(true);split_shell(false);}pcbs(.01);}
if(part=="floor_join_post_collision")intersection(){shell_join_holes();pcb_posts();}
if(part=="control_join_collision")intersection(){lid_bars_installed();box_rows(context_boxes);}
if(part=="lever_component_collision")intersection(){union(){lever_installed();lever_motion();}box_rows(component_boxes);}
if(part=="lever_lid_collision")intersection(){lever_motion();translate([0,0,H])lid();}
if(part=="lever_shell_collision")intersection(){lever_motion();shell();}
if(part=="lever_guide_collision")intersection(){lever_motion();guide_installed();}
if(part=="lever_holder_collision")intersection(){lever_motion();holders_installed();}
if(part=="lid_nut_collision")intersection(){shell();for(p=lid_fasteners)translate([p[0],p[1],40.7])rotate([0,0,p[0]==169?30:0])nut(4,1.6);}
if(part=="lid_nut_retention_positive")intersection(){shell();for(p=lid_fasteners)translate([p[0],p[1],41.7])rotate([0,0,p[0]==169?30:0])nut(4,1.6);}
if(part=="split_overlap_collision")intersection(){split_shell(true);split_shell(false);}
if(part=="lid_shell_collision")intersection(){translate([0,0,H+.01])lid();shell();}
if(part=="rear_shell_collision")intersection(){translate([0,-.01,0])rear_plate();shell();}
if(part=="pcb_positive") intersection(){pcbs();translate([32,50,6.8])cube([.2,.2,.2]);}
if(part=="shell_positive") intersection(){shell();translate([100,100,.5])cube([.2,.2,.2]);}
if(part=="assembly_preview") {color("gray")shell();color("green")pcbs();color("orange")box_rows(component_boxes);color("silver")rear_plate();}
