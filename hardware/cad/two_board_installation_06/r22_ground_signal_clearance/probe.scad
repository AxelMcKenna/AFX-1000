use <bows.scad>
use <terminals.scad>
use <../r10_interfaces/panel_mates.scad>
use <../r20_scene_signal/route.scad>
use <../r15_right_ground/right.scad>
use <../r14_left_ground/left.scad>
use <../r12_ground/routes.scad>
use <../r16_ground_support/support.scad>
use <../r18_selector_key/support.scad>
use <../r17_selector_support/support.scad>
use <../../two_board_print_01/housing.scad>
use <../../two_board_controls_04/display.scad>
part="wires";group="all";$fn=64;
module candidate(){corrected_ground_bows();}
if(part=="wires")intersection(){candidate();union(){panel_ground_left_formed();unaffected_right_ground();panel_scene_signal();}}
if(part=="receiving")intersection(){candidate();union(){panel_ground_allocations();tbh10_panel_mates();ground_splice_support();panel_ground_right_splice();release_keyed_guide();release_supported_selectors();}}
if(part=="structure")intersection(){candidate();union(){shell();holders_installed();lever_installed();rear_plate();board_heads();tbh04_display_installed();tbh04_fasteners();}}
if(part=="positive")candidate();

if(part=="terminal_clearance")intersection(){all_signal_terminal_receiving();union(){candidate();unaffected_right_ground();panel_ground_left_formed();}}
if(part=="original_terminal_conflict")intersection(){all_signal_terminal_receiving();union(){panel_ground_right_formed();panel_ground_left_formed();}}
