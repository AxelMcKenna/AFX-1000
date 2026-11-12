// Preserve the complete frozen housing parameter scope; imported with use only.
include <../../two_board_print_01/housing.scad>
module controls_keys_delegate(){for(b=buttons)button_pose(b)key(b);}
module controls_switches_delegate(){for(b=buttons)button_pose(b)switch_reference(0);}
module controls_clips_delegate(){for(b=buttons)button_pose(b)translate([0,0,clip_bottom])retaining_clip();}
