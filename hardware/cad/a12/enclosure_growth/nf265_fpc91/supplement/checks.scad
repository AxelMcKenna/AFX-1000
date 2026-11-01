// Named supplements; no replacement of the initial failed receiving study.
include <../tail_shape/checks.scad>
su_case="none";
// Exact KEMET max L1.75/W.95/T.95, plus declared .1 seat; native B90 pose.
module su_new_cap_bodies(m=0){for(x=[25.6,27.4])translate([x-.475-m,182.26-m,17.625-m])cube([.95+2*m,1.05+2*m,1.75+2*m]);}
module su_C203_2_tail(m=0){for(b=fr_tails)if(b[0]=="FPC91_C203.2")fr_boxes([b],"all",m);}
module su_actual_minimum_PCB(force_d=2.1){for(b=fr_boards)if(b[0]=="NF265")translate(b[1])rotate([90,0,0])difference(){translate([0,0,-1.76])cube([149,39,1.76]);for(h=b[3])fr_drill([h[0],h[1],(h[5]=="J2"||h[5]=="J4")?force_d:((h[5]=="H101"||h[5]=="H102")?2.5:h[2]),(h[5]=="J2"||h[5]=="J4")?force_d:((h[5]=="H101"||h[5]=="H102")?2.5:h[3]),h[4]]);}}
if(su_case=="actual_C401_C402_primary_body_geometry")intersection(){su_new_cap_bodies();su_new_cap_bodies(.01);}
if(su_case=="actual_C401_C402_tail_margin_collision")intersection(){su_new_cap_bodies();su_C203_2_tail(.45);}
if(su_case=="actual_C401_body_positive_control")intersection(){su_new_cap_bodies();translate([25.5,182.5,18.4])cube([.2,.2,.2]);}
if(su_case=="actual_force_minimum_bores_collision")intersection(){su_actual_minimum_PCB();nc265_world()nc265_force_gauges();}
if(su_case=="actual_mount_minimum_bores_collision")intersection(){su_actual_minimum_PCB();nc265_world()nc265_mount_gauges();}
if(su_case=="actual_old_force_bore_failure_witness")intersection(){su_actual_minimum_PCB(1);nc265_world()nc265_force_gauges();}
