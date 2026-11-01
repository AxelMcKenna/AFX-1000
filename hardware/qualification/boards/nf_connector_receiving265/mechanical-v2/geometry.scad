NC265_HOLES=[[5.0, 17.5, 0.75], [5.0, 19.5, 0.75], [7.0, 17.5, 0.75], [7.0, 19.5, 0.75], [9.0, 17.5, 0.75], [9.0, 19.5, 0.75], [11.0, 17.5, 0.75], [11.0, 19.5, 0.75], [13.0, 17.5, 0.75], [13.0, 19.5, 0.75], [15.0, 17.5, 0.75], [15.0, 19.5, 0.75], [17.0, 17.5, 0.75], [17.0, 19.5, 0.75], [19.0, 17.5, 0.75], [19.0, 19.5, 0.75], [21.0, 17.5, 0.75], [21.0, 19.5, 0.75], [23.0, 17.5, 0.75], [23.0, 19.5, 0.75], [25.0, 17.5, 0.75], [25.0, 19.5, 0.75], [27.0, 17.5, 0.75], [27.0, 19.5, 0.75], [29.0, 17.5, 0.75], [29.0, 19.5, 0.75], [31.0, 17.5, 0.75], [31.0, 19.5, 0.75], [33.0, 17.5, 0.75], [33.0, 19.5, 0.75], [68.0, 21.0, 2.2], [73.0, 21.0, 2.2], [57.0, 30.0, 0.75], [59.0, 30.0, 0.75], [79.0, 21.0, 2.2], [84.0, 21.0, 2.2], [100.0, 30.0, 0.75], [102.0, 30.0, 0.75], [123.0, 17.5, 1.0], [125.5, 17.5, 1.0]];
NC265_BOXES=[[2.8, 15.75, 0, 32.4, 5.5, 10], [65.6, 18.6, 0, 9.8, 4.8, 3.1], [54.8, 28.05, 0, 6.4, 5.0, 9], [76.6, 18.6, 0, 9.8, 4.8, 3.1], [97.8, 28.05, 0, 6.4, 5.0, 9], [120.3, 13.85, 0, 7.9, 6.25, 10.5]];
// NC265 source-bound LOCAL interface prototype; no full265 board/harness fit.
case_name="none";
module nc265_box(b,g=0){translate([b[0]-g,b[1]-g,b[2]-g])cube([b[3]+2*g,b[4]+2*g,b[5]+2*g]);}
module nc265_world(){multmatrix([[1,0,0,172],[0,0,-1,180.5],[0,1,0,3.5],[0,0,0,1]])children();}
module nc265_post(maximum=false){for(u=[61,90])translate([u,21,0])cylinder(d=maximum?6.1:6,h=5,$fn=128);}
module nc265_channels(){for(u=[68,73,79,84])translate([u,21,4.7])cylinder(d=1.65,h=8.5,$fn=128);}
module nc265_base(assembly=false){difference(){union(){nc265_box([58,17.5,4.8,35,3.5,8.2]);nc265_post();}nc265_channels();
 for(u=[61,90]){translate([u,21,-.01])cylinder(d=1.6,h=4.11,$fn=96);
 if(assembly)translate([u,21,-.01])cylinder(d=2.04,h=3.06,$fn=96);
 translate([u,21.01,9])rotate([90,0,0])cylinder(d=1.6,h=3.01,$fn=96);
 if(assembly)translate([u,21.01,9])rotate([90,0,0])cylinder(d=2.04,h=2.16,$fn=96);}}}
module nc265_cap(){difference(){nc265_box([58,21,5.3,35,3.5,7.7]);nc265_channels();for(u=[61,90])translate([u,24.6,9])rotate([90,0,0])cylinder(d=2.6,h=3.7,$fn=96);}}
module nc265_hardware(){for(u=[61,90]){
 translate([u,21,-1.95]){cylinder(d=2,h=5,$fn=96);translate([0,0,-1.72])cylinder(d=4,h=1.72,$fn=96);}
 translate([u,21,-1.95])difference(){cylinder(d=5,h=.35,$fn=96);translate([0,0,-.01])cylinder(d=2.2,h=.37,$fn=96);}
 translate([u,24.85,9])rotate([90,0,0]){cylinder(d=2,h=6,$fn=96);translate([0,0,-1.72])cylinder(d=4,h=1.72,$fn=96);}
 translate([u,24.85,9])rotate([90,0,0])difference(){cylinder(d=5,h=.35,$fn=96);translate([0,0,-.01])cylinder(d=2.2,h=.37,$fn=96);}}}
