// NEW assembly-state fixture. Parent all-controls-present failure is immutable.
include <../generated/entry_v6.scad>
module us_guide(){translate([0,0,panel_z-guide_thick])guide_plate();}
// Every modeled control OTHER THAN the guide is deliberately retained as
// an obstacle, even those that lift with the panel. This is conservative.
module us_other_controls(){
 ps_body();cp_pot_hardware();
 translate([0,0,7.6]){lever_bracket();lever_sweep();}
 touch_backer();for(b=buttons)button_pose(b){switch_holder(b);key_sweep(b);}
 a12_switch_electronics();
 for(c=caps)if(c[1]=="switch")translate([c[2],c[3],panel_z])selector_cap();
 ui_optics();
}
module us_panel_cohort(){ui_lid();ps_body();cp_pot_hardware();
 us_guide();touch_backer();for(b=buttons)button_pose(b){switch_holder(b);key_sweep(b);}
 a12_switch_electronics();for(c=caps)if(c[1]=="switch")translate([c[2],c[3],panel_z])selector_cap();ui_optics();}
// Static separated review state ONLY: +80Z is not a proven removal trajectory.
if(ua_case=="H9_service_retained_control_collision")intersection(){ui_h9_tool();us_other_controls();}
if(ua_case=="H9_guide_owner_geometry")intersection(){ui_h9_tool();us_guide();}
if(ua_case=="H9_other_control_owner_difference")difference(){intersection(){ui_h9_tool();ua_all_controls();}us_guide();}
if(ua_case=="H9_guide_owner_difference")difference(){intersection(){ui_h9_tool();us_guide();}ua_all_controls();}
if(ua_case=="H9_separated_panel_state_collision")intersection(){ui_h9_tool();translate([0,0,80])us_panel_cohort();}
if(ua_case=="H9_retained_lever_collision")intersection(){ui_h9_tool();translate([0,0,7.6]){lever_bracket();lever_sweep();}}
if(ua_case=="H9_tool_positive_control")intersection(){ui_h9_tool();translate([181.9,92.1,30])cube([.2,.2,.2]);}
if(ua_case=="H9_guide_positive_control")intersection(){ui_h9_tool();us_guide();translate([181.9,92.1,42.5])cube([.2,.2,.2]);}
