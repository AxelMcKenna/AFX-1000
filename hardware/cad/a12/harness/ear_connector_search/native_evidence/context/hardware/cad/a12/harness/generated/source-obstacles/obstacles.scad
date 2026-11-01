include </Users/axelmckrnna/dev/rmx-publish/hardware/cad/a12/thermal-integration.scad>
trial="case";
module window(){translate([154,104,3])cube([31,35,34]);}
module case_parts(){retained_thermal_shell();thermal_controls();thermal_metal_base();lower_shell_fasteners();}
if(trial=="case")intersection(){window();case_parts();}
if(trial=="return")intersection(){window();return_assembly();}
if(trial=="positive")intersection(){window();import("/Users/axelmckrnna/dev/rmx-publish/hardware/cad/a12/positive_links/generated/positive-links.stl");}
if(trial=="switch_lead_witness")intersection(){case_parts();translate([163.9,109.9,23])cube([.2,.2,.2]);}
