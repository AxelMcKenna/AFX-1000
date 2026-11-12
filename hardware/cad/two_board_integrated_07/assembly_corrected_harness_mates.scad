// Combined frozen candidates; clearance checks, not fabrication approval.
include <../two_board_sensor_05/population.scad>
use <assembly_ring_terminal.scad>
use <../two_board_installation_06/r8/terminal_harness.scad>
use <../two_board_controls_04/led_follow_on/banks.scad>
use <../two_board_controls_04/button_follow_on/buttons.scad>
use <../two_board_controls_04/connected_guide.scad>
use <../two_board_controls_04/pot_follow_on/body_receiving.scad>
use <../two_board_controls_04/ring_follow_on/ring.scad>
use <../two_board_sensor_05/harness_pot_clearance/route.scad>
use <../two_board_installation_06/r9/cooling_candidate.scad>
module final_lid_guide(){translate([0,0,H])tbh07_lid_variant();translate([0,0,H-guide_thick])tbh07_connected_guide_variant();}
module final_controls(){tbh09_addons();tbh06_ring_installed();tbh07_installed();tbh04_pot_body_receiving();}
module final_cooling(){tbh09_installed();tbh09_fans();}
if(part=="buttons_sensor_motion")intersection(){tbh07_installed();union(){tbh05_installed();actual_population();spring_bracket_world();spring_installed_envelope();spring_arm_sweep(.5);}}
if(part=="buttons_cooling")intersection(){tbh07_installed();final_cooling();}
if(part=="cooling_all_controls")intersection(){final_cooling();final_controls();}
if(part=="internal_fan_controls")intersection(){tbh08_harness();final_controls();}
if(part=="external_fan_controls")intersection(){tbh09_external_leads();final_controls();}
if(part=="internal_fan_guide")intersection(){tbh08_harness();final_lid_guide();}
if(part=="external_fan_guide")intersection(){tbh09_external_leads();final_lid_guide();}
if(part=="sensor_harness_controls")intersection(){tbh05_harness_complete();union(){tbh07_selectors();tbh07_display();tbh05_bank_meter_installed();tbh06_ring_installed();tbh07_installed();tbh04_pot_body_receiving();}}
if(part=="sensor_harness_final_guide")intersection(){tbh05_harness_complete();final_lid_guide();}
if(part=="sensor_harness_cooling")intersection(){tbh05_harness_complete();final_cooling();}
if(part=="sensor_internal_fan")intersection(){tbh05_harness_complete();tbh08_harness();}
if(part=="sensor_external_fan")intersection(){tbh05_harness_complete();tbh09_external_leads();}
if(part=="sensor_final_guide")intersection(){union(){tbh05_installed();actual_population();}final_lid_guide();}
if(part=="lever_final_guide")intersection(){union(){spring_bracket_world();spring_installed_envelope();spring_arm_sweep(.5);}final_lid_guide();}

use <../two_board_installation_06/r10_interfaces/panel_mates.scad>
if(part=="panel_mates_controls")intersection(){tbh10_panel_mates();final_controls();}
if(part=="panel_mates_guide")intersection(){tbh10_panel_mates();final_lid_guide();}
if(part=="panel_mates_sensor_harness")intersection(){tbh10_panel_mates();tbh05_harness_complete();}
if(part=="panel_mates_cooling")intersection(){tbh10_panel_mates();final_cooling();}
if(part=="panel_mates_internal_fan")intersection(){tbh10_panel_mates();tbh08_harness();}
if(part=="panel_mates_external_fan")intersection(){tbh10_panel_mates();tbh09_external_leads();}
