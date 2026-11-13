// Only scene0 plastic changes; all 29 frozen poses and nonplastic parts remain.
include <../../two_board_print_01/housing.scad>
use <../r36_scene0_relief/exits.scad>
use <../r21_adjacent_signals/control_obstacles.scad>
module panel_r37_button_holders(){for(b=buttons)if(b[0]=="scene_0")difference(){button_pose(b)switch_holder(b);scene0_source_channel();}else button_pose(b)switch_holder(b);}
module panel_r37_button_mechanisms(){for(b=buttons)if(b[0]=="scene_0")difference(){button_pose(b)mechanism(b,0);scene0_source_channel();}else button_pose(b)mechanism(b,0);}
module panel_r37_control_obstacles(){adjacent_controls_motion();adjacent_controls_clips();panel_r37_button_mechanisms();}
