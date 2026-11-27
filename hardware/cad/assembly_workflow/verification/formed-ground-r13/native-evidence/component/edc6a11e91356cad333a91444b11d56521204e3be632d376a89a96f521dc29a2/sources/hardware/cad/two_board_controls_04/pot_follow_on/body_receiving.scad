// Explicit receiving allocation, NOT a supplier-certified maximum envelope.
// Extends the old16x16 pot reserve to the real bushing shoulder atZ43.6.
include <../../two_board_print_01/captured.scad>
use <../../two_board_print_01/housing.scad>
use <../button_follow_on/buttons.scad>
use <../ring_follow_on/ring.scad>
use <../connected_guide.scad>
use <../led_follow_on/button_motion.scad>
use <knobs.scad>
$fn=96;part="pot_body_carriers";
module tbh04_pot_body_receiving(guard=0){for(k=knobs)translate([k[1]-8,k[2]-8,29.1])cube([16,16,14.5-guard]);}
if(part=="pot_body_carriers")intersection(){tbh04_pot_body_receiving();union(){tbh07_installed();tbh07_others();}}
if(part=="pot_body_buttons")intersection(){tbh04_pot_body_receiving();tbh05_button_motion_native();}
if(part=="pot_body_mainboard_housing")intersection(){tbh04_pot_body_receiving();union(){box_rows(component_boxes);pcbs();shell();rear_plate();holders_installed();lid_bars_installed();board_heads();}}
if(part=="pot_body_guide")intersection(){tbh04_pot_body_receiving();translate([0,0,42.2])tbh07_connected_guide_variant();}
if(part=="pot_body_lid")intersection(){tbh04_pot_body_receiving(.01);translate([0,0,43.6])tbh06_lid_variant();}
if(part=="pot_panel_hardware_carriers")intersection(){union(){tbh04_pot_panel_hardware();tbh04_pot_shafts_max();}union(){tbh07_installed();tbh07_others();}}
