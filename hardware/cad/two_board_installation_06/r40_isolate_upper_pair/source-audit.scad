// Full expanded route against ORIGINAL unrelieved controls: no r36 channel reliance.
use <clearance.scad>
use <../r21_adjacent_signals/control_obstacles.scad>
part="original_controls";group="all";$fn=64;
if(part=="original_controls")intersection(){isolate_upper_control_clearance();adjacent_controls_obstacles();}
