use <direct-exits.scad>
use <sensor-source-extract.scad>
use <population.scad>
use <../r21_adjacent_signals/control_obstacles.scad>
use <../r22_ground_signal_clearance/bows.scad>
use <../r14_left_ground/left.scad>
use <../r15_right_ground/right.scad>
use <../r20_scene_signal/route.scad>
use <../r16_ground_support/support.scad>
use <../r18_selector_key/support.scad>
part="positive";
if(part=="positive")touch_direct_exits();
if(part=="sensor")intersection(){touch_direct_exits();tbh05_harness_installed();}
if(part=="population")intersection(){touch_direct_exits();touch_host_other_population();}
if(part=="controls")intersection(){touch_direct_exits();adjacent_controls_obstacles();}
if(part=="ground_supports")intersection(){touch_direct_exits();union(){panel_ground_left_formed();corrected_ground_scene_links();unaffected_right_ground();panel_scene_signal();ground_splice_support();panel_ground_right_splice();release_keyed_guide();}}
