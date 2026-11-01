include <gauge.scad>
module attachment(){lug();washer_head();}
if(part=="south_lug_inflated_electronics"){intersection(){expanded()lug();electronics();}}
if(part=="south_complete_inflated_electronics"){intersection(){expanded()attachment();electronics();}}
if(part=="south_complete_nominal_electronics"){intersection(){attachment();electronics();}}
if(part=="south_lug_inflated_positive"){intersection(){expanded()lug();positive_hardware();}}
if(part=="south_complete_inflated_positive"){intersection(){expanded()attachment();positive_hardware();}}
if(part=="south_complete_nominal_positive"){intersection(){attachment();positive_hardware();}}
if(part=="south_lug_inflated_returns"){intersection(){expanded()lug();other_returns();}}
if(part=="south_complete_inflated_returns"){intersection(){expanded()attachment();other_returns();}}
if(part=="south_complete_nominal_returns"){intersection(){attachment();other_returns();}}
if(part=="south_attachment"){attachment();}
if(part=="south_positive_control"){intersection(){lug();located()translate([7,-.1,.1])cube([.2,.2,.2]);}}
if(part=="known_bad_clock_negative_control"){intersection(){minkowski(){translate([132,129.5,15.1])rotate([0,0,-20]){local_flat();local_barrel();}cube([1.8,1.8,1.8],center=true);}positive_hardware();}}