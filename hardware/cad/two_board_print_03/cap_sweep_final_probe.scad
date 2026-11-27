include <retention_r5.scad>
if(part=="cap_path_collision")intersection(){cap_sweep_constructed();union(){translate([0,0,-.01])bracket_world();translate([0,0,7.6])lever_arm(0);shims_world();shaft();}}
if(part=="cap_path_containment")difference(){union()for(dx=[0,8,16,24,32])translate([dx,0,0])guard();cap_sweep_constructed();}
