use <mount.scad>
use <../r25_touch_module/module.scad>
include <../../two_board_print_01/housing.scad>
part="positive";
module revised_posts(){difference(){touch_posts();touch_nut_pocket_extension();for(m=touch_mounts)translate([m[0],m[1],-.1])cylinder(d=2.4,h=m[2]+.2);}}
if(part=="positive")touch_fastener_nominal();
if(part=="revised_posts")revised_posts();
if(part=="upper_components")intersection(){touch_upper_fastener_receiving();union(){touch_c3_components();touch_c3_tails();}}
if(part=="hardware_components")intersection(){touch_fastener_nominal();union(){touch_c3_components();touch_c3_tails();}}
if(part=="raw_hardware_posts")intersection(){touch_fastener_nominal();revised_posts();}
if(part=="removed_material")intersection(){touch_nut_pocket_extension();shell();}
