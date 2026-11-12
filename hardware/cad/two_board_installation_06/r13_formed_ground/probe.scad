use <exits.scad>
use <../r12_ground/routes.scad>
use <../r10_interfaces/panel_mates.scad>
use <../../two_board_print_01/housing.scad>
use <../../two_board_controls_04/selectors.scad>
part="structure";exit_angle=0;group="all";$fn=32;
module candidate(){if(group=="D_J2002_split"){panel_ground_selected_exits();}else if(group=="D_J2002"){panel_ground_exit_D_J2002_15(exit_angle);panel_ground_exit_D_J2002_16(exit_angle);}else panel_ground_formed_exits(exit_angle);}
if(part=="structure")intersection(){candidate();union(){shell();holders_installed();lever_installed();rear_plate();board_heads();tbh04_selector_brackets();tbh04_selector_pcbs();tbh04_selector_bodies();tbh04_selector_fasteners();}}
if(part=="allocations")intersection(){candidate();panel_ground_allocations();}
if(part=="mates")intersection(){candidate();tbh10_panel_mates();}
if(part=="positive")candidate();
