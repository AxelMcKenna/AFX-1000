use <routes.scad>
use <../r21_adjacent_signals/control_obstacles.scad>
use <../r21_adjacent_signals/routes.scad>
use <../r33_touch_flex/flex.scad>
use <clearance.scad>
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
module candidate(){panel_next_inputs();}
if(part=="wires")union(){intersection(){candidate();union(){panel_ground_left_formed();corrected_ground_scene_links();unaffected_right_ground();panel_scene_signal();panel_adjacent_signals();}}}
if(part=="structure")intersection(){candidate();union(){shell();holders_installed();lever_installed();rear_plate();board_heads();tbh04_display_installed();tbh04_fasteners();}}
if(part=="receiving")intersection(){candidate();union(){panel_ground_allocations();tbh10_panel_mates();tbh04_selector_wiring();ground_splice_support();panel_ground_right_splice();release_keyed_guide();release_supported_selectors();}}
if(part=="positive")candidate();

if(part=="controls")intersection(){candidate();adjacent_controls_obstacles();}
if(part=="controls_clearance")intersection(){next_input_control_clearance();adjacent_controls_obstacles();}

if(part=="future_touch")intersection(){candidate();touch_flex_wires();}
