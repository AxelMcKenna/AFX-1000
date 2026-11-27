// Print-first kit. Actual r6 interfaces, no changes to the housing.
include <../two_board_print_01/housing.scad>
module corner_shell(){
 union(){
  // Overlap the sacrificial base by 0.1 to avoid a coplanar boolean seam.
  translate([-1,-1,0])cube([20,20,2.1]);
  translate([0,-174.4,-33.6])intersection(){shell();translate([-.1,174.4,35.6])cube([18.1,18.1,8.1]);}
 }
}
module corner_lid(){
 translate([0,-174.4,0])intersection(){lid();translate([0,174.4,-2])cube([18,18,5]);}
}
module button_panel(){
 difference(){
  cube([36,34,2]);
  translate([18-134,17-22,-.1])linear_extrude(2.2)for(c=openings)if(c[0]=="quantize")aperture(c);
  for(p=buttons[0][8])translate([18+p[0],17+p[1],-.1]){
   cylinder(d=2.4,h=2.2);translate([0,0,1])cylinder(d1=2.4,d2=4.6,h=1.2);
  }
 }
}
module button_guide(){
 difference(){
  cube([36,34,guide_thick]);
  translate([18,17,-.1])linear_extrude(guide_thick+.2)post_profile(stem_d+.4,stem_flat+.2);
  for(p=buttons[0][8])translate([18+p[0],17+p[1],-.1])cylinder(d=2.4,h=guide_thick+.2);
 }
}
module pot_panel(){difference(){cube([32,28,2]);translate([16-18,14-27,-.1])linear_extrude(2.2)for(c=openings)if(c[0]=="input")aperture(c);}}
module corner_nut_sweep(){hull(){translate([3.9,14.1,7.1])nut(4,1.6);translate([9.9,8.1,7.1])nut(4,1.6);}}
if(part=="corner_shell_coupon")corner_shell();
if(part=="corner_lid_coupon")translate([0,18,2])rotate([180,0,0])corner_lid();
if(part=="button_panel_coupon")button_panel();
if(part=="button_guide_coupon")button_guide();
if(part=="pot_panel_coupon")pot_panel();
if(part=="corner_lid_collision")intersection(){corner_shell();translate([0,0,10.01])corner_lid();}
if(part=="corner_nut_insertion_collision")intersection(){corner_shell();corner_nut_sweep();}
if(part=="button_panel_motion_collision")intersection(){button_panel();translate([18,17,0])key_sweep(buttons[0]);}
if(part=="button_guide_motion_collision")intersection(){translate([0,0,-guide_thick])button_guide();translate([18,17,0])key_sweep(buttons[0]);}
if(part=="corner_nut_retention_positive")intersection(){corner_shell();translate([3.9,14.1,8.1])nut(4,1.6);}
if(part=="panel_material_positive")intersection(){button_panel();translate([1,1,.5])cube([.2,.2,.2]);}
