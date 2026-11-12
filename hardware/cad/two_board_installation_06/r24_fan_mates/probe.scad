use <mates.scad>
use <../r8/terminal_harness.scad>
part="scoped";$fn=24;
if(part=="original")intersection(){tbh08_harness();captured_fan_connectors();}
if(part=="unmasked")intersection(){tbh08_harness();conditional_fan_connectors();}
if(part=="scoped")difference(){intersection(){tbh08_harness();conditional_fan_connectors();}fan_entry_masks();}
if(part=="wrongmask")difference(){intersection(){tbh08_harness();conditional_fan_connectors();}translate([.5,0,0])fan_entry_masks();}
if(part=="positive")conditional_fan_connectors();
use <harness.scad>
use <../r7/fan_harness.scad>
if(part=="scoped_corrected")difference(){intersection(){reconciled_fan_harness();conditional_fan_connectors();}fan_entry_masks();}
if(part=="unmasked_corrected")intersection(){reconciled_fan_harness();conditional_fan_connectors();}
if(part=="wrongmask_corrected")difference(){intersection(){reconciled_fan_harness();conditional_fan_connectors();}translate([.5,0,0])fan_entry_masks();}
if(part=="prefix_subset")difference(){retained_fan_bundle();union(){tbh06_route_0();tbh06_route_1();}}
if(part=="start_containment")difference(){fanout_start_spheres();retained_fan_bundle();}
if(part=="positive_corrected")reconciled_fan_harness();
