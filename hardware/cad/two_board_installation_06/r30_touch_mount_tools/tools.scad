// Custom nonmarring nut support tool; nominal geometry, not a torque tool.
r30_centres=[[130.0871,168.922],[93.0871,168.9352]];
module nut_tool_local(top=3.2,od=3.5,bore=2.4,handle=12){difference(){union(){translate([0,0,-12])cylinder(d=od,h=top+12,$fn=64);translate([0,0,-20])cylinder(d=handle,h=8,$fn=64);}translate([0,0,-20.1])cylinder(d=bore,h=top+20.2,$fn=64);}}
module touch_nut_tools_nominal(){for(p=r30_centres)translate([p[0],p[1],0])nut_tool_local();}
// Tolerance + 0.1 mm lateral registration: outer OD3.6+0.2; bore2.3-0.2.
// Sweeps insertion from below, with maximum tip height from roof4.9 - nut1.35.
module touch_nut_tool_access(){for(p=r30_centres)translate([p[0],p[1],0])difference(){union(){translate([0,0,-32])cylinder(d=3.8,h=35.55,$fn=64);translate([0,0,-40])cylinder(d=12.3,h=28,$fn=64);}translate([0,0,-40.1])cylinder(d=2.1,h=43.75,$fn=64);}}
