include </Users/axelmckrnna/dev/rmx-publish/hardware/cad/a12/thermal/enlarged_base_pot/context/hardware/cad/a12/pot_stack/generated/context-derived.scad>
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
if(ps_case=="body_other_electronics_collision")intersection(){ps_body(.25);ui_electronics();}
if(ps_case=="body_controls_collision")intersection(){ps_body(.25);ui_controls();}
if(ps_case=="body_case_collision")intersection(){ps_body(.25);ui_case_and_lid();}
if(ps_case=="body_power_wire_collision")intersection(){ps_body(.25);union(){ui_power_only();pf_wires(.25);ui_all_joints(.25);ui_h9_head();tc2_posts();tc2_heads();}}
if(ps_case=="new_knobs_environment_collision")for(k=knobs)intersection(){translate([k[1],k[2],49.1])ps_knob(k[3],k[4]);union(){ui_electronics();ui_power_only();ui_case_and_lid();ps_body();}}
if(ps_case=="new_knobs_other_controls_collision")for(k=knobs)intersection(){translate([k[1],k[2],49.1])ps_knob(k[3],k[4]);ps_other_controls();}
if(ps_case=="hardware_other_components_collision")for(p=ps_centres)intersection(){translate([p[0],p[1],0])ps_hardware_max();union(){ui_electronics();ui_power_only();ps_other_controls();pf_wires(.25);ui_all_joints(.25);}}
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
