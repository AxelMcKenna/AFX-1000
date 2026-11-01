include </Users/axelmckrnna/dev/rmx-publish/hardware/cad/a12/thermal/interior_airpath_meter318/model/ht-checks.scad>
include <source-tray.scad>
// AP02 actual conditional mechanical prototype; no installed seal/flow guarantee.
ap_case="none";
ap_fans=[[80,165.5],[254,165.5]];
ap_feet=[[20,20],[314,20],[20,168.4],[314,168.4]];
ap_bays=[[36,137,112,188.4],[229.5,137,278.5,188.4]];
module ap_round(w,d,r){hull()for(x=[r,w-r],y=[r,d-r])translate([x,y])circle(r=r,$fn=96);}
module ap_ports_2d(){
 difference(){translate([38,164])ap_round(72,19,1);translate([93.0871,168.9352])circle(r=6,$fn=256);}
 translate([231.5,154])ap_round(45,29,1);
}
module ap_port_cuts(){translate([0,0,-6.3])linear_extrude(9.10002)ap_ports_2d();}
// Named test-only interior: exact cut boundaries audited to15.2553nm binary32
// roundoff. Parent approved20nmXY/Ztestguard; actual openings unchanged.
module ap_port_void_interior(){translate([0,0,-6.19998])linear_extrude(8.99996)offset(delta=-.00002)ap_ports_2d();}
module ap_exhaust_cuts(){for(i=[0:17])translate([-.1,40+5.5*i,5])rotate([90,0,90])linear_extrude(3.2)ap_round(4,36,1.5);}
module ap_top_seal_2d(){for(b=ap_bays)difference(){translate([b[0],b[1]])square([b[2]-b[0],b[3]-b[1]]);translate([b[0]+2,b[1]+2])square([b[2]-b[0]-4,b[3]-b[1]-4]);}}
module ap_upper_gaskets(){translate([0,0,-6.7])linear_extrude(.5)ap_top_seal_2d();}
module ap_meter_orifices(w=16){for(p=ap_fans)translate([p[0],142,-22])rotate([90,0,0])linear_extrude(11)translate([-w/2,0])ap_round(w,10,1);}
module ap_baffles(){difference(){
 for(b=ap_bays)translate([0,0,-24.7])linear_extrude(18)difference(){
  translate([b[0],b[1]])square([b[2]-b[0],b[3]-b[1]-2]);
  translate([b[0]+2,b[1]+2])square([b[2]-b[0]-4,b[3]-b[1]]);
 }
 ap_meter_orifices(16);
 for(p=ap_fans)for(x=[-7,7])translate([p[0]+x,136.99,-8.9])rotate([-90,0,0])cylinder(d=2.4,h=2.02,$fn=48);
 for(x=[46,235.5])translate([x,136.99,-10])rotate([-90,0,0])cylinder(d=4.4,h=2.02,$fn=96);
}}
module ap_land_2d(){projection()import("nominal-frame-land.stl");}
module ap_common_land_2d(){projection()import("nominal-common-land.stl");}
module ap_bearing_disks_2d(){for(x=[-16,16],y=[-16,16])translate([x,y])circle(r=3.1,$fn=96);}
module ap_frame_gaskets(){for(p=ap_fans)translate([p[0],p[1],-25.2])linear_extrude(.5)difference(){ap_land_2d();ap_bearing_disks_2d();}}
module ap_frame_recess(){for(p=ap_fans)translate([p[0],p[1],-25.2])linear_extrude(.50002)difference(){offset(delta=.1)ap_land_2d();ap_bearing_disks_2d();}}
// The cutter fully overlaps the already-lowered baffle tops. Avoid a10nm
// nearcoincidentY186.39999/186.4 sliver in the manufactured tray mesh.
module ap_front_seal_recess(){for(b=ap_bays)translate([b[0]-.01,185.9,-6.7])cube([b[2]-b[0]+.02,2.6,.50002]);}
module ap_tray(){difference(){union(){ap_source_tray();ap_baffles();}ap_frame_recess();ap_front_seal_recess();}}
module ap_guard_slots_2d(){intersection(){circle(d=37.5,$fn=256);union(){for(x=[-15:5:15])translate([x-2,-20])square([4,40]);}}}
module ap_one_guard(){difference(){translate([-22,-22,-27.7])linear_extrude(1)ap_round(44,44,3);
 translate([0,0,-27.71])linear_extrude(1.02)ap_guard_slots_2d();
 for(x=[-16,16],y=[-16,16])translate([x,y,-27.71])cylinder(d=4.4,h=1.02);
}}
module ap_guards(){for(p=ap_fans)translate([p[0],p[1],0])ap_one_guard();}
module ap_fan(t=10.4){difference(){translate([-20.25,-20.25,-24.7])cube([40.5,40.5,t]);for(x=[-16,16],y=[-16,16])translate([x,y,-24.71])cylinder(d=4,h=t+.02,$fn=128);}}
module ap_fans_assembly(t=10.4){for(p=ap_fans)translate([p[0],p[1],0])ap_fan(t);}
module ap_shims(t=10.4){for(p=ap_fans)translate([p[0],p[1],-24.7+t])linear_extrude(12.5-t)difference(){ap_common_land_2d();for(x=[-16,16],y=[-16,16])translate([x,y])circle(d=4.4,$fn=128);}}
module ap_fan_stress(){for(p=ap_fans)translate([p[0]-20.55,p[1]-20.55,-24.7])cube([41.1,41.1,12.5]);}
module ap_seal_washers(){for(p=ap_fans)for(x=[-16,16],y=[-16,16])translate([p[0]+x,p[1]+y,-28.2])difference(){cylinder(d=5.5,h=.5,$fn=96);translate([0,0,-.01])cylinder(d=3.4,h=.52,$fn=128);}}
module ap_fasteners(){for(p=ap_fans)for(x=[-16,16],y=[-16,16])translate([p[0]+x,p[1]+y,0]){
 // Prototype M3x20head bears DIRECTLY on sealwasher; no drywasher bypass.
 translate([0,0,-31.2])cylinder(d=6,h=3,$fn=96);
 translate([0,0,-28.2])cylinder(d=3.1,h=20,$fn=128);
 for(z=[-26.7,-12.2])translate([0,0,z])difference(){cylinder(d=7.4,h=.5,$fn=96);cylinder(d=3.4,h=.51,$fn=128);}
 translate([0,0,-11.7])difference(){cylinder(d=6.8,h=2.6,$fn=6);cylinder(d=3.12,h=2.61,$fn=128);}
}}
module ap_hardware_stress(){for(p=ap_fans)for(x=[-16,16],y=[-16,16])translate([p[0]+x,p[1]+y,-31.20002])cylinder(r=(3.7+sqrt(2)*.275+.005)/cos(180/128),h=23.00004,$fn=128);}
module ap_meter_plates(){difference(){for(p=ap_fans)translate([p[0]-10,134.5,-24.2])cube([20,2,17.5]);ap_meter_orifices();
 for(p=ap_fans)for(x=[-7,7])translate([p[0]+x,134.49,-8.9])rotate([-90,0,0])cylinder(d=2.4,h=2.02,$fn=48);
}}
module ap_meter_gaskets(){difference(){for(p=ap_fans)translate([p[0]-10,136.5,-24.2])cube([20,.5,17.5]);ap_meter_orifices(16);
 for(p=ap_fans)for(x=[-7,7])translate([p[0]+x,136.49,-8.9])rotate([-90,0,0])cylinder(d=2.4,h=.52,$fn=48);
}}
module ap_meter_fasteners(){for(p=ap_fans)for(x=[-7,7])translate([p[0]+x,134,-8.9])rotate([-90,0,0]){
 translate([0,0,-2.6])cylinder(d=4.4,h=2.6,$fn=96);
 cylinder(d=2.1,h=8,$fn=96);
 translate([0,0,5])difference(){cylinder(d=4.7/cos(30),h=1.6,$fn=6);cylinder(d=2.2,h=1.61,$fn=96);}
}}
module ap_meter_seal_washers(){for(p=ap_fans)for(x=[-7,7])translate([p[0]+x,134,-8.9])rotate([-90,0,0])difference(){cylinder(d=4,h=.5,$fn=96);translate([0,0,-.01])cylinder(d=2.3,h=.52,$fn=96);}}
// Receiving gauge for a FULLY FILLED lead/encapsulant composite. Actualthree
// 26AWGleadODs/resin/retention/curing/leakprocess remain unselected/unproved.
module ap_feedthroughs(){for(x=[46,235.5])translate([x,137,-10])rotate([-90,0,0]){
 cylinder(d=4.4,h=2,$fn=96);
 translate([0,0,-1.5])cylinder(d=6,h=1.5,$fn=96);
 translate([0,0,2])cylinder(d=6,h=.6,$fn=96);
}}
module ap_added(){ap_upper_gaskets();ap_frame_gaskets();ap_shims();ap_seal_washers();ap_meter_plates();ap_meter_gaskets();ap_meter_fasteners();ap_meter_seal_washers();ap_feedthroughs();}
module ap_everything_added(){ap_tray();ap_guards();ap_fans_assembly();ap_fasteners();ap_added();}
module ap_shank_sweep(m,z,h){for(p=ap_fans)for(x=[-16,16],y=[-16,16])hull()for(dx=[-m,m],dy=[-m,m])translate([p[0]+x+dx,p[1]+y+dy,z])cylinder(r=1.555/cos(180/128),h=h,$fn=128);}
module ap_nominal_boundary_faces(){
 for(b=ap_bays){
  for(x=[b[0]+1,b[2]-1])translate([x,b[1]+1,-24.69])cube([.02,b[3]-b[1]-2,18.48]);
  for(y=[b[1]+1,b[3]-1])translate([b[0]+1,y,-24.69])cube([b[2]-b[0]-2,.02,18.48]);
  difference(){
   translate([b[0]+2,b[1]+2,-6.19])cube([b[2]-b[0]-4,b[3]-b[1]-4,.02]);
   ap_port_cuts();
  }
  difference(){
   translate([b[0]+2,b[1]+2,-26.19])cube([b[2]-b[0]-4,b[3]-b[1]-4,.02]);
   for(p=ap_fans){
    translate([p[0],p[1],-26.2])cylinder(d=37.5,h=.05,$fn=96);
    for(x=[-16,16],y=[-16,16])translate([p[0]+x,p[1]+y,-26.2])cylinder(d=4.4,h=.05,$fn=96);
   }
  }
 }
}
module ap_boundary_test_faces(){difference(){
 ap_nominal_boundary_faces();
 // Declared active rear meter ports and sealed bolt penetrations remain
 // separate interfaces; this check does not assert installed leak tightness.
 ap_meter_orifices(16);
 for(p=ap_fans)for(x=[-7,7])translate([p[0]+x,136.99,-8.9])rotate([-90,0,0])cylinder(d=2.4,h=2.02,$fn=48);
}}
module ap_scene_obstacles(f=0){
 if(f==0)ui_electronics(false,false);
 if(f==1){ps_body();cp_pot_hardware();}
 if(f==2)ps_other_controls();
 if(f==3){ui_power_only();ui_h9_head();tc2_posts();tc2_heads();eb_lower();}
 if(f==4){pf_wires(.25);ui_all_joints(.25);}
}
if(ap_case=="inlet_area_gauge")linear_extrude(.1)ap_ports_2d();
if(ap_case=="exhaust_area_gauge")linear_extrude(.1)ap_round(4,36,1.5);
if(ap_case=="guard_area_gauge")linear_extrude(.1)ap_guard_slots_2d();
if(ap_case=="base_geometry")thermal_metal_base();
if(ap_case=="carrier_geometry"){ui_shell();tc2_posts();}
if(ap_case=="tray_geometry")ap_tray();
if(ap_case=="guard_geometry")ap_guards();
if(ap_case=="upper_gasket_geometry")ap_upper_gaskets();
if(ap_case=="frame_gasket_geometry")ap_frame_gaskets();
if(ap_case=="shim_geometry")ap_shims();
if(ap_case=="meter_plate_geometry")ap_meter_plates();
if(ap_case=="meter_gasket_geometry")ap_meter_gaskets();
if(ap_case=="meter_fastener_receiving")ap_meter_fasteners();
if(ap_case=="fan_receiving_geometry")ap_fans_assembly();
if(ap_case=="feedthrough_receiving_geometry")ap_feedthroughs();
if(ap_case=="fastener_seal_geometry"){ap_seal_washers();ap_meter_seal_washers();}
if(ap_case=="inlet_solid_void_collision")intersection(){ap_port_void_interior();union(){thermal_metal_base();ui_shell();tc2_posts();}}
if(ap_case=="void_fixture_metal_level_control")intersection(){ap_port_void_interior();translate([39.9,169.9,-3])cube([.2,.2,.2]);}
if(ap_case=="void_fixture_floor_level_control")intersection(){ap_port_void_interior();translate([39.9,169.9,1])cube([.2,.2,.2]);}
if(ap_case=="exhaust_solid_void_collision")intersection(){ap_exhaust_cuts();ui_shell();}
if(ap_case=="old_plate_blockage_control")intersection(){ap_old_metal_base();translate([39.9,169.9,-3])cube([.2,.2,.2]);}
if(ap_case=="old_floor_blockage_control")intersection(){ap_old_carrier();translate([39.9,169.9,1])cube([.2,.2,.2]);}
if(ap_case=="old_wall_blockage_control")intersection(){ap_old_carrier();translate([.9,41.9,19.9])cube([.2,.2,.2]);}
if(ap_case=="protected_post_island_metal_control")intersection(){thermal_metal_base();translate([92.9871,168.8352,-3])cube([.2,.2,.2]);}
if(ap_case=="protected_post_island_floor_control")intersection(){ui_shell();translate([92.9871,168.8352,1])cube([.2,.2,.2]);}
if(ap_case=="post_island_join_control")intersection(){thermal_metal_base();translate([92.9871,163.7,-3])cube([.2,.2,.2]);}
if(ap_case=="new_pin_void_collision")intersection(){thermal_metal_base();translate([39.9,144.9,-12])cube([.2,.2,.2]);}
if(ap_case=="retained_pin_control")intersection(){thermal_metal_base();translate([39.9,130.9,-12])cube([.2,.2,.2]);}
if(ap_case=="floating_fan_hole_collision")intersection(){ap_shank_sweep(.275,-24.69998,10.49996);ap_fans_assembly(10.5);}
if(ap_case=="floating_tray_hole_collision")intersection(){ap_shank_sweep(.275,-26.19998,1.49996);ap_tray();}
if(ap_case=="floating_guard_hole_collision")intersection(){ap_shank_sweep(.375,-27.69998,.99996);ap_guards();}
if(ap_case=="floating_shim_hole_collision")intersection(){ap_shank_sweep(.295,-14.29998,2.09996);ap_shims();}
if(ap_case=="fixed_axis_hole_failure_witness")intersection(){ap_shank_sweep(.55,-24.69998,10.49996);ap_fans_assembly(10.5);}
// Approved named test-only20nmshim-up shifts exclude ONLY the correlated
// fan/shim seat planes. Raw5064/5080plane-onlytriangles are preserved.
if(ap_case=="matched_shim_min_collision")intersection(){ap_fans_assembly(10);translate([0,0,.00002])ap_shims(10);}
if(ap_case=="matched_shim_max_collision")intersection(){ap_fans_assembly(10.5);translate([0,0,.00002])ap_shims(10.5);}
if(ap_case=="minimum_contact_positive_control")intersection(){ap_fans_assembly(10);translate([0,0,-.05])ap_shims(10);translate([79.8,184.7,-14.74])cube([.4,.4,.02]);}
if(ap_case=="maximum_contact_positive_control")intersection(){ap_fans_assembly(10.5);translate([0,0,-.05])ap_shims(10.5);translate([79.8,184.7,-14.24])cube([.4,.4,.02]);}
if(ap_case=="nominal_pressure_boundary_void_collision")difference(){ap_boundary_test_faces();union(){ap_tray();ap_upper_gaskets();thermal_metal_base();ap_feedthroughs();}}
if(ap_case=="missing_feedthrough_failure_witness")difference(){ap_boundary_test_faces();union(){ap_tray();ap_upper_gaskets();thermal_metal_base();}}
if(ap_case=="feedthrough_fan_collision")intersection(){ap_feedthroughs();ap_fan_stress();}
if(ap_case=="feedthrough_pin_collision")intersection(){ap_feedthroughs();thermal_metal_base();}
if(ap_case=="feedthrough_positive_control")intersection(){ap_feedthroughs();translate([45.9,137.9,-10.1])cube([.2,.2,.2]);}
if(ap_case=="old_open_plenum_failure_witness")difference(){ap_boundary_test_faces();union(){ap_source_tray();thermal_metal_base();}}
if(ap_case=="meter_border_positive_control")intersection(){ap_meter_plates();translate([83.9,135,-15])cube([.2,.2,.2]);}
if(ap_case=="fan_baffle_collision")intersection(){ap_fan_stress();ap_baffles();}
if(ap_case=="meter_fan_collision")intersection(){union(){ap_meter_plates();ap_meter_gaskets();ap_meter_fasteners();ap_meter_seal_washers();}ap_fan_stress();}
if(ap_case=="pins_baffle_collision")intersection(){ap_baffles();thermal_metal_base();}
if(ap_case=="meter_pins_collision")intersection(){union(){ap_meter_plates();ap_meter_gaskets();ap_meter_fasteners();ap_meter_seal_washers();}thermal_metal_base();}
if(ap_case=="fan_tray_collision")intersection(){translate([0,0,.00002])ap_fan_stress();ap_tray();}
if(ap_case=="tray_base_collision")intersection(){translate([0,0,-.00002])ap_tray();thermal_metal_base();}
if(ap_case=="new_added_case_collision")intersection(){ap_added();union(){ui_shell();ui_lid();rear_panel();}}
for(f=[0:4])if(ap_case==str("new_added_obstacle_",f))intersection(){ap_everything_added();ap_scene_obstacles(f);}
// Complete currently modeled scene families, separate objects in3MF. Bounds,
// reserves and opaque receiving composites are explicitly REVIEW ONLY.
if(ap_case=="assembly_feet")render(){eb_feet_assembly();eb_foot_screws();}
if(ap_case=="assembly_lower_hardware")render()eb_lower();
if(ap_case=="assembly_lid")render()ui_lid();
if(ap_case=="assembly_rear")render()rear_panel();
if(ap_case=="assembly_electronics")render()ui_electronics(false,false);
if(ap_case=="assembly_controls")render()ui_controls();
if(ap_case=="assembly_pots")render(){ps_body();cp_pot_hardware();}
if(ap_case=="assembly_power")render()eb_other_hardware();
if(ap_case=="assembly_wires")render(){pf_wires(0);ui_all_joints(0);}
if(ap_case=="assembly_TIM_shims")render()eb_interfaces();
if(ap_case=="assembly_foot_spacers")render()fi_spacers();
if(ap_case=="assembly_all_gaskets")render(){ap_upper_gaskets();ap_frame_gaskets();ap_seal_washers();ap_meter_gaskets();ap_meter_seal_washers();}
if(ap_case=="assembly_fan_fasteners")render()ap_fasteners();
if(ap_case=="assembly_meter_hardware")render(){ap_meter_plates();ap_meter_fasteners();}

