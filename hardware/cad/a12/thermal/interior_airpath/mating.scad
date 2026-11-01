// Supplementary AP02 nominal mates. Original70-case sources are not edited.
include <generated/checks.scad>
mate_case="none";
module mate_meter_parts(){ap_meter_plates();ap_meter_gaskets();ap_baffles();ap_meter_seal_washers();}
if(mate_case=="M3_hardware_nominal_mates")intersection(){ap_fasteners();union(){ap_tray();ap_guards();ap_fans_assembly();ap_shims();ap_seal_washers();}}
if(mate_case=="M2_hardware_nominal_mates")intersection(){ap_meter_fasteners();mate_meter_parts();}
if(mate_case=="upper_gasket_base")intersection(){ap_upper_gaskets();thermal_metal_base();}
if(mate_case=="upper_gasket_tray")intersection(){ap_upper_gaskets();ap_tray();}
if(mate_case=="frame_gasket_tray")intersection(){ap_frame_gaskets();ap_tray();}
if(mate_case=="frame_gasket_fan")intersection(){ap_frame_gaskets();ap_fans_assembly();}
if(mate_case=="meter_gasket_wall_plate")intersection(){ap_meter_gaskets();union(){ap_meter_plates();ap_baffles();}}
if(mate_case=="feedthrough_wall")intersection(){ap_feedthroughs();ap_baffles();}
if(mate_case=="new_hardware_base_pins")intersection(){union(){ap_hardware_stress();ap_meter_fasteners();ap_feedthroughs();}thermal_metal_base();}
if(mate_case=="new_parts_feet_spacers")intersection(){union(){ap_baffles();ap_added();ap_fasteners();ap_fans_assembly();}union(){eb_feet_assembly();fi_spacers();}}
if(mate_case=="meter_plate_other_new_parts")intersection(){ap_meter_plates();union(){ap_baffles();ap_feedthroughs();ap_upper_gaskets();ap_shims();ap_frame_gaskets();}}
// Deliberate20micron overlaps are1000×the approved20nmtestguards.
if(mate_case=="M3_directseal_overlap_control")intersection(){ap_fasteners();translate([0,0,-.02])ap_seal_washers();translate([97.8,181.3,-28.215])cube([.4,.4,.01]);}
if(mate_case=="M2_directseal_overlap_control")intersection(){ap_meter_fasteners();translate([0,-.02,0])ap_meter_seal_washers();translate([74.3,138.985,-9.1])cube([.4,.01,.4]);}
if(mate_case=="upper_seal_tray_overlap_control")intersection(){ap_tray();translate([0,0,-.02])ap_upper_gaskets();translate([49.8,142.8,-6.715])cube([.4,.4,.01]);}
if(mate_case=="upper_seal_base_overlap_control")intersection(){thermal_metal_base();translate([0,0,.02])ap_upper_gaskets();translate([49.8,142.8,-6.195])cube([.4,.4,.01]);}
if(mate_case=="frame_seal_tray_overlap_control")intersection(){ap_tray();translate([0,0,-.02])ap_frame_gaskets();translate([79.8,184.7,-25.215])cube([.4,.4,.01]);}
if(mate_case=="frame_seal_fan_overlap_control")intersection(){ap_fans_assembly();translate([0,0,.02])ap_frame_gaskets();translate([79.8,184.7,-24.695])cube([.4,.4,.01]);}
if(mate_case=="meter_seal_plate_overlap_control")intersection(){ap_meter_plates();translate([0,-.02,0])ap_meter_gaskets();translate([87.8,141.485,-15.2])cube([.4,.01,.4]);}
if(mate_case=="meter_seal_wall_overlap_control")intersection(){ap_baffles();translate([0,.02,0])ap_meter_gaskets();translate([87.8,142.005,-15.2])cube([.4,.01,.4]);}
