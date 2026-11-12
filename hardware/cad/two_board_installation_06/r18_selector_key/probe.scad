use <support.scad>
use <../r17_selector_support/support.scad>
use <../r16_ground_support/support.scad>
use <../r15_right_ground/right.scad>
use <../r14_left_ground/left.scad>
use <../r12_ground/routes.scad>
use <../../two_board_print_01/housing.scad>
use <../../two_board_controls_04/selectors.scad>
use <../../two_board_controls_04/display.scad>
part="selectors";group="all";$fn=64;
if(part=="selectors")difference(){intersection(){release_keyed_guide();release_supported_selectors();}rs_seat_masks();}
if(part=="wires")intersection(){release_keyed_guide();union(){panel_ground_left_formed();panel_ground_right_formed();}}
if(part=="receiving")intersection(){release_keyed_guide();union(){panel_ground_allocations();tbh04_selector_wiring();ground_splice_support();panel_ground_right_splice();}}
if(part=="structure")intersection(){release_keyed_guide();union(){shell();holders_installed();lever_installed();rear_plate();board_heads();tbh04_display_installed();tbh04_fasteners();}}
if(part=="positive")release_keyed_guide();

if(part=="rotation_stop")intersection(){translate([316,63.5,0])rotate([0,0,group=="cw"?-3:3])translate([-316,-63.5,0])release_keyed_guide();tbh04_selector_pcbs();translate([300,40,38.11])cube([40,40,2]);}
