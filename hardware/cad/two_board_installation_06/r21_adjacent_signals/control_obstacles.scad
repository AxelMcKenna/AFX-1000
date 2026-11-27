// Same frozen housing parameter scope and delegates as controls workflow adapter.
include <../../two_board_print_01/housing.scad>
module adjacent_controls_motion(){for(b=buttons)translate([b[5],b[6],43.6])rotate([0,0,b[7]])key_sweep(b);}
module adjacent_controls_clips(){for(b=buttons)button_pose(b)translate([0,0,clip_bottom])retaining_clip();}
module adjacent_controls_mechanisms(){for(b=buttons)button_pose(b)mechanism(b,0);}
module adjacent_controls_obstacles(){adjacent_controls_motion();adjacent_controls_clips();adjacent_controls_mechanisms();}
