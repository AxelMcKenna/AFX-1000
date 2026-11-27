// TBH06 alternative only: external two-fan intake, opposite-side exhaust.
// Coordinate frame and sealed r6 source unchanged. No thermal release.
include <../../two_board_print_01/captured.scad>
use <../../two_board_print_01/housing.scad>
use <../../two_board_print_03/retention_r5.scad>
$fn=64;
part="shell_variant";
W=338;H=43.6;D=192.4;
tbh06_fan_centres=[45,145];
module tbh06_port(y,x=-1){translate([x,y-18,8])cube([5,36,30]);}
module tbh06_bolt(y,z){translate([-2,y,z])rotate([0,90,0])cylinder(d=3.4,h=9);}
module tbh06_nut(y,z){translate([2.8,y,z])rotate([0,90,0])cylinder(d=6.6,h=2.4,$fn=6);}
module tbh06_mounting_holes(){for(c=tbh06_fan_centres,y=[c-26.5,c+26.5],z=[8,38])tbh06_bolt(y,z);}
module tbh06_shell_variant(){difference(){shell();for(y=tbh06_fan_centres){tbh06_port(y);tbh06_port(y,W-4);}tbh06_mounting_holes();tbh06_exhaust_holes();for(y=tbh06_fan_centres)tbh06_lead_bore(y);for(c=tbh06_fan_centres,yy=[c-16,c+16],z=[6.8,38.8])translate([-1,yy,z])rotate([0,90,0])cylinder(d=4.8,h=5);}}
// Pod fan seat lies outside sealed shell: maximum body 40.5 square ×10.5.
// Body cavity 41.5 square. Axial gap shimmed after measuring actual fan.
module tbh06_pod_core(y=0){difference(){union(){
 translate([-15,y-22.75,.05])cube([15,45.5,45.5]);
 translate([-2,y-30,3])cube([2,60,39.6]);
 }translate([-15.1,y-20.75,2.05])cube([12.1,41.5,41.5]);
 hull(){translate([-3.1,y,22.8])rotate([0,90,0])cylinder(d=36,h=.2);translate([-.1,y-18,8])cube([.2,36,30]);}
 for(yy=[y-26.5,y+26.5],z=[8,38])tbh06_bolt(yy,z);
 for(yy=[y-16,y+16],z=[6.8,38.8])translate([-16,yy,z])rotate([0,90,0])cylinder(d=4.8,h=16);
 for(yy=[y-16,y+16],z=[6.8,38.8])translate([-3.4,yy,z])rotate([0,90,0])cylinder(d=7.8/cos(30),h=3.5,$fn=6);
}}
// Cable bay receives factory lead exit on the +Y edge after fan rotation.
// Slot spans fan depth; no unsupported assumption about axial lead emergence.
module tbh06_lead_bore(y){translate([-3,y+30.25,15])rotate([0,90,0])cylinder(d=8.4,h=7);}
module tbh06_lead_cavity(y){translate([-13,y+20.75,10])cube([11,12.75,32.5]);translate([-15.1,y+23,14])cube([2.2,10.5,24]);}
module tbh06_lead_bridge(y){difference(){translate([-10,y+25,18])cube([8.1,10.5,4]);for(yy=[y+26,y+32.7])translate([-9,yy,17.9])cube([3.2,1.4,4.2]);}}
module tbh06_pod(y=0){difference(){union(){difference(){union(){tbh06_pod_core(y);translate([-15,y+20.75,8])cube([15,14.75,36.5]);}tbh06_lead_cavity(y);translate([-15.1,y+20.2,28])cube([12.3,3,12]);}tbh06_lead_bridge(y);
 for(z=[10,42])translate([-13,y+30, z-2.5])cube([7,5.5,5]);}
 tbh06_lead_bore(y);translate([-1.1,y+30.25,15])rotate([0,90,0])cylinder(d=10.4,h=1.2);
 for(z=[10,42]){translate([-18,y+32.5,z])rotate([0,90,0])cylinder(d=2.4,h=13);translate([-8.4,y+32.5,z])rotate([0,90,0])cylinder(d=4.2/cos(30),h=1.8,$fn=6);}
}}
module tbh06_lead_cap(y=0){difference(){translate([-17,y+20.75,8])cube([2,14.75,36.5]);for(z=[10,42])translate([-18,y+32.5,z])rotate([0,90,0])cylinder(d=2.4,h=4);}}
module tbh06_bushing(y=0){difference(){union(){translate([-1,y+30.25,15])rotate([0,90,0])cylinder(d=8.2,h=4);translate([-1,y+30.25,15])rotate([0,90,0])cylinder(d=10,h=.9);}translate([-1.1,y+30.25,15])rotate([0,90,0])cylinder(d=6.2,h=4.2);translate([-1.01,y+30.25,15])rotate([0,90,0])cylinder(d1=7,d2=6.2,h=.5);translate([2.51,y+30.25,15])rotate([0,90,0])cylinder(d1=6.2,d2=7,h=.5);}}
module tbh06_lead_hardware(){for(y=tbh06_fan_centres,z=[10,42]){translate([-18.6,y+32.5,z])rotate([0,90,0])cylinder(d=4,h=1.6);translate([-17,y+32.5,z])rotate([0,90,0])cylinder(d=2,h=12);translate([-8.3,y+32.5,z])rotate([0,90,0])cylinder(d=4/cos(30),h=1.6,$fn=6);}}
module tbh06_lead_parts(){for(y=tbh06_fan_centres){tbh06_lead_cap(y);tbh06_bushing(y);}tbh06_lead_hardware();}
// Separate tbh06_guard: four M4 fan bolts with floating captive nuts retain body without crediting printed friction.
// Slots need a separately retained fine mesh for finger/wire exclusion.
module tbh06_guard(y=0){difference(){translate([-17,y-22.75,.05])cube([2,45.5,45.5]);
 translate([-18,y,22.8])rotate([0,90,0])cylinder(d=36,h=4);
 for(yy=[y-16,y+16],z=[6.8,38.8])translate([-18,yy,z])rotate([0,90,0])cylinder(d=4.8,h=4);
}}
module tbh06_fans(){for(y=tbh06_fan_centres)difference(){translate([-14,y-20.25,2.55])cube([10.5,40.5,40.5]);for(yy=[y-16,y+16],z=[6.8,38.8])translate([-15,yy,z])rotate([0,90,0])cylinder(d=4,h=13);}}
module tbh06_hardware(){for(c=tbh06_fan_centres,y=[c-26.5,c+26.5],z=[8,38]){translate([-4.5,y,z])rotate([0,90,0])cylinder(d=5.5,h=2.5);translate([-2,y,z])rotate([0,90,0])cylinder(d=3,h=8);tbh06_nut(y,z);}for(c=tbh06_fan_centres,y=[c-16,c+16],z=[6.8,38.8]){translate([-21,y,z])rotate([0,90,0])cylinder(d=7,h=4);translate([-17,y,z])rotate([0,90,0])cylinder(d=4,h=20);translate([-3.3,y,z])rotate([0,90,0])cylinder(d=7/cos(30),h=3.2,$fn=6);}}
// Howard 304 SS woven 10 mesh, .010 inch wire. Exact nominal wire visual.
// Cut 41×41, deburr, retain perimeter between guard and fan frame/shims.
module tbh06_mesh(y=0){difference(){intersection(){translate([-15,y-20.5,2.3])cube([.6,41,41]);union(){for(a=[-10:10]){translate([-14.85,y+a*2.54,0])cylinder(d=.254,h=46,$fn=12);translate([-14.596,y-23,22.8+a*2.54])rotate([-90,0,0])cylinder(d=.254,h=46,$fn=12);}}}for(yy=[y-16,y+16],z=[6.8,38.8])translate([-16,yy,z])rotate([0,90,0])cylinder(d=4.8,h=3);}}
module tbh06_meshes(){for(y=tbh06_fan_centres)tbh06_mesh(y);}
module tbh06_installed(){for(y=tbh06_fan_centres){tbh06_pod(y);tbh06_guard(y);}tbh06_hardware();tbh06_meshes();tbh06_exhausts();tbh06_lead_parts();}
module tbh06_exhaust_holes(){for(c=tbh06_fan_centres,y=[c-20,c+20],z=[6,40])translate([332,y,z])rotate([0,90,0])cylinder(d=2.4,h=11);}
// 44x38 mesh is positively trapped by a 36x30 aperture and four M2 bolts.
module tbh06_exhaust_screen_frame(y=0){difference(){translate([338,y-24,2])cube([3,48,42]);translate([337.9,y-18,8])cube([3.2,36,30]);translate([337.9,y-22.1,3.9])cube([.7,44.2,38.2]);for(yy=[y-20,y+20],z=[6,40])translate([337,yy,z])rotate([0,90,0])cylinder(d=2.4,h=5);}}
module tbh06_exhaust_mesh(y=0){difference(){intersection(){translate([338.01,y-22,4])cube([.58,44,38]);union(){for(a=[-10:10]){translate([338.15,y+a*2.54,0])cylinder(d=.254,h=46,$fn=12);translate([338.404,y-25,23+a*2.54])rotate([-90,0,0])cylinder(d=.254,h=50,$fn=12);}}}for(yy=[y-20,y+20],z=[6,40])translate([337,yy,z])rotate([0,90,0])cylinder(d=2.4,h=5);}}
module tbh06_exhaust_hardware(){for(c=tbh06_fan_centres,y=[c-20,c+20],z=[6,40]){translate([333,y,z])rotate([0,90,0])cylinder(d=2,h=8);translate([341,y,z])rotate([0,90,0])cylinder(d=4,h=1.6);translate([333.6,y,z])rotate([0,90,0])cylinder(d=4/cos(30),h=1.6,$fn=6);}}
module tbh06_exhausts(){for(y=tbh06_fan_centres){tbh06_exhaust_screen_frame(y);tbh06_exhaust_mesh(y);}tbh06_exhaust_hardware();}
if(part=="shell_variant")tbh06_shell_variant();
if(part=="pod")translate([0,30,0])tbh06_pod();
if(part=="guard")translate([0,22.75,0])tbh06_guard();
if(part=="exhaust_frame")translate([-338,24,-2])tbh06_exhaust_screen_frame();
if(part=="assembly"){color("gray")tbh06_shell_variant();color("orange")tbh06_installed();color("blue")tbh06_fans();}
if(part=="hardware_components")intersection(){tbh06_hardware();box_rows(component_boxes);}
if(part=="hardware_controls")intersection(){tbh06_hardware();box_rows(context_boxes);}
if(part=="pod_components")intersection(){tbh06_installed();box_rows(component_boxes);}
if(part=="mesh_fan_clearance")intersection(){tbh06_meshes();tbh06_fans();}
if(part=="fan_pod_clearance")intersection(){tbh06_fans();for(y=tbh06_fan_centres){tbh06_pod(y);tbh06_guard(y);}}
if(part=="shell_components")intersection(){tbh06_shell_variant();box_rows(component_boxes);}
if(part=="positive_control")intersection(){tbh06_installed();translate([-16,23,1])cube([2,2,2]);}

