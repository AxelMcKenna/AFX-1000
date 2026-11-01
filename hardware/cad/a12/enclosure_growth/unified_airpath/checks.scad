// UA01 private coherent source32 scene; no qualification/release claims.
include <generated/unified-context.scad>
ua_case="none";
module ua_expand(m){minkowski(){children();cube([2*m,2*m,2*m],center=true);}}
module ua_returns(){return_assembly();}
module ua_return_copper_stress(){ua_expand(.16)return_bars();}
module ua_pb(name){import(str(ua_pb_folder,name,".stl"));}
module ua_PB_links(){ua_pb("ANA-COVERED-ENVELOPE");ua_pb("DIG-COVERED-ENVELOPE");}
module ua_PB_support(){ua_pb("SUPPORT-ENVELOPE");}
module ua_wire_parts(){pf_wires();}
module ua_free_wire(m=.25){pf_wires(m);}
module ua_components(m=.25){ei_native_components("all",m);}
module ua_all_controls(){ps_body();cp_pot_hardware();ps_other_controls();}
if(ua_case=="new_ANA_return_geometry")return_ana_bar();
if(ua_case=="new_ANA_retention_geometry"){return_retention();}
if(ua_case=="new_wire_pair_geometry")ua_wire_parts();
if(ua_case=="ANA_return_C24_clearance_collision")intersection(){ua_expand(.16)return_ana_bar();union(){ei_native_components("E28_C24",.25);ei_native_components("E28_C20",.25);}}
if(ua_case=="new_return_new_ground_collision")intersection(){ua_return_copper_stress();pf_wire(1,.25);}
if(ua_case=="old_return_new_ground_failure")intersection(){ua_old_ANA_bar();pf_wire(1,.25);}
if(ua_case=="old_ground_source_bore_failure")intersection(){pf_source_PCB();pf_sweep([[161,126.5,3.5],[161,126.5,9.72]],1.005);}
if(ua_case=="new_wire_pair_collision")intersection(){pf_wire(0,.25);pf_wire(1);}
if(ua_case=="new_wire_source_bore_collision")intersection(){pf_source_PCB();pf_relative_source();}
if(ua_case=="new_wire_receiver_bore_collision")intersection(){pf_receiver_PCB();pf_relative_receiver();}
if(ua_case=="return_vs_PB_ANA_collision")intersection(){ua_expand(.16)ua_returns();ua_expand(.35)ua_pb("ANA-COVERED-ENVELOPE");}
if(ua_case=="return_vs_PB_DIG_collision")intersection(){ua_expand(.16)ua_returns();ua_expand(.35)ua_pb("DIG-COVERED-ENVELOPE");}
if(ua_case=="return_vs_PB_support_collision")intersection(){ua_expand(.16)ua_returns();ua_expand(.35)ua_PB_support();}
if(ua_case=="new_wire_components_collision")intersection(){ua_free_wire();ui_wire_obstacles();}
if(ua_case=="new_wire_controls_collision")intersection(){ua_free_wire();ua_all_controls();}
if(ua_case=="new_wire_case_collision")intersection(){ua_free_wire();union(){ui_shell();ui_lid();rear_panel();thermal_metal_base();ap_tray();ap_everything_added();}}
if(ua_case=="new_wire_return_hardware_collision")intersection(){ua_free_wire();return_assembly();}
if(ua_case=="new_wire_PB_ANA_collision")intersection(){ua_free_wire();ua_expand(.1)ua_pb("ANA-COVERED-ENVELOPE");}
if(ua_case=="new_wire_PB_DIG_collision")intersection(){ua_free_wire();ua_expand(.1)ua_pb("DIG-COVERED-ENVELOPE");}
if(ua_case=="new_wire_PB_support_collision")intersection(){ua_free_wire();ua_expand(.1)ua_PB_support();}
if(ua_case=="native_component_case_0p25_collision")intersection(){ua_components();ei_case_obstacles();}
if(ua_case=="native_component_other_0p25_collision")intersection(){ua_components();ei_other_electronics();}
if(ua_case=="native_boards_mutual_0p25_collision")intersection(){union(){ei_native_board("P03");ei_native_components("P03",.25);}union(){ei_native_board("E28");ei_native_components("E28",.25);}}
if(ua_case=="new_R1_control")intersection(){ui_boxes(ui_inherited_envelopes);translate([109,81,8.4])cube([.2,.2,.2]);}
if(ua_case=="new_ground_control")intersection(){pf_wire(1,.25);translate([160.9,129.4,12])cube([.2,.2,.2]);}
if(ua_case=="new_ANA_shift_control")intersection(){return_ana_bar();translate([160.9,134.5,13])cube([.2,.2,.2]);}
