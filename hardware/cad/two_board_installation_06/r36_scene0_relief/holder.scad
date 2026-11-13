// Source-delegating candidate: no frozen housing/button files are modified.
include <../../two_board_print_01/housing.scad>
use <exits.scad>
module scene0_original_holder(){for(b=buttons)if(b[0]=="scene_0")button_pose(b)switch_holder(b);}
module scene0_relieved_holder(){difference(){scene0_original_holder();scene0_source_channel();}}
module scene0_relieved_mechanism(){for(b=buttons)if(b[0]=="scene_0")difference(){button_pose(b)mechanism(b,0);scene0_source_channel();}}
module scene0_other_parts_guard(){for(b=buttons)if(b[0]=="scene_0")button_pose(b){
 switch_reference(0);
 translate([0,0,clip_bottom])retaining_clip();
 key_sweep(b);
 // Enclose every spring/puck/stem position by retained fixture dimensions.
 translate([0,0,-board_drop+switch_case-travel])cylinder(r=max(stem_d,spring_od,puck_d)/2+.1,h=board_drop+cap_under+cap_thick-switch_case+travel);
}}
module scene0_mount_posts_guard(){for(b=buttons)if(b[0]=="scene_0")button_pose(b)for(p=b[8])translate([p[0],p[1],-board_drop-1.6])cylinder(d=4.2,h=board_drop+1.6-guide_thick);}
module scene0_bearing_layer_guard(){for(b=buttons)if(b[0]=="scene_0")button_pose(b)translate([-3,-3,-board_drop-.5])cube([6,6,.5]);}
module scene0_input_lead_bores_guard(){for(b=buttons)if(b[0]=="scene_0")button_pose(b)for(x=[-3.25,3.25],y=[-2.25,2.25])translate([x,y,-board_drop-1.7])cylinder(d=1.2,h=1.8);}
module scene0_relief_removed(){intersection(){scene0_original_holder();scene0_source_channel();}}