// AP03 source-derived approach gauges. No aerodynamic guarantee.
module ap3_gap_core(){for(p=ap_fans)translate([p[0]-20,139,-22])cube([40,5.95,9.8]);}
module ap3_approach_top(){for(p=ap_fans)translate([p[0]-20,139,-12.21])cube([40,5.95,.01]);}
module ap3_moving_parts(){ap_baffles();ap_upper_gaskets();ap_meter_plates();ap_meter_gaskets();ap_meter_fasteners();ap_meter_seal_washers();ap_feedthroughs();}
if(ap_case=="new_aperture_area")translate([0,0,0])linear_extrude(.1)ap_round(16,10,1);
if(ap_case=="approach_core_solid_intersection")intersection(){ap3_gap_core();union(){ap_baffles();ap_fan_stress();ap_meter_plates();ap_meter_gaskets();ap_meter_fasteners();ap_meter_seal_washers();ap_feedthroughs();thermal_metal_base();}}
if(ap_case=="approach_top_intrusion")intersection(){ap3_approach_top();ap_feedthroughs();}
if(ap_case=="new_meter_to_bolt_seal_collision")intersection(){ap_meter_orifices();union(){ap_meter_fasteners();ap_meter_seal_washers();}}
if(ap_case=="new_aperture_interior_blockage")intersection(){for(p=ap_fans)translate([p[0],139.01,-21.99998])rotate([90,0,0])linear_extrude(4.49)offset(delta=-.00002)translate([-8,0])ap_round(16,9.99996,1);union(){ap_baffles();ap_meter_plates();ap_meter_gaskets();}}
if(ap_case=="approach_core_positive_control")intersection(){ap3_gap_core();translate([79.9,141,-18])cube([.2,.2,.2]);}
if(ap_case=="new_meter_border_control")intersection(){ap_meter_plates();translate([88.9,135,-18])cube([.2,.2,.2]);}
