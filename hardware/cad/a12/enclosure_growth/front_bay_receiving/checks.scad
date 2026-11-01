// New capturedNF233+FPC84 receiving study; parentUA01 is read-only.
include <../unified_airpath/generated/entry_v6.scad>
include <generated/components233.scad>
fr_case="none";
module fr_case_environment(){ui_shell();ui_lid();rear_panel();thermal_metal_base();ap_everything_added();eb_feet_assembly();eb_foot_screws();eb_lower();}
module fr_power_environment(){ua_returns();ua_PB_links();ua_PB_support();ui_h9_head();tc2_heads();}
module fr_all_components(id="all",m=.45){fr_boxes(fr_boxes,id,m);fr_boxes(fr_tails,id,m);}
module fr_all_material(id="all",m=.45){fr_PCB(id,m);fr_all_components(id,m);fr_boxes(fr_mates,id,m);}
// All315/317sourceparts retained. Wholeboard filled holes in the expanded
// comparison are conservative; nominal PCB exports retain actualdrills.
for(id=["NF233","FPC84"]){
 if(fr_case==str(id,"_PCB_geometry"))fr_PCB(id);
 if(fr_case==str(id,"_components_geometry"))fr_all_components(id,0);
 if(fr_case==str(id,"_body_case_collision"))intersection(){fr_all_material(id);fr_case_environment();}
 if(fr_case==str(id,"_body_electronics_collision"))intersection(){fr_all_material(id);union(){ui_electronics(false,false);tc2_posts();}}
 if(fr_case==str(id,"_body_controls_collision"))intersection(){fr_all_material(id);ua_all_controls();}
 if(fr_case==str(id,"_body_power_collision"))intersection(){fr_all_material(id);fr_power_environment();}
 if(fr_case==str(id,"_body_wires_collision"))intersection(){fr_all_material(id);union(){pf_wires(.65);ui_all_joints(.25);}}
 if(fr_case==str(id,"_short_bundle_case_collision"))intersection(){fr_boxes(fr_bundles,id,.9);fr_case_environment();}
 if(fr_case==str(id,"_short_bundle_electronics_collision"))intersection(){fr_boxes(fr_bundles,id,.9);ui_electronics(false,false);}
 if(fr_case==str(id,"_short_bundle_power_controls_collision"))intersection(){fr_boxes(fr_bundles,id,.9);union(){fr_power_environment();ua_all_controls();}}
 if(fr_case==str(id,"_mate_other_components_collision"))for(a=fr_mates)if(substr_id(a[0],id))for(b=fr_boxes)if(substr_id(b[0],id)&&a[0]!=b[0])intersection(){fr_boxes([a],"all",.25);fr_boxes([b]);}
 if(fr_case==str(id,"_mate_mutual_collision"))for(i=[0:len(fr_mates)-1],j=[0:len(fr_mates)-1])if(i<j&&substr_id(fr_mates[i][0],id)&&substr_id(fr_mates[j][0],id))intersection(){fr_boxes([fr_mates[i]],"all",.25);fr_boxes([fr_mates[j]]);}
 if(fr_case==str(id,"_nominal_native_drill_calibration_collision"))intersection(){fr_PCB(id);for(b=fr_boards)if(b[0]==id)translate(b[1])rotate([90,0,0])for(h=b[3])translate([h[0],h[1],-1.77])cylinder(d=min(h[2],h[3])*.25,h=1.78,$fn=48);}
}
if(fr_case=="boards_and_receivers_mutual_collision")intersection(){fr_all_material("NF233",.65);fr_all_material("FPC84",0);}
if(fr_case=="NF_PCB_positive_control")intersection(){fr_PCB("NF233");translate([180,181,10])cube([.2,.2,.2]);}
if(fr_case=="FPC_PCB_positive_control")intersection(){fr_PCB("FPC84");translate([30,181,10])cube([.2,.2,.2]);}
// Potential vertical-projection obstruction only, not an airflow solution.
if(fr_case=="new_receiving_inlet_shadow")linear_extrude(.1)intersection(){projection()fr_all_material("all",0);ap_ports_2d();}
