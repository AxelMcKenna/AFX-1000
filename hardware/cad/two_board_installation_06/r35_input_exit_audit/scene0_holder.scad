// Delegate the exact current holder, preserving its installed pose and parameters.
include <../../two_board_print_01/housing.scad>
module scene0_holder_owned(){for(b=buttons)if(b[0]=="scene_0")button_pose(b)switch_holder(b);}
