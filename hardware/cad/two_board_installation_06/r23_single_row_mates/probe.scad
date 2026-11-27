use <mates.scad>
use <../r10_interfaces/panel_mates.scad>
use <../r14_left_ground/left.scad>
use <../r22_ground_signal_clearance/bows.scad>
use <../r20_scene_signal/route.scad>
use <../r21_adjacent_signals/routes.scad>
use <../r16_ground_support/support.scad>
use <../r18_selector_key/support.scad>
use <../r17_selector_support/support.scad>
use <../../two_board_print_01/housing.scad>
part="components";group="all";$fn=64;
module other_wires_supports(){panel_ground_left_formed();corrected_ground_scene_links();unaffected_right_ground();panel_scene_signal();panel_adjacent_signals();ground_splice_support();release_keyed_guide();release_supported_selectors();}
if(part=="components")intersection(){single_row_mates();union(){other_captured_allocations();tbh10_panel_mates();}}
if(part=="wires_supports")intersection(){single_row_mates();other_wires_supports();}
if(part=="structure")intersection(){single_row_mates();union(){shell();holders_installed();lever_installed();rear_plate();board_heads();}}
if(part=="withdrawal")intersection(){single_row_withdrawal();union(){other_captured_allocations();tbh10_panel_mates();other_wires_supports();shell();holders_installed();lever_installed();}}
if(part=="positive")single_row_mates();
