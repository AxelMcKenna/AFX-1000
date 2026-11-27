// Project receiving cap; manufacturer only provides reference assembly height.
module fan_box(b){translate([b[0],b[1],b[2]])cube([b[3]-b[0],b[4]-b[1],b[5]-b[2]]);}
module captured_fan_connectors(){fan_box([17.55, 171.65, 9.14, 29.45, 179.4, 23.36]);fan_box([15.55, 145.65, 9.14, 27.45, 153.4, 23.36]);}
module conditional_fan_connectors(){fan_box([17.55, 171.65, 9.14, 29.45, 179.4, 20.0]);fan_box([15.55, 145.65, 9.14, 27.45, 153.4, 20.0]);}
module fan_entry_masks(){translate([21.0, 175.0, 18.3])cylinder(r=.98,h=1.70001,$fn=64);translate([23.5, 175.0, 18.3])cylinder(r=.98,h=1.70001,$fn=64);translate([26.0, 175.0, 18.3])cylinder(r=.98,h=1.70001,$fn=64);translate([19.0, 149.0, 18.3])cylinder(r=.98,h=1.70001,$fn=64);translate([21.5, 149.0, 18.3])cylinder(r=.98,h=1.70001,$fn=64);translate([24.0, 149.0, 18.3])cylinder(r=.98,h=1.70001,$fn=64);}
