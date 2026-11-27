use <module.scad>
include <../../two_board_print_01/housing.scad>
part="positive";
module current_posts(){difference(){touch_posts();for(m=touch_mounts)translate([m[0],m[1],-.1]){cylinder(d=2.4,h=m[2]+.2);nut(4.2,1.9);}}}
module current_touch_heads(){for(m=touch_mounts)translate([m[0],m[1],21.6])cylinder(d=4.5,h=2.5);}
if(part=="positive")touch_c3_receiving();
if(part=="posts_components")intersection(){current_posts();union(){touch_c3_components();touch_c3_tails();}}
if(part=="heads_components")intersection(){current_touch_heads();union(){touch_c3_components();touch_c3_tails();}}
// Post/board exact seat plane is intentionally not discarded by this raw witness.
if(part=="posts_board")intersection(){current_posts();touch_c3_board();}
if(part=="old_box_witness")intersection(){current_posts();translate([82,158,17])cube([53.848,21.844,11]);}
