use <route.scad>
use <../r15_right_ground/right.scad>
use <../r14_left_ground/left.scad>
use <../r12_ground/routes.scad>
use <../r10_interfaces/panel_mates.scad>
use <../../two_board_print_01/housing.scad>
use <../../two_board_controls_04/selectors.scad>
use <../../two_board_controls_04/display.scad>
part="ground";group="all";$fn=64;
if(part=="ground")intersection(){panel_scene_signal();union(){panel_ground_left_formed();panel_ground_right_formed();}}
if(part=="structure")intersection(){panel_scene_signal();union(){shell();holders_installed();lever_installed();rear_plate();board_heads();tbh04_display_installed();tbh04_fasteners();}}
if(part=="receiving")intersection(){panel_scene_signal();union(){panel_ground_allocations();tbh10_panel_mates();tbh04_selector_wiring();}}
if(part=="positive")panel_scene_signal();

module escape(a){for(t=[0:3:87])hull(){for(q=[t,t+3])translate([221+12*(1-cos(q))*cos(a),48.46+12*(1-cos(q))*sin(a),27.04+12*sin(q)])sphere(r=.6,$fn=24);}}
if(part=="escape_study")for(a=[0:30:330])translate([a/30*1000,0,0])intersection(){escape(a);union(){holders_installed();lever_installed();panel_ground_left_formed();panel_ground_right_formed();}}
