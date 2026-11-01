// Conservative interior lower-leg core; deliberately10um inside geometric
// Y boundaries (not an expansion/repair of either physical part).
module ap3_clear_lower_core(){for(p=ap_fans)translate([p[0]-15.5,139.01,-22])cube([31,5.93,9.8]);}
module ap3_rear_intruders(){ap_baffles();ap_fan_stress();ap_meter_plates();ap_meter_gaskets();ap_meter_fasteners();ap_meter_seal_washers();ap_feedthroughs();thermal_metal_base();}
if(ap_case=="lower_approach_clear_core_collision")intersection(){ap3_clear_lower_core();ap3_rear_intruders();}
if(ap_case=="lower_approach_core_control")intersection(){ap3_clear_lower_core();translate([79.9,141,-18])cube([.2,.2,.2]);}
if(ap_case=="old_rear_wall_approach_witness")intersection(){ap3_clear_lower_core();for(p=ap_fans)translate([p[0]-16,142,-22])cube([32,2,9.8]);}
// Pure positive FIP intrusion probe excludes only actual broad-core boundaries,
// with10um of geometric reservation at its twoYedges, not seat exclusions.
if(ap_case=="rear_feedthrough_intrusion_witness")intersection(){for(p=ap_fans)translate([p[0]-20,139.01,-22])cube([40,5.93,9.8]);ap_feedthroughs();}
