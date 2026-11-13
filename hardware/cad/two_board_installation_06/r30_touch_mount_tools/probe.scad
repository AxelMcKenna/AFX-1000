use <tools.scad>
use <../r26_touch_mount/mount.scad>
include <../../two_board_print_01/housing.scad>
part="positive";
module revised_shell(){difference(){shell();touch_nut_pocket_extension();}}
if(part=="positive")touch_nut_tools_nominal();
if(part=="access_positive")touch_nut_tool_access();
if(part=="access_shell")intersection(){touch_nut_tool_access();revised_shell();}
if(part=="nominal_hardware")intersection(){touch_nut_tools_nominal();touch_fastener_nominal();}
