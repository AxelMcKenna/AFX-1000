// Complete inherited scope for the unchanged key geometry and travel.
include <../../two_board_print_01/housing.scad>
module tbh07_caps_at(p=0){for(b=buttons)if(b[0]!="tap"&&b[0]!="nudge_down"&&b[0]!="nudge_up"&&b[0]!="bank")translate([b[5],b[6],43.6-p])rotate([0,0,b[7]])key(b);}
