// EB01 derived scene. No captured source files or parent modules are edited.
eb_case="none";
module eb_foot_screw(p){translate([p[0],p[1],0])rotate([180,0,0]){
 cylinder(d=5.6,h=.35,$fn=64);
 translate([0,0,.35])cylinder(d1=5.6,d2=3,h=1.3,$fn=64);
 translate([0,0,1.65])cylinder(d=3,h=10.35,$fn=64);
}}
module eb_foot_screws(){for(p=thermal_feet_xy)eb_foot_screw(p);}
module eb_feet_assembly(){difference(){thermal_feet();
 // Thread engagement only: major-diameter fit abstraction, NOT a tap drill.
 for(p=thermal_feet_xy)translate([p[0],p[1],-16.2])cylinder(d=3.02,h=10.00002,$fn=64);
}}
module eb_base(){thermal_metal_base();}
module eb_metal(){eb_base();eb_feet_assembly();}
module eb_lower(){lower_shell_fasteners();}
module eb_case_and_lid(){ui_shell();tc2_posts();rear_panel();ui_lid();}
module eb_other_hardware(){return_assembly();import("EB_POSITIVE_STL");ui_h9_head();tc2_heads();}
module eb_bearing_shifted_lower(){translate([0,0,.00002])eb_lower();}
module eb_screw_tip_control(){intersection(){eb_foot_screws();translate([19.9,19.9,-10])cube([.2,.2,.2]);}}
module eb_newfront_witness(){translate([166.9,180.3,-3])cube([.2,.2,.2]);}
module eb_case_newbolt_witness(){translate([166.9,180.3,8])cube([.2,.2,.2]);}
if(eb_case=="metal_geometry")eb_base();
if(eb_case=="standalone_metal_geometry")eb_part_metal_base();
if(eb_case=="feet_geometry")thermal_feet();
if(eb_case=="carrier_geometry"){ui_shell();tc2_posts();}
if(eb_case=="attachment_geometry"){eb_lower();eb_foot_screws();}
if(eb_case=="assembly_geometry"){eb_metal();eb_lower();eb_foot_screws();eb_case_and_lid();ui_electronics();ui_controls();eb_other_hardware();pf_wires();ui_all_joints();}
if(eb_case=="retained_controls_review")ui_controls();
if(eb_case=="retained_electronics_review")ui_electronics();
if(eb_case=="retained_wire_review"){pf_wires();ui_all_joints();}
if(eb_case=="retained_power_review")eb_other_hardware();
if(eb_case=="lid_rear_review"){ui_lid();rear_panel();}
if(eb_case=="metal_carrier_collision")intersection(){translate([0,0,-.00002])eb_base();ui_shell();}
if(eb_case=="metal_electronics_collision")intersection(){eb_metal();ui_electronics();}
if(eb_case=="metal_native_0p25_collision")intersection(){eb_metal();ei_native_components("all",.25);}
if(eb_case=="metal_controls_ports_collision")intersection(){eb_metal();union(){ui_controls_and_lid();ui_rear_bodies(.25);}}
if(eb_case=="metal_wire_collision")intersection(){eb_metal();union(){pf_wires(.25);ui_all_joints(.25);}}
if(eb_case=="metal_return_positive_collision")intersection(){translate([0,0,-.00002])eb_base();eb_other_hardware();}
if(eb_case=="lower_carrier_collision")intersection(){eb_bearing_shifted_lower();ui_shell();}
if(eb_case=="lower_metal_collision")intersection(){eb_lower();eb_metal();}
if(eb_case=="lower_electronics_collision")intersection(){eb_lower();ui_electronics();}
if(eb_case=="lower_native_0p25_collision")intersection(){eb_lower();ei_native_components("all",.25);}
if(eb_case=="lower_controls_ports_collision")intersection(){eb_lower();union(){ui_controls_and_lid();ui_rear_bodies(.25);}}
if(eb_case=="lower_wire_collision")intersection(){eb_lower();union(){pf_wires(.25);ui_all_joints(.25);}}
if(eb_case=="lower_other_hardware_collision")intersection(){eb_lower();eb_other_hardware();}
if(eb_case=="foot_screw_base_collision")intersection(){eb_foot_screws();eb_base();}
if(eb_case=="foot_screw_feet_collision")intersection(){eb_foot_screws();eb_feet_assembly();}
if(eb_case=="foot_screw_carrier_collision")intersection(){translate([0,0,-.00002])eb_foot_screws();ui_shell();}
if(eb_case=="foot_screw_other_collision")intersection(){eb_foot_screws();union(){ui_electronics();ui_controls();eb_other_hardware();}}
if(eb_case=="feet_pin_collision")intersection(){translate([0,0,-.00002])eb_feet_assembly();eb_base();}
if(eb_case=="front_material_positive_control")intersection(){eb_base();translate([166.9,170,-3])cube([.2,.2,.2]);}
if(eb_case=="new_bolt_material_positive_control")intersection(){eb_lower();eb_case_newbolt_witness();}
if(eb_case=="foot_screw_positive_control")eb_screw_tip_control();
if(eb_case=="missing_new_bore_positive_control")intersection(){eb_lower();translate([163,176.4,0])cube([8,8,10]);}
if(eb_case=="unrelieved_carrier_positive_control")intersection(){eb_base();a12_chassis();translate([211.5,118.5,.5])cube([1,1,1]);}
if(eb_case=="undersized_foot_countersink_positive_control")intersection(){eb_foot_screws();difference(){translate([16,16,-6.2])cube([8,8,6.2]);translate([20,20,-6.21])cylinder(d=3.4,h=6.22,$fn=64);translate([20,20,-1.3])cylinder(d1=3.4,d2=6,h=1.3,$fn=64);}}
