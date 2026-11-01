include </Users/axelmckrnna/dev/rmx-publish/hardware/cad/a12/thermal/interior_airpath_meter318/mating.scad>
include </Users/axelmckrnna/dev/rmx-publish/hardware/cad/a12/thermal/interior_airpath_meter318/mating_guards.scad>
mate_seated_case="none";
if(mate_seated_case=="M3_hardware_nominal_mates")difference(){intersection(){ap_fasteners();union(){ap_tray();ap_guards();ap_fans_assembly();ap_shims();ap_seal_washers();}}mate_guard_for("M3_hardware_nominal_mates");}
if(mate_seated_case=="M2_hardware_nominal_mates")difference(){intersection(){ap_meter_fasteners();mate_meter_parts();}mate_guard_for("M2_hardware_nominal_mates");}
if(mate_seated_case=="upper_gasket_base")difference(){intersection(){ap_upper_gaskets();thermal_metal_base();}mate_guard_for("upper_gasket_base");}
if(mate_seated_case=="upper_gasket_tray")difference(){intersection(){ap_upper_gaskets();ap_tray();}mate_guard_for("upper_gasket_tray");}
if(mate_seated_case=="frame_gasket_tray")difference(){intersection(){ap_frame_gaskets();ap_tray();}mate_guard_for("frame_gasket_tray");}
if(mate_seated_case=="frame_gasket_fan")difference(){intersection(){ap_frame_gaskets();ap_fans_assembly();}mate_guard_for("frame_gasket_fan");}
if(mate_seated_case=="meter_gasket_wall_plate")difference(){intersection(){ap_meter_gaskets();union(){ap_meter_plates();ap_baffles();}}mate_guard_for("meter_gasket_wall_plate");}
if(mate_seated_case=="feedthrough_wall")difference(){intersection(){ap_feedthroughs();ap_baffles();}mate_guard_for("feedthrough_wall");}
if(mate_seated_case=="new_hardware_base_pins")intersection(){union(){ap_hardware_stress();ap_meter_fasteners();ap_feedthroughs();}thermal_metal_base();}
if(mate_seated_case=="new_parts_feet_spacers")intersection(){union(){ap_baffles();ap_added();ap_fasteners();ap_fans_assembly();}union(){eb_feet_assembly();fi_spacers();}}
if(mate_seated_case=="meter_plate_other_new_parts")intersection(){ap_meter_plates();union(){ap_baffles();ap_feedthroughs();ap_upper_gaskets();ap_shims();ap_frame_gaskets();}}
if(mate_seated_case=="M3_directseal_overlap_control")difference(){intersection(){ap_fasteners();translate([0,0,-.02])ap_seal_washers();translate([97.8,181.3,-28.215])cube([.4,.4,.01]);}mate_guard_for("M3_hardware_nominal_mates");}
if(mate_seated_case=="M2_directseal_overlap_control")difference(){intersection(){ap_meter_fasteners();translate([0,-.02,0])ap_meter_seal_washers();translate([74.3,133.985,-9.1])cube([.4,.01,.4]);}mate_guard_for("M2_hardware_nominal_mates");}
if(mate_seated_case=="upper_seal_tray_overlap_control")difference(){intersection(){ap_tray();translate([0,0,-.02])ap_upper_gaskets();translate([49.8,137.8,-6.715])cube([.4,.4,.01]);}mate_guard_for("upper_gasket_tray");}
if(mate_seated_case=="upper_seal_base_overlap_control")difference(){intersection(){thermal_metal_base();translate([0,0,.02])ap_upper_gaskets();translate([49.8,137.8,-6.195])cube([.4,.4,.01]);}mate_guard_for("upper_gasket_base");}
if(mate_seated_case=="frame_seal_tray_overlap_control")difference(){intersection(){ap_tray();translate([0,0,-.02])ap_frame_gaskets();translate([79.8,184.7,-25.215])cube([.4,.4,.01]);}mate_guard_for("frame_gasket_tray");}
if(mate_seated_case=="frame_seal_fan_overlap_control")difference(){intersection(){ap_fans_assembly();translate([0,0,.02])ap_frame_gaskets();translate([79.8,184.7,-24.695])cube([.4,.4,.01]);}mate_guard_for("frame_gasket_fan");}
if(mate_seated_case=="meter_seal_plate_overlap_control")difference(){intersection(){ap_meter_plates();translate([0,-.02,0])ap_meter_gaskets();translate([88.8,136.485,-15.2])cube([.4,.01,.4]);}mate_guard_for("meter_gasket_wall_plate");}
if(mate_seated_case=="meter_seal_wall_overlap_control")difference(){intersection(){ap_baffles();translate([0,.02,0])ap_meter_gaskets();translate([88.8,137.005,-15.2])cube([.4,.01,.4]);}mate_guard_for("meter_gasket_wall_plate");}

module mate_boss_radial_overlap(){intersection(){ap_tray();for(p=ap_fans)for(x=[-16,16],y=[-16,16])translate([p[0]+x,p[1]+y,-25.1])difference(){cylinder(r=3.1,h=.3,$fn=96);translate([0,0,-.01])cylinder(r=3.08,h=.32,$fn=96);}}}
module mate_FIP_radial_overlap(){intersection(){ap_baffles();for(x=[46,235.5])translate([x,137,-10])rotate([-90,0,0])cylinder(r=2.22,h=2,$fn=96);}}
module mate_FIP_axial_overlap(){intersection(){ap_baffles();translate([0,.02,0])ap_feedthroughs();}}
if(mate_seated_case=="boss_radial_overlap_control")difference(){mate_boss_radial_overlap();mate_guard_for("frame_gasket_tray");}
if(mate_seated_case=="FIP_radial_overlap_control")difference(){mate_FIP_radial_overlap();mate_guard_for("feedthrough_wall");}
if(mate_seated_case=="FIP_axial_overlap_control")difference(){mate_FIP_axial_overlap();mate_guard_for("feedthrough_wall");}