module nc265_strain_world(){nc265_world(){nc265_base(true);nc265_cap();nc265_hardware();}}
module nc265_strain_receiving_world(){nc265_world(){nc265_post(true);nc265_box([58,17.5,4.8,35,3.5,8.2]);nc265_box([58,21,5.3,35,3.5,7.7]);
 for(u=[61,90]){translate([u,21,-3.83])cylinder(d=5,h=2.39,$fn=128);translate([u,26.57,9])rotate([90,0,0])cylinder(d=5,h=3.57,$fn=128);}}}
module nc265_pcb(minimum_force_bore=false,thickness=1.76){difference(){nc265_box([0,0,-thickness,149,39,thickness]);
 for(h=NC265_HOLES)translate([h[0],h[1],-1.8])cylinder(d=(minimum_force_bore&&h[2]>2)?2.1:h[2],h=1.9,$fn=128);
 for(u=[61,90])translate([u,21,-1.8])cylinder(d=2.5,h=1.9,$fn=128);}}
module nc265_port_receivers(g=0){for(b=NC265_BOXES)nc265_box(b,g);}
module nc265_interface_receivers_world(){nc265_world()nc265_port_receivers();}
module nc265_force_gauges(){for(u=[68,73,79,84])translate([u,21,-1.8])cylinder(d=2.01,h=1.9,$fn=128);}
module nc265_mount_gauges(){for(u=[61,90])translate([u,21,-1.8])cylinder(d=2.41,h=1.9,$fn=128);}
module nc265_wire_prototype(){for(u=[68,73,79,84])translate([u,21,3.1])cylinder(d=1.7,h=12.9,$fn=128);}
module nc265_grip_contact_mask(){for(u=[68,73,79,84])translate([u,21,4.8])cylinder(d=1.9,h=8.2,$fn=128);}
if(case_name=="base_part")nc265_base();
if(case_name=="cap_part")nc265_cap();
if(case_name=="assembly_review"){nc265_pcb(false,1.6);nc265_port_receivers();nc265_base(true);nc265_cap();nc265_hardware();nc265_wire_prototype();}
if(case_name=="ports_pair_margin")for(i=[0:4])for(j=[i+1:5])intersection(){nc265_box(NC265_BOXES[i],.25);nc265_box(NC265_BOXES[j]);}
if(case_name=="force_solder_post_margin")intersection(){for(i=[1,3])nc265_box(NC265_BOXES[i],.45);nc265_post(true);}
if(case_name=="force_solder_bridge_margin")intersection(){for(i=[1,3])nc265_box(NC265_BOXES[i],.45);union(){nc265_base();nc265_cap();}}
if(case_name=="ports_other_strain_margin")intersection(){for(i=[0,2,4,5])nc265_box(NC265_BOXES[i],.45);union(){nc265_base();nc265_cap();nc265_hardware();}}
if(case_name=="own_PCB_seats")intersection(){nc265_pcb();union(){nc265_base();nc265_cap();nc265_port_receivers();}}
if(case_name=="mount_gauge_min_bores")intersection(){nc265_mount_gauges();nc265_pcb();}
if(case_name=="force_gauge_min_bores")intersection(){nc265_force_gauges();nc265_pcb(true);}
if(case_name=="old_mount_bore_witness")intersection(){translate([90,21,-1.76])cylinder(d=2.41,h=1.76,$fn=128);difference(){nc265_box([87,18,-1.76,6,6,1.76]);translate([90,21,-1.8])cylinder(d=2.3,h=1.9,$fn=128);}}
if(case_name=="old_force_bore_witness")intersection(){translate([68,21,-1.76])cylinder(d=2.01,h=1.76,$fn=128);difference(){nc265_box([65,18,-1.76,6,6,1.76]);translate([68,21,-1.8])cylinder(d=1,h=1.9,$fn=128);}}
if(case_name=="wire_outside_grip_collision")difference(){intersection(){nc265_wire_prototype();union(){nc265_base();nc265_cap();}}nc265_grip_contact_mask();}
if(case_name=="intentional_grip_contact_witness")intersection(){nc265_wire_prototype();union(){nc265_base();nc265_cap();}}
if(case_name=="hardware_receiving_threads")intersection(){nc265_hardware();union(){nc265_base(true);nc265_cap();}}
if(case_name=="hardware_matched_nominal_PCB")intersection(){nc265_hardware();nc265_pcb(false,1.6);}
if(case_name=="uncut_thread_pilots_witness")intersection(){nc265_hardware();nc265_base(false);}
if(case_name=="base_cap_nonseat_overlap")intersection(){nc265_base();nc265_cap();}
if(case_name=="control_contact_point")intersection(){nc265_base();nc265_box([59,18.5,6, .2,.2,.2]);}
