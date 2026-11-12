include <spring.scad>
module actual_population(){
translate([301.3,78.4,28.900000000000002])cube([1.75,7.2,5.4]);
translate([301.3,75.39999999999999,28.965])cube([1.0,2.8,1.46]);
translate([298.2,77.1,24.200000000000003])cube([3.7,1.8,1.8]);
translate([298.2,79.6,24.200000000000003])cube([3.7,1.8,1.8]);
translate([298.2,82.1,24.200000000000003])cube([3.7,1.8,1.8]);
translate([298.2,84.6,24.200000000000003])cube([3.7,1.8,1.8]);
sensor_wiring_envelope();}
if(part=="population_carrier_clearance")intersection(){actual_population();union(){carrier_complete();sensor_cap();}}
if(part=="population_shell_clearance")intersection(){actual_population();shell();}
if(part=="population_controls_clearance")intersection(){actual_population();union(){translate([0,0,H])lid();guide_installed();holders_installed();}}
if(part=="population_rotor_clearance")intersection(){actual_population();union(){spring_arm_sweep(.5);spring_bracket_world();spring_installed_envelope();}}
