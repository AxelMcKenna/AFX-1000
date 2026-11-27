use <hardware.scad>
use <support.scad>
use <../r27_touch_host/population.scad>
use <../r21_adjacent_signals/control_obstacles.scad>
use <../r29_touch_inline/route-draft.scad>
include <../../two_board_print_01/housing.scad>
part="positive";
module receiver(){touch_cradle_upper_hardware_receiving();touch_cradle_tip_receiving();}
if(part=="positive")touch_cradle_fastener_nominal();
if(part=="receiver_positive")receiver();
if(part=="population")intersection(){receiver();touch_host_other_population();}
if(part=="controls")intersection(){receiver();adjacent_controls_obstacles();}
if(part=="wires")intersection(){receiver();touch_wires();}
if(part=="raw_support")intersection(){touch_cradle_fastener_nominal();touch_cradle();}
if(part=="raw_shell")intersection(){touch_cradle_fastener_nominal();shell();}
