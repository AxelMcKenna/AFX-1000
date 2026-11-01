include </Users/axelmckrnna/dev/rmx-publish/hardware/cad/a12/positive_links/proposals/dig-leg-y121p3/native/context/hardware/cad/a12/pot_stack/generated/checks.scad>
include </Users/axelmckrnna/dev/rmx-publish/hardware/cad/a12/positive_links/proposals/dig-leg-y121p3/native/gauge-derived.scad>
pb_parts="/Users/axelmckrnna/dev/rmx-publish/hardware/cad/a12/positive_links/proposals/dig-leg-y121p3/native/context/hardware/cad/a12/positive_links/proposals/dig-leg-y121p3/generated/";

pb_case="none";
module pb_raw(name){import(str(pb_parts,name,".stl"));}
module pb_links(){pb_raw("ANA-COVERED-ENVELOPE");pb_raw("DIG-COVERED-ENVELOPE");}
module pb_support(){pb_raw("SUPPORT-ENVELOPE");}
module pb_all(){pb_links();pb_support();}
module pb_expand(m){minkowski(){children();cube([2*m,2*m,2*m],center=true);}}
module pb_J8(){let($fn=96)expanded(){lug();washer_head();}}
module pb_nominal_J8(){let($fn=96){lug();washer_head();shaft();}}
// Only the four positive terminal bodies are intended electrical contacts.
// The four negative-terminal bodies remain full collision obstacles.
module pb_components(){ui_boxes([for(b=ui_native_boxes)if(!in_list(b[0],["P03_J24","P03_J23","E28_J10","E28_J11"]))b]);ui_cylinders();ui_boxes(ui_inherited_envelopes);ui_rear_bodies();tc2_components();ps_body();}
module pb_board_obstacles(){ui_PCBS();pb_components();}
module pb_others(){ui_controls();ui_lid();tc2_posts();tc2_heads();ui_h9_head();lower_shell_fasteners();}
module pb_returns(){return_assembly();}
module pb_case_obstacles(){ui_shell_rear();}
if(pb_case=="old_J8_positive_failure")intersection(){pb_J8();let($fn=96)positive_hardware();}
if(pb_case=="new_J8_positive_collision")intersection(){pb_J8();pb_expand(.1)pb_all();}
if(pb_case=="new_positive_electronics_fed_collision")intersection(){pb_expand(.35)pb_all();pb_board_obstacles();}
if(pb_case=="new_positive_controls_hardware_collision")intersection(){pb_expand(.35)pb_all();pb_others();}
if(pb_case=="new_positive_returns_collision")intersection(){pb_expand(.35)pb_all();pb_returns();}
if(pb_case=="new_positive_case_collision")intersection(){union(){pb_expand(.35)pb_links();intersection(){pb_expand(.35)pb_support();translate([-100,-100,2.80002])cube([600,600,200]);}}pb_case_obstacles();}
if(pb_case=="new_positive_old_fed_wire_collision")intersection(){pb_expand(.1)pb_all();union(){pf_wires(.25);ui_all_joints(.25);}}
// U14 source geometry is intentionally a separate context: this does not
// claim the old fed/J4 wire endpoints are valid on U14/P9.
if(pb_case=="new_positive_U14_component_collision")intersection(){pb_expand(.35)pb_all();let($fn=96)minkowski(){electronics();cube([.00000002,.00000002,.4],center=true);}}
if(pb_case=="new_J8_controls_case_collision")intersection(){pb_J8();union(){pb_others();pb_case_obstacles();ps_body();}}
if(pb_case=="new_J8_old_fed_wire_collision")intersection(){pb_J8();union(){pf_wires();ui_all_joints();}}
if(pb_case=="positive_bar_control")intersection(){pb_raw("DIG-CU");translate([119.9,121.2,18])cube([.2,.2,.2]);}
if(pb_case=="positive_support_control")intersection(){pb_support();translate([165.9,123.4,3])cube([.2,.2,.2]);}
if(pb_case=="J8_control")intersection(){let($fn=96)lug();located()translate([7,-.1,.1])cube([.2,.2,.2]);}
if(pb_case=="candidate_DIG_geometry")pb_raw("DIG-CU");
if(pb_case=="candidate_support_geometry")pb_support();
