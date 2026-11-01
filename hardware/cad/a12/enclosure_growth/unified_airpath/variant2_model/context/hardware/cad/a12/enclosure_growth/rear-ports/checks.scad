include </Users/axelmckrnna/dev/rmx-publish/hardware/cad/a12/enclosure_growth/unified_airpath/variant2_model/context/hardware/cad/a12/thermal-integration.scad>
rp_old=[["input_rca_l", 34.0, 0, 7.199999999999999, 12, 17, 12], ["input_rca_r", 50.0, 0, 7.199999999999999, 12, 17, 12], ["input_ts_l", 64.5, 0, 3.6999999999999993, 19, 28, 19], ["input_ts_r", 84.5, 0, 3.6999999999999993, 19, 28, 19], ["output_rca_l", 130.0, 0, 7.199999999999999, 12, 17, 12], ["output_rca_r", 146.0, 0, 7.199999999999999, 12, 17, 12], ["output_ts_l", 172.5, 0, 3.6999999999999993, 19, 28, 19], ["output_ts_r", 192.5, 0, 3.6999999999999993, 19, 28, 19], ["hardware_bypass", 218.5, 0, 9.0, 9, 18, 14], ["line_mode", 236.5, 0, 12.5, 9, 18, 7], ["micro_sd", 111.0, 0, 14.5, 14, 18, 3], ["service_usb", 257.0, 0, 12.0, 12, 25, 8]];
rp_new=[["input_rca_l", 34.0, 0, 7.999999999999999, 12, 17, 12], ["input_rca_r", 50.0, 0, 7.999999999999999, 12, 17, 12], ["input_ts_l", 64.5, 0, 4.499999999999999, 19, 28, 19], ["input_ts_r", 84.5, 0, 4.499999999999999, 19, 28, 19], ["output_rca_l", 130.0, 0, 7.999999999999999, 12, 17, 12], ["output_rca_r", 146.0, 0, 7.999999999999999, 12, 17, 12], ["output_ts_l", 172.5, 0, 4.499999999999999, 19, 28, 19], ["output_ts_r", 192.5, 0, 4.499999999999999, 19, 28, 19], ["hardware_bypass", 218.5, 0, 9.0, 9, 18, 14], ["line_mode", 236.5, 0, 12.5, 9, 18, 7], ["micro_sd", 111.0, 0, 14.5, 14, 18, 3], ["service_usb", 257.0, 0, 12.0, 12, 25, 8]];

rear_case="plate";
function rp_audio_id(id)=id=="input_rca_l"||id=="input_rca_r"||id=="input_ts_l"||id=="input_ts_r"||id=="output_rca_l"||id=="output_rca_r"||id=="output_ts_l"||id=="output_ts_r";
// The mating face is correlated at Y0. The requirement boxes describe the
// body BEHIND that face, not the thread/neck through its own panel aperture.
// A 20nm inward guard removes only the coplanar rear-face STL artifact.
module rp_boxes(rows,m=0){for(b=rows)translate([b[1]-m,.00002,b[3]-.2-m])cube([b[4]+2*m,b[5]+m,b[6]+.4+2*m]);}
module rp_plate(){rear_panel();}
module rp_chassis(){retained_thermal_shell();}
if(rear_case=="plate")rp_plate();
if(rear_case=="bodies")rp_boxes([for(b=rp_new)if(rp_audio_id(b[0]))b]);
if(rear_case=="audio_chassis_collision")intersection(){rp_boxes([for(b=rp_new)if(rp_audio_id(b[0]))b],.25);rp_chassis();}
if(rear_case=="other_ports_chassis_collision")intersection(){rp_boxes([for(b=rp_new)if(!rp_audio_id(b[0]))b],.25);rp_chassis();}
if(rear_case=="old_TS_blocked_witness")intersection(){rp_boxes([for(b=rp_old)if(b[0]=="input_ts_l"||b[0]=="input_ts_r"||b[0]=="output_ts_l"||b[0]=="output_ts_r")b]);rp_chassis();}
if(rear_case=="plate_positive_control")intersection(){rp_plate();translate([15.9,-1,4])cube([.2,.2,.2]);}
if(rear_case=="TS_body_positive_control")intersection(){rp_boxes([for(b=rp_new)if(b[0]=="input_ts_l")b]);translate([73.9,1,4.7])cube([.2,.2,.2]);}
