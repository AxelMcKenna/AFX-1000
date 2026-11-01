include </Users/axelmckrnna/dev/rmx-publish/hardware/cad/a12/thermal/enlarged_base_pot/context/hardware/cad/a12/enclosure_growth/integration_repaired/generated/checks.scad>
include <parts.scad>
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
 for(p=thermal_feet_xy)translate([p[0],p[1],-12.00002])cylinder(d=3.02,h=5.80004,$fn=64);
}}
module eb_base(){thermal_metal_base();}
module eb_metal(){eb_base();eb_feet_assembly();}
module eb_interfaces(){thermal_pads(6.5);thermal_shims(.2);}
module eb_lower(){lower_shell_fasteners();}
module eb_case_and_lid(){ui_shell();tc2_posts();rear_panel();ui_lid();}
module eb_other_hardware(){return_assembly();import("/Users/axelmckrnna/dev/rmx-publish/hardware/cad/a12/thermal/enlarged_base_pot/context/hardware/cad/a12/positive_links/generated/positive-links.stl");ui_h9_head();tc2_heads();}
module eb_bearing_shifted_lower(){translate([0,0,.00002])eb_lower();}
module eb_screw_tip_control(){intersection(){eb_foot_screws();translate([19.9,19.9,-10])cube([.2,.2,.2]);}}
module eb_newfront_witness(){translate([166.9,180.3,-3])cube([.2,.2,.2]);}
module eb_case_newbolt_witness(){translate([166.9,180.3,8])cube([.2,.2,.2]);}
if(eb_case=="metal_geometry")eb_base();
if(eb_case=="standalone_metal_geometry")eb_part_metal_base();
if(eb_case=="feet_geometry")thermal_feet();
if(eb_case=="feet_assembly_geometry")eb_feet_assembly();
if(eb_case=="carrier_geometry"){ui_shell();tc2_posts();}
if(eb_case=="attachment_geometry"){eb_lower();eb_foot_screws();}
if(eb_case=="assembly_geometry"){eb_metal();eb_interfaces();eb_lower();eb_foot_screws();eb_case_and_lid();ui_electronics();ui_controls();eb_other_hardware();pf_wires();ui_all_joints();}
if(eb_case=="interface_geometry")eb_interfaces();
if(eb_case=="interface_carrier_collision")intersection(){eb_interfaces();ui_shell();}
if(eb_case=="interface_components_collision")intersection(){eb_interfaces();ui_components();}
if(eb_case=="interface_PCB_seat_collision")intersection(){translate([0,0,-.00002])eb_interfaces();ui_PCBS();}
if(eb_case=="interface_other_hardware_collision")intersection(){eb_interfaces();union(){eb_lower();eb_other_hardware();}}
if(eb_case=="interface_wire_controls_collision")intersection(){eb_interfaces();union(){pf_wires(.25);ui_all_joints(.25);ui_controls_and_lid();}}
if(eb_case=="interface_positive_control")intersection(){eb_interfaces();translate([270,134,5.5])cube([.2,.2,.2]);}
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
module ps_knob(d,h,bore=6.2) {
    difference() {
        cylinder(d=d,h=h);
        for(a=[0:360/32:359]) rotate([0,0,a]) translate([d/2,0,0.8]) cylinder(d=0.8,h=h-1.6,$fn=12);
        translate([0,0,-0.1]) cylinder(d=bore,h=min(10,h-2)+0.1);
        translate([0,0,-0.1]) cylinder(d1=bore+0.8,d2=bore,h=0.7);
        translate([0,0,3]) rotate([0,90,0]) cylinder(d=2.5,h=d/2+1);
        translate([6,0,3]) rotate([0,90,0]) cylinder(d=4,h=d/2);
        translate([-0.45,-d/2+1,h-0.5]) cube([0.9,d*0.32,0.6]);
    }
}
module ps_mechanisms_without_knobs(){translate([0,0,7.6]){lever_bracket();lever_sweep();}translate([0,0,panel_z-guide_thick])guide_plate();touch_backer();for(b=buttons)button_pose(b){switch_holder(b);key_sweep(b);}a12_switch_electronics();for(c=caps)if(c[1]=="switch")translate([c[2],c[3],panel_z])selector_cap();}
module ps_other_controls(){ps_mechanisms_without_knobs();ui_optics();}
ps_centres=[[18, 27], [114, 27], [52, 78], [108, 78], [164, 78], [244, 78], [18, 133], [53, 133], [194, 133], [295, 133]];

