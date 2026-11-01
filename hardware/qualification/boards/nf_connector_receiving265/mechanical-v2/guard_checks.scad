// TEST ONLY: no manufacturing or receiving geometry is changed.
include <geometry.scad>
guard_case="none";
nc265_contact_e=0.00002;
// Circumscribed1024-gon stays within20nm radial extension for R<=3.
function nc265_guard_r(r)=r/cos(180/1024)+0.000005;
module nc265_front_seat_mask(){
 for(b=NC265_BOXES)translate([b[0]-nc265_contact_e,b[1]-nc265_contact_e,-nc265_contact_e])cube([b[3]+2*nc265_contact_e,b[4]+2*nc265_contact_e,2*nc265_contact_e]);
 for(u=[61,90])translate([u,21,-nc265_contact_e])cylinder(r=nc265_guard_r(3),h=2*nc265_contact_e,$fn=1024);
}
module nc265_base_cap_seat_mask(){translate([58-nc265_contact_e,21-nc265_contact_e,5.3-nc265_contact_e])cube([35+2*nc265_contact_e,2*nc265_contact_e,7.7+2*nc265_contact_e]);}
module nc265_back_washer_mask(){for(u=[61,90])translate([u,21,-1.6-nc265_contact_e])cylinder(r=nc265_guard_r(2.5),h=2*nc265_contact_e,$fn=1024);}
module nc265_cap_washer_mask(){for(u=[61,90])translate([u,24.5+nc265_contact_e,9])rotate([90,0,0])cylinder(r=nc265_guard_r(2.5),h=2*nc265_contact_e,$fn=1024);}
module nc265_thread_tip_mask(){for(u=[61,90])translate([u,18.85+nc265_contact_e,9])rotate([90,0,0])cylinder(r=nc265_guard_r(1),h=2*nc265_contact_e,$fn=1024);}

if(guard_case=="front_seats_guarded")difference(){intersection(){nc265_pcb();union(){nc265_base();nc265_cap();nc265_port_receivers();}}nc265_front_seat_mask();}
if(guard_case=="thread_and_cap_washer_guarded")difference(){intersection(){nc265_hardware();union(){nc265_base(true);nc265_cap();}}union(){nc265_thread_tip_mask();nc265_cap_washer_mask();}}
if(guard_case=="back_washer_guarded")difference(){intersection(){nc265_hardware();nc265_pcb(false,1.6);}nc265_back_washer_mask();}
if(guard_case=="base_cap_guarded")difference(){intersection(){nc265_base();nc265_cap();}nc265_base_cap_seat_mask();}

// Each deliberate1000nm intrusion must retain980nm after the20nm mask.
if(guard_case=="front_1000nm_control")difference(){nc265_box([66,20,-.001,.1,.1,.001]);nc265_front_seat_mask();}
if(guard_case=="thread_tip_1000nm_control")difference(){nc265_box([61.85,18.849,8.95,.1,.001,.1]);nc265_thread_tip_mask();}
if(guard_case=="cap_washer_1000nm_control")difference(){nc265_box([62.5,24.499,9,.1,.001,.1]);nc265_cap_washer_mask();}
if(guard_case=="back_washer_1000nm_control")difference(){nc265_box([62.5,21,-1.6,.1,.1,.001]);nc265_back_washer_mask();}
if(guard_case=="base_cap_1000nm_control")difference(){nc265_box([59,20.999,6,.1,.001,.1]);nc265_base_cap_seat_mask();}
