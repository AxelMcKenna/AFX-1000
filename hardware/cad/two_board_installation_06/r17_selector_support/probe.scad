use <support.scad>
use <../r16_ground_support/support.scad>
use <../r15_right_ground/right.scad>
use <../r14_left_ground/left.scad>
use <../r12_ground/routes.scad>
use <../../two_board_print_01/housing.scad>
use <../../two_board_controls_04/selectors.scad>
use <../../two_board_controls_04/display.scad>
part="selectors";group="all";$fn=64;
if(part=="selectors")difference(){intersection(){release_wire_guide();release_supported_selectors();}rs_seat_masks();}
if(part=="wires")intersection(){release_wire_guide();union(){panel_ground_left_formed();panel_ground_right_formed();}}
if(part=="receiving")intersection(){release_wire_guide();union(){panel_ground_allocations();tbh04_selector_wiring();ground_splice_support();panel_ground_right_splice();}}
if(part=="structure")intersection(){release_wire_guide();union(){shell();holders_installed();lever_installed();rear_plate();board_heads();tbh04_display_installed();tbh04_fasteners();}}
if(part=="positive")release_wire_guide();
