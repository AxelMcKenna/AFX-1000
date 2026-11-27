use <routes.scad>
use <../r10_interfaces/panel_mates.scad>
use <../../two_board_print_01/housing.scad>
use <../../two_board_controls_04/selectors.scad>
use <../../two_board_controls_04/display.scad>
part="structure";
$fn=32;
module candidate(){panel_ground_wires();panel_ground_splice();}
if(part=="structure")intersection(){candidate();union(){shell();holders_installed();lever_installed();rear_plate();board_heads();tbh04_selector_brackets();tbh04_selector_pcbs();tbh04_selector_bodies();tbh04_selector_fasteners();}}
if(part=="allocations")intersection(){candidate();panel_ground_allocations();}
if(part=="mates")intersection(){candidate();tbh10_panel_mates();}
if(part=="positive")candidate();
