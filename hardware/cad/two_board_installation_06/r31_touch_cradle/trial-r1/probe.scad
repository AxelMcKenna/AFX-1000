use <support.scad>
use <../r29_touch_inline/route-draft.scad>
use <../r27_touch_host/population.scad>
use <../r21_adjacent_signals/control_obstacles.scad>
include <../../two_board_print_01/housing.scad>
part="positive";
if(part=="positive")touch_cradle();
if(part=="population")intersection(){touch_cradle();touch_host_other_population();}
if(part=="controls")intersection(){touch_cradle();adjacent_controls_obstacles();}
if(part=="wires")intersection(){touch_cradle();touch_wires();}
if(part=="raw_pcbs")intersection(){touch_cradle();pcbs();}
