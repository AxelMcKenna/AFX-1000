// AP03 source-derived approach gauges. No aerodynamic guarantee.
module ap3_gap_core(){for(p=ap_fans)translate([p[0]-20,139,-22])cube([40,5.95,9.8]);}
module ap3_approach_top(){for(p=ap_fans)translate([p[0]-20,139,-12.21])cube([40,5.95,.01]);}
module ap3_moving_parts(){ap_baffles();ap_upper_gaskets();ap_meter_plates();ap_meter_gaskets();ap_meter_fasteners();ap_meter_seal_washers();ap_feedthroughs();}
if(ap_case=="new_aperture_area")translate([0,0,0])linear_extrude(.1)ap_round(16,10,1);
if(ap_case=="approach_core_solid_intersection")intersection(){ap3_gap_core();union(){ap_baffles();ap_fan_stress();ap_meter_plates();ap_meter_gaskets();ap_meter_fasteners();ap_meter_seal_washers();ap_feedthroughs();thermal_metal_base();}}
if(ap_case=="approach_top_intrusion")intersection(){ap3_approach_top();ap_feedthroughs();}
if(ap_case=="new_meter_to_bolt_seal_collision")intersection(){ap_meter_orifices();union(){ap_meter_fasteners();ap_meter_seal_washers();}}
if(ap_case=="new_aperture_interior_blockage")intersection(){for(p=ap_fans)translate([p[0],139.01,-21.99998])rotate([90,0,0])linear_extrude(4.49)offset(delta=-.00002)translate([-8,0])ap_round(16,9.99996,1);union(){ap_baffles();ap_meter_plates();ap_meter_gaskets();}}
if(ap_case=="approach_core_positive_control")intersection(){ap3_gap_core();translate([79.9,141,-18])cube([.2,.2,.2]);}
if(ap_case=="new_meter_border_control")intersection(){ap_meter_plates();translate([88.9,135,-18])cube([.2,.2,.2]);}
