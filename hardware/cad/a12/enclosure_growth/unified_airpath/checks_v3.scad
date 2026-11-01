ua_return_part_boxes=[["AFX-A12-R03-ANA-BAR", [133.99983209384965, 130.12440229741526, 11.253325783728565], [183.00081515691082, 153.00090116947072, 16.600998540587405]], ["AFX-A12-R03-ANA-BASE-SCREW", [164.09619682169068, 132.72157239512757, -6.2003756734369135], [167.90380317830932, 136.52842760487243, 3.800197770229959]], ["AFX-A12-R03-ANA-CAP-SCREW0", [164.49970339465506, 127.77499989999998, 12.922918686892936], [167.50029660534494, 130.77500010000006, 19.523373528421857]], ["AFX-A12-R03-ANA-CAP-SCREW1", [164.49970339465506, 138.47499989999994, 12.922918686892936], [167.50029660534494, 141.47500010000005, 19.523373528421857]], ["AFX-A12-R03-ANA-CAP", [163.97115374615385, 127.59615374615385, 15.832692207692304], [168.02884625384615, 141.65384625384615, 17.95192317692308]], ["AFX-A12-R03-ANA-END0-SCREW", [135.99940688931017, 144.99999989999998, 7.649703394655073], [142.00059311068983, 151.00000010000002, 18.170593110689843]], ["AFX-A12-R03-ANA-END0-WASHER", [135.4993080541952, 144.49999989999998, 15.099308054195197], [142.5006919458048, 151.50000010000002, 15.650691945804803]], ["AFX-A12-R03-ANA-END1-SCREW", [174.99940688931017, 132.99999989999998, 9.149703394655075], [181.00059311068983, 139.00000010000002, 19.670593110689843]], ["AFX-A12-R03-ANA-END1-WASHER", [174.4993080541952, 132.49999989999998, 16.5993080541952], [181.5006919458048, 139.50000010000002, 17.150691945804805]], ["AFX-A12-R03-ANA-POST", [163.8846152846154, 127.50961528461538, -0.0002966053449271612], [168.1153847153846, 141.7403847153846, 16.43846163846154]], ["AFX-A12-R03-DIG-BAR", [126.99916135975624, 109.99942162144617, 11.5990014594126], [183.00083864024376, 134.50000010000005, 16.600998540587398]], ["AFX-A12-R03-DIG-BASE-SCREW", [164.09619682169068, 111.09657239512757, -6.200375673436906], [167.90380317830932, 114.90342760487243, 3.800197770229958]], ["AFX-A12-R03-DIG-CAP-SCREW0", [164.49970339465506, 106.14999989999998, 13.265466763816026], [167.50029660534494, 109.15000010000003, 19.865921605344933]], ["AFX-A12-R03-DIG-CAP-SCREW1", [164.49970339465506, 116.84999989999997, 13.265466763816026], [167.50029660534494, 119.85000010000002, 19.865921605344933]], ["AFX-A12-R03-DIG-CAP", [163.9531249, 105.9531249, 16.431249899999997], [168.0468751, 120.0468751, 18.3125001]], ["AFX-A12-R03-DIG-END0-SCREW", [128.99940688931017, 126.49999989999995, 7.649703394655073], [135.00059311068983, 132.50000010000002, 18.170593110689843]], ["AFX-A12-R03-DIG-END0-WASHER", [128.4993080541952, 125.99999989999996, 15.099308054195197], [135.5006919458048, 133.00000010000002, 15.650691945804803]], ["AFX-A12-R03-DIG-END1-SCREW", [174.99940688931017, 118.99999989999996, 9.14970339465507], [181.00059311068983, 125.00000010000004, 19.670593110689836]], ["AFX-A12-R03-DIG-END1-WASHER", [174.4993080541952, 118.49999989999996, 16.599308054195202], [181.5006919458048, 125.50000010000004, 17.1506919458048]], ["AFX-A12-R03-DIG-POST", [163.9531249, 105.9531249, -0.0002966053449322202], [168.0468751, 120.0468751, 16.7125001]]];
module ua_return_bbox_supersets(m=.51){for(b=ua_return_part_boxes)translate([b[1][0]-m,b[1][1]-m,b[1][2]-m])cube([b[2][0]-b[1][0]+2*m,b[2][1]-b[1][1]+2*m,b[2][2]-b[1][2]+2*m]);}
// UA01 private coherent source32 scene; no qualification/release claims.
include <generated/unified-context_v2.scad>
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
if(ua_case=="return_vs_PB_ANA_collision")intersection(){ua_return_bbox_supersets();ua_pb("ANA-COVERED-ENVELOPE");}
if(ua_case=="return_vs_PB_DIG_collision")intersection(){ua_return_bbox_supersets();ua_pb("DIG-COVERED-ENVELOPE");}
if(ua_case=="return_vs_PB_support_collision")intersection(){ua_return_bbox_supersets();ua_PB_support();}
if(ua_case=="new_wire_components_collision")intersection(){ua_free_wire();ui_wire_obstacles();}
if(ua_case=="new_wire_controls_collision")intersection(){ua_free_wire();ua_all_controls();}
if(ua_case=="new_wire_case_collision")intersection(){ua_free_wire();union(){ui_shell();ui_lid();rear_panel();thermal_metal_base();ap_tray();ap_everything_added();}}
if(ua_case=="new_wire_return_hardware_collision")intersection(){ua_free_wire();return_assembly();}
if(ua_case=="new_wire_PB_ANA_collision")intersection(){ua_free_wire(.4232050807568878);ua_pb("ANA-COVERED-ENVELOPE");}
if(ua_case=="new_wire_PB_DIG_collision")intersection(){ua_free_wire(.4232050807568878);ua_pb("DIG-COVERED-ENVELOPE");}
if(ua_case=="new_wire_PB_support_collision")intersection(){ua_free_wire(.4232050807568878);ua_PB_support();}
if(ua_case=="native_component_case_0p25_collision")intersection(){ua_components();ei_case_obstacles();}
if(ua_case=="native_component_other_0p25_collision")intersection(){ua_components();ei_other_electronics();}
if(ua_case=="native_boards_mutual_0p25_collision")intersection(){union(){ei_native_board("P03");ei_native_components("P03",.25);}union(){ei_native_board("E28");ei_native_components("E28",.25);}}
if(ua_case=="new_R1_control")intersection(){ui_boxes(ui_inherited_envelopes);translate([109,81,8.4])cube([.2,.2,.2]);}
if(ua_case=="new_ground_control")intersection(){pf_wire(1,.25);translate([160.9,129.4,12])cube([.2,.2,.2]);}
if(ua_case=="new_ANA_shift_control")intersection(){return_ana_bar();translate([160.9,134.5,13])cube([.2,.2,.2]);}

if(ua_case=="part_ANA_POST")import("/Users/axelmckrnna/dev/rmx-publish/hardware/cad/a12/enclosure_growth/unified_airpath/return_variant2/generated/AFX-A12-R03-ANA-POST.stl");

if(ua_case=="part_ANA_CAP")import("/Users/axelmckrnna/dev/rmx-publish/hardware/cad/a12/enclosure_growth/unified_airpath/return_variant2/generated/AFX-A12-R03-ANA-CAP.stl");

if(ua_case=="part_DIG_POST")import("/Users/axelmckrnna/dev/rmx-publish/hardware/cad/a12/enclosure_growth/unified_airpath/return_variant2/generated/AFX-A12-R03-DIG-POST.stl");

if(ua_case=="part_DIG_CAP")import("/Users/axelmckrnna/dev/rmx-publish/hardware/cad/a12/enclosure_growth/unified_airpath/return_variant2/generated/AFX-A12-R03-DIG-CAP.stl");
