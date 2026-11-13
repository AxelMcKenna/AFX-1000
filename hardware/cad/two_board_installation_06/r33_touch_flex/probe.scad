use <flex.scad>
use <../r31_touch_cradle/support.scad>
use <../r27_touch_host/sensor-source-extract.scad>
use <../r27_touch_host/population.scad>
use <../r21_adjacent_signals/control_obstacles.scad>
use <../r22_ground_signal_clearance/bows.scad>
use <../r14_left_ground/left.scad>
use <../r15_right_ground/right.scad>
use <../r20_scene_signal/route.scad>
use <../r16_ground_support/support.scad>
use <../r18_selector_key/support.scad>
part="positive";
if(part=="positive")touch_flex_wires();
if(part=="sensor")intersection(){touch_flex_wires();tbh05_harness_installed();}
if(part=="population")intersection(){touch_flex_wires();touch_host_other_population();}
if(part=="controls")intersection(){touch_flex_wires();adjacent_controls_obstacles();}
if(part=="ground_supports")intersection(){touch_flex_wires();union(){panel_ground_left_formed();corrected_ground_scene_links();unaffected_right_ground();panel_scene_signal();ground_splice_support();panel_ground_right_splice();release_keyed_guide();}}


if(part=="cradle")intersection(){touch_flex_wires();union(){touch_cradle();touch_cradle_strap();}}
if(part=="mutual")union(){intersection(){touch_flex_TH1(r=.795);touch_flex_TH2(r=.795);}intersection(){touch_flex_TH1(r=.795);touch_flex_TH3(r=.795);}intersection(){touch_flex_TH1(r=.795);touch_flex_TH4(r=.795);}intersection(){touch_flex_TH2(r=.795);touch_flex_TH3(r=.795);}intersection(){touch_flex_TH2(r=.795);touch_flex_TH4(r=.795);}intersection(){touch_flex_TH3(r=.795);touch_flex_TH4(r=.795);}}
