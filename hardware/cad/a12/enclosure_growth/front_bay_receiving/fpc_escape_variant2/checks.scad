// New fourteen actual-pin local exits; no full-harness or wire approval.
include <../robust_rear_variant/checks.scad>
include <routes.scad>
escape_case="none";
fr_escape_ids=["J3.1", "J3.2", "J203.1", "J203.2", "J203.3", "J202.1", "J202.2", "J202.3", "J201.1", "J201.2", "J4.1", "J4.2", "J2.1", "J2.2"];
fr_escape_refs=["J3", "J3", "J203", "J203", "J203", "J202", "J202", "J202", "J201", "J201", "J4", "J4", "J2", "J2"];

if(escape_case=="wire_escape_geometry")fr_escapes(0);
if(escape_case=="wire_escape_case_collision")intersection(){fr_escapes();fr_case_environment();}
if(escape_case=="wire_escape_existing_electronics_collision")intersection(){fr_escapes();ui_electronics(false,false);}
if(escape_case=="wire_escape_NF_receiving_collision")intersection(){fr_escapes();fr_all_material("NF233",.2);}
if(escape_case=="wire_escape_other_FPC_parts_collision")for(i=[0:len(fr_escape_routes)-1])intersection(){fr_escape_sweep(fr_escape_routes[i],.955+.000753+.9);union(){fr_PCB("FPC84",.2);fr_boxes([for(b=fr_boxes)if(fr_matches(b[0],"FPC84")&&b[0]!=str("FPC84_",fr_escape_refs[i]))b],"all",.2);fr_boxes(fr_tails,"FPC84",.2);}}
if(escape_case=="wire_escape_power_controls_collision")intersection(){fr_escapes();union(){fr_power_environment();ua_all_controls();}}
if(escape_case=="wire_escape_existing_wires_collision")intersection(){fr_escapes();pf_wires(.25);}
if(escape_case=="wire_escape_intrinsic_pair_collision")for(i=[0:len(fr_escape_routes)-1],j=[0:len(fr_escape_routes)-1])if(i<j)intersection(){fr_escape_sweep(fr_escape_routes[i],.955+.000753+.24);fr_escape_sweep(fr_escape_routes[j],.955+.000753+.24);}
if(escape_case=="wire_escape_positive_control")intersection(){fr_escapes();translate([18.9,162.9,11])cube([.2,.2,.2]);}
