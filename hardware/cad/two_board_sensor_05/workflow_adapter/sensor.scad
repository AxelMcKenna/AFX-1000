// Thin, zero-argument exports of frozen sensor/lever geometry in housing coordinates.
// Use these atomic roles once. Do not also instantiate tbh05_installed().
use <../carrier.scad>
use <../population.scad>
use <../spring.scad>
use <../harness_mate_clearance/route.scad>
$fn=64;
module sensor_fixture(){carrier_complete();sensor_cap();sensor_screws();cap_screws();}
module sensor_substrate(){sensor_board();}
module sensor_population(){actual_population();}
module sensor_harness(){tbh05_harness_complete();}
module sensor_lever_bracket(){spring_bracket_world();}
module sensor_lever_guard(){guard();}
module sensor_lever_motion(){spring_arm_sweep(.5);}
module sensor_spring_motion(){spring_installed_envelope();}

module sensor_lever_nominal(){translate([0,0,7.6])lever_arm_spring(0);}
module sensor_pivot_shims(){shims_world();}
module sensor_pivot_shaft(){shaft();}
module sensor_right_screw_heads(){screw_heads();}
module sensor_spring_pins_nominal(){fixed_pin();moving_pin(0);}
module sensor_spring_body_nominal(){spring_body_at(0);}
