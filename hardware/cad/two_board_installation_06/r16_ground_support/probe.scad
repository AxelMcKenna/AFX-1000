use <support.scad>
use <../r15_right_ground/right.scad>
use <../r14_left_ground/left.scad>
use <../r12_ground/routes.scad>
use <../../two_board_print_01/housing.scad>
use <../../two_board_controls_04/selectors.scad>
use <../../two_board_controls_04/display.scad>
part="selectors";group="all";$fn=64;
module candidate(){ground_splice_support();}
if(part=="selectors")difference(){intersection(){candidate();ground_supported_selectors();}gs_pcb_seat_masks();gs_hardware_seat_masks();}
if(part=="ground_wires")intersection(){candidate();union(){panel_ground_left_formed();panel_ground_right_formed();}}
if(part=="splice_body")intersection(){ground_splice_support_prints();panel_ground_right_splice();}
if(part=="allocations")intersection(){candidate();panel_ground_allocations();}
if(part=="structure")intersection(){candidate();union(){shell();holders_installed();lever_installed();rear_plate();board_heads();tbh04_display_installed();tbh04_fasteners();}}
if(part=="cap_hardware")difference(){intersection(){ground_splice_support_prints();ground_splice_cap_hardware();}gs_hardware_seat_masks();}
if(part=="halves")difference(){intersection(){ground_splice_saddle();ground_splice_cap();}gs_half_seat_masks();}
if(part=="positive")candidate();

if(part=="saddle_positive")ground_splice_saddle();
if(part=="cap_positive")ground_splice_cap();
if(part=="retention")intersection(){ground_splice_support_prints();translate(group=="up"?[0,0,.3]:group=="down"?[0,0,-.3]:group=="left"?[-.3,0,0]:[.3,0,0])panel_ground_right_splice();}
