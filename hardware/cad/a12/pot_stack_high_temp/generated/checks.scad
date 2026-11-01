include </Users/axelmckrnna/dev/rmx-publish/hardware/cad/a12/pot_stack_high_temp/model/context-derived.scad>
// HT01 source-backed receiving bounds, not a vendor STEP or fabricated assembly.
ht_case="none";
ht_i=0;
ht_family=0;
module ht_one_pocket(){translate([-1.2,5.1,43.59998])cube([2.4,1.8,1.10002]);}
module ht_lug_pockets(){for(p=ps_centres)translate([p[0],p[1],0])ht_one_pocket();}
module ht_lug(m=0){translate([-1.05-m,5.3-m,43.5])cube([2.1+2*m,1.4+2*m,1.0]);}
module ht_local_body(m=0){
 // Includes actual required substrate and complete allocated rear-tail/solder reserve.
 translate([-8-m,-8-m,29.4-m])cube([16+2*m,16+2*m,43.59998-(29.4-m)]);
}
module ht_bushing(){translate([0,0,43.5])cylinder(d=9.1/cos(180/128),h=5.4,$fn=128);}
module ht_hardware(){
 ht_bushing();
 translate([0,0,45.5])difference(){cylinder(d=14.2,h=.9,$fn=128);cylinder(d=8.8,h=1,$fn=128);}
 translate([0,0,45.9])difference(){cylinder(d=11.2/cos(30),h=2.7,$fn=6);cylinder(d=8.8,h=3,$fn=128);}
}
module ht_shaft(){hull()for(x=[-.05,.05],y=[-.05,.05])translate([x,y,48.9])cylinder(d=6/cos(180/128),h=10,$fn=128);}
module ht_grub_gauge(axis=5){translate([1.4,-.1,49.1+axis-.05-1.55])cube([.2,.2,3.4]);}
module ht_flat_allowed(){translate([1.3,-.2,52.35])cube([.4,.4,57.25-52.35]);}
module ht_lug_registered(m=.1){hull()for(x=[-m,m],y=[-m,m])translate([x,y,0])ht_lug(.005);}
module ht_other_power(){eb_metal();eb_interfaces();eb_lower();eb_foot_screws();ui_power_only();fi_tray();fi_guards();fi_spacers();fi_fans();fi_fan_fasteners();}
module ht_substrate(){difference(){
 translate([-8,-8,32])cube([16,16,1.6]);
 for(x=[-2.5,0,2.5])translate([x,6.5,31.99])cylinder(d=1.1,h=1.62,$fn=48);
 for(x=[-5.65,5.65])translate([x-1,-1-.6,31.99])cube([2,1.2,1.62]);
}}
module ht_all_knobs(){for(k=knobs)translate([k[1],k[2],49.2])ps_knob(k[3],k[4]);}
module ht_body_controls(){intersection(){ps_body(.25);ps_other_controls();}}
module ht_local_round_panel(){difference(){translate([-10,-10,43.6])cube([20,20,2]);translate([0,0,43.59])cylinder(d=9.5,h=2.02,$fn=48);}}
module ht_local_slotted_panel(){difference(){ht_local_round_panel();ht_one_pocket();}}
if(ht_case=="old_panel_lug_collision_witness")intersection(){ht_lug_registered();ht_local_round_panel();}
if(ht_case=="new_panel_lug_collision")intersection(){ht_lug_registered();ht_local_slotted_panel();}
if(ht_case=="new_panel_lug_20percent_collision")intersection(){ht_lug_registered(.12);ht_local_slotted_panel();}
if(ht_case=="all_lugs_panel_collision")intersection(){for(p=ps_centres)translate([p[0],p[1],0])ht_lug_registered(.12);ui_lid();}
if(ht_case=="thread_panel_collision")for(p=ps_centres)intersection(){translate([p[0],p[1],0])ps_thread_registration(.12);ui_lid();}
if(ht_case=="old_axis_flat_failure_witness")difference(){ht_grub_gauge(3);ht_flat_allowed();}
if(ht_case=="new_axis_flat_collision")difference(){ht_grub_gauge();ht_flat_allowed();}
// This is the requested1mm axial end-clearance gauge, not extra shaft material.
if(ht_case=="old_bore_clearance_failure_witness")intersection(){translate([-.1,-.1,58.9])cube([.2,.2,1]);translate([0,0,49.1])difference(){cylinder(d=16,h=13);translate([0,0,-.1])cylinder(d=6.2,h=10.1);}}
if(ht_case=="new_knobs_environment_collision")intersection(){ht_all_knobs();union(){ui_electronics(false,false);ht_other_power();ui_case_and_lid();ps_body();}}
if(ht_case=="new_knobs_controls_collision")intersection(){ht_all_knobs();ps_other_controls();}
if(ht_case=="body_electronics_collision")intersection(){ps_body(.25);ui_electronics(false,false);}
if(ht_case=="body_controls_collision")ht_body_controls();
if(ht_case=="body_case_collision")intersection(){ps_body(.25);ui_case_and_lid();}
if(ht_case=="body_power_collision")intersection(){ps_body(.25);ht_other_power();}
if(ht_case=="body_wire_collision")intersection(){ps_body(.25);union(){pf_wires(.25);ui_all_joints(.25);}}
if(ht_case=="body_geometry")ps_body();
if(ht_case=="substrate_geometry")ht_substrate();
if(ht_case=="panel_geometry")ui_lid();
if(ht_case=="hardware_geometry")ht_hardware();
if(ht_case=="stack_review"){ps_body();for(p=ps_centres)translate([p[0],p[1],0]){ht_hardware();ht_shaft();}ht_all_knobs();}
if(ht_case=="body_positive_control")intersection(){ps_body();translate([17.9,26.9,33])cube([.2,.2,.2]);}
if(ht_case=="substrate_positive_control")intersection(){ht_substrate();translate([-.1,-.1,32.7])cube([.2,.2,.2]);}
if(ht_case=="lug_positive_control")intersection(){ht_lug();translate([-.1,5.9,43.8])cube([.2,.2,.2]);}
if(ht_case=="pocket_void_control")intersection(){ht_local_slotted_panel();translate([-.1,5.9,43.8])cube([.2,.2,.2]);}
module ht_hardware_pair(i,f){
 p=ps_centres[i];
 intersection(){
  translate([p[0],p[1],0])ht_hardware();
  if(f==0)ui_electronics(false,false);
  if(f==1)cp_other_pot_bodies(p);
  if(f==2)ht_other_power();
  if(f==3)ps_other_controls();
  if(f==4)pf_wires(.25);
  if(f==5)ui_all_joints(.25);
 }
}
if(ht_case=="hardware_environment_pair")ht_hardware_pair(ht_i,ht_family);
if(ht_case=="hardware_index_control"){
 p=ps_centres[ht_i];
 intersection(){translate([p[0],p[1],0])ht_hardware();translate([p[0]+3.9,p[1]-.1,47])cube([.2,.2,.2]);}
}
for(i=[0:3]){
 if(ht_case==str("knob_",i))ps_knob([16,17,29,32][i],[13,15,18,18][i]);
 if(ht_case==str("shaft_knob_",i,"_collision"))intersection(){ht_shaft();ps_local_knob(i,true);}
 if(ht_case==str("hardware_knob_",i,"_collision"))intersection(){ht_hardware();ps_local_knob(i,true);}
}
