// Additional expanded-route check against frozen lid, guide and join-bar source geometry.
use <clearance.scad>
include <../../two_board_print_01/housing.scad>
use <../../two_board_controls_04/display.scad>
part="lid_guide";group="all";$fn=64;
if(part=="lid_guide")intersection(){isolate_upper_control_clearance();union(){translate([0,0,H])tbh04_lid_variant();translate([0,0,H-guide_thick])tbh04_guide_variant();lid_bars_installed();}}