ps_case="stack";
module ps_body(m=0){for(p=ps_centres)translate([p[0]-8-m,p[1]-8-m,27.7-.2-m])cube([16+2*m,16+2*m,43.59998-(27.7-.2-m)]);}
// Actual mounting faces are correlated at panelbottom43.6; no top Z clearance
// is applied through their own intended shoulder seat.
module ps_bushing(d=9,lo=43.6,hi=48.6){translate([0,0,lo])cylinder(d=d/cos(180/128),h=hi-lo,$fn=128);}
module ps_hardware_max(){ps_bushing(9.1,43.5,48.9);translate([0,0,45.4])difference(){cylinder(d=16,h=.9,$fn=128);cylinder(d=8.8,h=1,$fn=128);}translate([0,0,45.8])difference(){cylinder(d=11.5/cos(30),h=2.7,$fn=6);cylinder(d=8.8,h=3,$fn=128);}}
module ps_shaft_max(){hull()for(x=[-.05,.05],y=[-.05,.05])translate([x,y,48.9])cylinder(d=6/cos(180/128),h=7.1,$fn=128);}
module ps_local_knob(i=0,low=false){translate([0,0,low?49.1:49.2])ps_knob([16,17,29,32][i],[13,15,18,18][i]);}
module ps_bearing(axis=3,base=49.3){translate([1.4,-.1,base+axis-.05-1.5])cube([.2,.2,3.1]);}
module ps_exposed_shaft_band(){translate([1.3,-.2,49.15])cube([.4,.4,54.15-49.15]);}
module ps_thread_registration(m=.1){hull()for(x=[-m,m],y=[-m,m])translate([x,y,43.55])cylinder(d=9.11/cos(180/128),h=2.3,$fn=128);}
if(ps_case=="body_geometry")ps_body();
if(ps_case=="panel_geometry")ui_lid();
if(ps_case=="stack"){ps_body();for(k=knobs)translate([k[1],k[2],0]){ps_hardware_max();ps_shaft_max();translate([0,0,49.2])ps_knob(k[3],k[4]);}}
if(ps_case=="body_other_electronics_collision")intersection(){ps_body(.25);ui_electronics(false,false);}
if(ps_case=="body_controls_collision")intersection(){ps_body(.25);ui_controls();}
if(ps_case=="body_case_collision")intersection(){ps_body(.25);ui_case_and_lid();}
if(ps_case=="body_power_wire_collision")intersection(){ps_body(.25);union(){ui_power_only();pf_wires(.25);ui_all_joints(.25);ui_h9_head();tc2_posts();tc2_heads();}}
if(ps_case=="new_knobs_environment_collision")for(k=knobs)intersection(){translate([k[1],k[2],49.1])ps_knob(k[3],k[4]);union(){ui_electronics();ui_power_only();ui_case_and_lid();ps_body();}}
if(ps_case=="new_knobs_other_controls_collision")for(k=knobs)intersection(){translate([k[1],k[2],49.1])ps_knob(k[3],k[4]);ps_other_controls();}
if(ps_case=="hardware_other_components_collision")for(p=ps_centres)intersection(){translate([p[0],p[1],0])ps_hardware_max();union(){ui_electronics(false,false);cp_other_pot_bodies(p);ui_power_only();ps_other_controls();pf_wires(.25);ui_all_joints(.25);}}
if(ps_case=="knobs_mutual_collision")for(i=[0:len(knobs)-1],j=[0:len(knobs)-1])if(i<j)intersection(){translate([knobs[i][1],knobs[i][2],49.2])ps_knob(knobs[i][3],knobs[i][4]);translate([knobs[j][1],knobs[j][2],49.2])ps_knob(knobs[j][3],knobs[j][4]);}
if(ps_case=="thread_panel_registration_collision")for(p=ps_centres)intersection(){translate([p[0],p[1],0])ps_thread_registration();ui_lid();}
if(ps_case=="thread_panel_20percent_sensitivity_collision")for(p=ps_centres)intersection(){translate([p[0],p[1],0])ps_thread_registration(.12);ui_lid();}
if(ps_case=="old_bore_blocked_witness")intersection(){ps_thread_registration();translate([0,0,43.6])difference(){translate([-10,-10,0])cube([20,20,2]);translate([0,0,-.01])cylinder(d=9.3,h=2.02,$fn=48);}}
if(ps_case=="old_bushing_knob_blocked_witness")intersection(){ps_bushing();translate([0,0,48.4])knob(16,13);}
if(ps_case=="old_bearing_outside_shaft_witness")difference(){ps_bearing(6,48.4);ps_exposed_shaft_band();}
if(ps_case=="new_bearing_axial_collision")difference(){ps_bearing();ps_exposed_shaft_band();}
if(ps_case=="body_positive_control")intersection(){ps_body();translate([17.9,26.9,30])cube([.2,.2,.2]);}
if(ps_case=="hardware_positive_control")intersection(){ps_hardware_max();translate([3.9,-.1,47])cube([.2,.2,.2]);}
if(ps_case=="bearing_positive_control")intersection(){ps_bearing();translate([1.4,-.1,52])cube([.2,.2,.2]);}
for(i=[0:3]){
 if(ps_case==str("knob_",i))ps_knob([16,17,29,32][i],[13,15,18,18][i]);
 if(ps_case==str("shaft_knob_",i,"_collision"))intersection(){ps_shaft_max();ps_local_knob(i,true);}
 if(ps_case==str("hardware_knob_",i,"_collision"))intersection(){ps_hardware_max();ps_local_knob(i,true);}
}

// CP01 additional own-contact contracts. All dimensions are source requirements.
module cp_other_pot_bodies(p){for(q=ps_centres)if(q!=p)translate([q[0]-8,q[1]-8,27.5])cube([16,16,43.59998-27.5]);}
module cp_pot_hardware(){for(p=ps_centres)translate([p[0],p[1],0]){ps_hardware_max();ps_shaft_max();}}
if(cp_case=="pot_hardware_review")cp_pot_hardware();
if(cp_case=="body_base_all_collision")intersection(){ps_body(.25);union(){eb_metal();eb_interfaces();eb_lower();eb_foot_screws();}}
if(cp_case=="receivers_base_all_collision")intersection(){cp_pot_hardware();union(){eb_metal();eb_interfaces();eb_lower();eb_foot_screws();}}
if(cp_case=="body_interface_positive_control")intersection(){ps_body();translate([193.9,132.9,30])cube([.2,.2,.2]);}
