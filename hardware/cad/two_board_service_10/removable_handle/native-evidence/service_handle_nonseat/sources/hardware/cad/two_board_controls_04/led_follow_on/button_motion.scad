// Import through the housing's complete parameter scope, not bare controls.scad.
include <../../two_board_print_01/housing.scad>
module tbh05_button_motion_native(){for(b=buttons)translate([b[5],b[6],43.6])rotate([0,0,b[7]])key_sweep(b);}
