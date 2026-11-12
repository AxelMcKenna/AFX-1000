use <left.scad>
use <../r12_ground/routes.scad>
use <../r10_interfaces/panel_mates.scad>
use <../../two_board_print_01/housing.scad>
use <../../two_board_controls_04/selectors.scad>
part="structure";group="all";$fn=32;
module candidate(){if(group=="feed")panel_ground_left_feed();else if(group=="links")panel_ground_left_links();else panel_ground_left_formed();}
if(part=="structure")intersection(){candidate();union(){shell();holders_installed();lever_installed();rear_plate();board_heads();tbh04_selector_brackets();tbh04_selector_pcbs();tbh04_selector_bodies();tbh04_selector_fasteners();}}
if(part=="allocations")intersection(){candidate();panel_ground_allocations();}
if(part=="mates")intersection(){candidate();tbh10_panel_mates();}
if(part=="positive")candidate();
use <../../two_board_controls_04/display.scad>
if(part=="display")intersection(){candidate();union(){tbh04_display_installed();tbh04_wire_reserve();tbh04_fasteners();}}
