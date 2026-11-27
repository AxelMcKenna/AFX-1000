// Cross-workstream assembly checks; candidate interfaces, not a print release.
include <../two_board_sensor_05/population.scad>
use <../two_board_controls_04/display.scad>
use <../two_board_installation_06/r7/fan_harness.scad>
use <../two_board_controls_04/pot_follow_on/knobs.scad>
use <../two_board_controls_04/led_follow_on/button_motion.scad>
use <../two_board_controls_04/led_follow_on/banks.scad>
use <../two_board_controls_04/selectors.scad>
use <../two_board_installation_06/r7/cooling_candidate.scad>

module tbh07_selectors() {
 tbh04_selector_brackets(); tbh04_selector_pcbs();
 tbh04_selector_bodies(); tbh04_selector_leads();
 tbh04_selector_wiring(); tbh04_selector_fasteners();
 tbh04_selector_motion();
}
module tbh07_display() {
 tbh04_display_installed(); tbh04_wire_reserve(); tbh04_fasteners();
}
module tbh07_lid_and_guide() {
 translate([0,0,H])tbh05_bank_meter_lid();
 translate([0,0,H-guide_thick])tbh05_bank_meter_guide();
}
if(part=="sensor_selectors")intersection(){tbh05_installed();tbh07_selectors();}
if(part=="lever_selectors")intersection(){spring_arm_sweep(.5);tbh07_selectors();}
if(part=="display_selectors")intersection(){tbh07_display();tbh07_selectors();}
if(part=="new_controls_cooling")intersection(){
 union(){tbh05_installed();tbh07_selectors();tbh07_display();}
 union(){tbh06_installed();tbh06_fans();}
}
if(part=="sensor_revised_lid")intersection(){tbh05_installed();tbh07_lid_and_guide();}
if(part=="spring_new_controls")intersection(){
 union(){spring_bracket_world();spring_installed_envelope();spring_arm_sweep(.5);}
 union(){tbh07_selectors();tbh07_display();tbh07_lid_and_guide();}
}
if(part=="spring_cooling")intersection(){
 union(){spring_bracket_world();spring_installed_envelope();spring_arm_sweep(.5);}
 union(){tbh06_installed();tbh06_fans();}
}
if(part=="assembly") {
 color("gray")tbh06_shell_variant();
 color("orange")tbh06_installed();
 color("blue")tbh06_fans();
 color("green")pcbs();
 color("yellow")tbh07_display();
 color("cyan")tbh07_selectors();
 color("orange")tbh05_installed();
 color("gray"){spring_bracket_world();guard();}
 color("green")translate([0,0,7.6])lever_arm_spring(0);
}

if(part=="population_latest_controls")intersection(){actual_population();union(){tbh07_selectors();tbh07_display();tbh07_lid_and_guide();}}
if(part=="population_cooling_r7")intersection(){actual_population();union(){tbh06_installed();tbh06_fans();tbh06_shell_variant();}}

if(part=="led_sensor_rotor")intersection(){tbh05_bank_meter_installed();union(){tbh05_installed();actual_population();spring_bracket_world();spring_installed_envelope();spring_arm_sweep(.5);}}
if(part=="led_display_selectors")intersection(){tbh05_bank_meter_installed();union(){tbh07_display();tbh07_selectors();}}
if(part=="led_cooling")intersection(){tbh05_bank_meter_installed();union(){tbh06_installed();tbh06_fans();}}

if(part=="knob_button_motion")intersection(){tbh04_pot_knobs_installed();tbh05_button_motion_native();}
if(part=="knob_addons")intersection(){tbh04_pot_knobs_installed();union(){tbh07_selectors();tbh07_display();tbh05_bank_meter_installed();tbh05_installed();actual_population();tbh06_installed();tbh06_fans();}}
if(part=="knob_lever_motion")intersection(){tbh04_pot_knobs_installed();union(){spring_arm_sweep(.5);spring_bracket_world();spring_installed_envelope();}}

if(part=="fan_harness_addons")intersection(){tbh06_harness();union(){tbh07_selectors();tbh07_display();tbh05_bank_meter_installed();tbh05_installed();actual_population();spring_bracket_world();spring_installed_envelope();spring_arm_sweep(.5);tbh04_pot_knobs_installed();}}
if(part=="fan_harness_lid_guide")intersection(){tbh06_harness();tbh07_lid_and_guide();}
