// Preserve the complete frozen housing parameter scope; imported with use only.
include <../../two_board_print_01/housing.scad>
module controls_keys_delegate(){for(b=buttons)button_pose(b)key(b);}
module controls_switches_delegate(){for(b=buttons)button_pose(b)switch_reference(0);}
module controls_clips_delegate(){for(b=buttons)button_pose(b)translate([0,0,clip_bottom])retaining_clip();}
module controls_mechanisms_delegate(){for(b=buttons)button_pose(b)mechanism(b,0);}
module controls_touch_backer_delegate(){touch_backer();}
module controls_touch_lens_delegate(){translate([74.8,125.8,35.2+panel_z-34])touch_lens();}
