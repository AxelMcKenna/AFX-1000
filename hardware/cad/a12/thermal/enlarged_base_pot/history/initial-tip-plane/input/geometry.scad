// CP01 additional own-contact contracts. All dimensions are source requirements.
module cp_other_pot_bodies(p){for(q=ps_centres)if(q!=p)translate([q[0]-8,q[1]-8,27.5])cube([16,16,43.59998-27.5]);}
module cp_pot_hardware(){for(p=ps_centres)translate([p[0],p[1],0]){ps_hardware_max();ps_shaft_max();}}
if(cp_case=="pot_hardware_review")cp_pot_hardware();
if(cp_case=="body_base_all_collision")intersection(){ps_body(.25);union(){eb_metal();eb_interfaces();eb_lower();eb_foot_screws();}}
if(cp_case=="receivers_base_all_collision")intersection(){cp_pot_hardware();union(){eb_metal();eb_interfaces();eb_lower();eb_foot_screws();}}
if(cp_case=="body_interface_positive_control")intersection(){ps_body();translate([193.9,132.9,30])cube([.2,.2,.2]);}
