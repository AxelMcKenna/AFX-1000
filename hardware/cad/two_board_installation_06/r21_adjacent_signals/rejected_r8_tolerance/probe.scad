use <routes.scad>
use <control_obstacles.scad>
use <../r22_ground_signal_clearance/bows.scad>
use <../r16_ground_support/support.scad>
use <../r18_selector_key/support.scad>
use <../r17_selector_support/support.scad>
use <../r20_scene_signal/route.scad>
use <../r15_right_ground/right.scad>
use <../r14_left_ground/left.scad>
use <../r12_ground/routes.scad>
use <../r10_interfaces/panel_mates.scad>
use <../../two_board_print_01/housing.scad>
use <../../two_board_controls_04/selectors.scad>
use <../../two_board_controls_04/display.scad>
part="wires";group="all";$fn=64;
module candidate(){if(group=="S02")panel_signal_S02();else if(group=="S03")panel_signal_S03();else panel_adjacent_signals();}
if(part=="wires")union(){intersection(){candidate();union(){panel_ground_left_formed();corrected_ground_scene_links();unaffected_right_ground();panel_scene_signal();}}if(group=="all")intersection(){panel_signal_S02();panel_signal_S03();}}
if(part=="structure")intersection(){candidate();union(){shell();holders_installed();lever_installed();rear_plate();board_heads();tbh04_display_installed();tbh04_fasteners();}}
if(part=="receiving")intersection(){candidate();union(){panel_ground_allocations();tbh10_panel_mates();tbh04_selector_wiring();ground_splice_support();panel_ground_right_splice();release_keyed_guide();release_supported_selectors();}}
if(part=="positive")candidate();

if(part=="controls")intersection(){candidate();adjacent_controls_obstacles();}
