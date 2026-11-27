// Existing housing hardware only. Follow-on controls/sensor/cooling come from registries.
include <../two_board_print_01/captured.scad>
use <../two_board_print_01/housing.scad>
module base_main_pcbs(){pcbs();}
module base_rear_panel(){rear_plate();}
module base_button_holders(){holders_installed();}
module base_lid_bars(){lid_bars_installed();}
module base_board_heads(){
 for(m=mounts)if(m[0]!="D_H2" && m[0]!="D_H5")
  translate([m[1],m[2],m[3]+1.6])cylinder(d=4.5,h=2.5);
 for(m=touch_mounts)translate([m[0],m[1],21.6])cylinder(d=4.5,h=2.5);
}
