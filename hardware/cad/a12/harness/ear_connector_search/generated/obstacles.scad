include </Users/axelmckrnna/dev/rmx-publish/hardware/cad/a12/harness/ear_connector_search/inputs/context/hardware/cad/a12/thermal-integration.scad>
trial="case";
module window(){translate([154,90,3])cube([44,49,34]);}
module case_parts(){retained_thermal_shell();thermal_controls();thermal_metal_base();lower_shell_fasteners();}
if(trial=="case")intersection(){window();case_parts();}
if(trial=="witness")intersection(){case_parts();translate([163.9,109.9,23])cube([.2,.2,.2]);}