if(part=="mesh_hardware_clearance")intersection(){tbh06_meshes();tbh06_hardware();}

if(part=="exhaust_components")intersection(){tbh06_exhausts();box_rows(component_boxes);}
if(part=="exhaust_controls")intersection(){tbh06_exhausts();box_rows(context_boxes);}
if(part=="exhaust_lever")intersection(){tbh06_exhausts();union(){guard();bracket_world();axial_motion();}}
if(part=="exhaust_mesh_frame")intersection(){for(y=tbh06_fan_centres)tbh06_exhaust_mesh(y);for(y=tbh06_fan_centres)tbh06_exhaust_screen_frame(y);}
if(part=="exhaust_positive")intersection(){for(y=tbh06_fan_centres)tbh06_exhaust_screen_frame(y);translate([338.5,21.5,3])cube([1,1,1]);}

if(part=="lead_cap")translate([17,-20.75,-8])tbh06_lead_cap();
if(part=="lead_bushing")translate([1,-30.25,-10])tbh06_bushing();
if(part=="lead_components")intersection(){tbh06_lead_parts();box_rows(component_boxes);}
if(part=="lead_controls")intersection(){tbh06_lead_parts();box_rows(context_boxes);}
if(part=="lead_fans")intersection(){tbh06_lead_parts();tbh06_fans();}
if(part=="bushing_shell")intersection(){for(y=tbh06_fan_centres)tbh06_bushing(y);tbh06_shell_variant();}
if(part=="bushing_pod")intersection(){for(y=tbh06_fan_centres)tbh06_bushing(y);for(y=tbh06_fan_centres)tbh06_pod(y);}
if(part=="bushing_retention_positive")intersection(){for(y=tbh06_fan_centres)translate([1,0,0])tbh06_bushing(y);tbh06_shell_variant();}

// Loose pre-tightening strap path, 2.5 width x1.1 thickness, received T18R.
module tbh06_tie_paths(){for(y=tbh06_fan_centres){for(yy=[y+26.1,y+32.8])translate([-8.65,yy,10.6])cube([2.5,1.1,12.6]);for(z=[10.6,22.1])translate([-8.65,y+26.1,z])cube([2.5,7.8,1.1]);}}
if(part=="tie_bridge_clearance")intersection(){tbh06_tie_paths();for(y=tbh06_fan_centres)tbh06_lead_bridge(y);}
if(part=="tie_retention_positive")intersection(){translate([1,0,0])tbh06_tie_paths();for(y=tbh06_fan_centres)tbh06_lead_bridge(y);}
