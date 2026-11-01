include </Users/axelmckrnna/dev/rmx-publish/hardware/cad/a12/positive_links/proposals/dig-leg-y121p3/native/checks.scad>

gs_case="none";
module gs_gauge(m){let($fn=96)minkowski(){union(){lug();washer_head();}cube([2*m,2*m,2*m],center=true);}}
if(gs_case=="complete_attachment_positive_collision")intersection(){gs_gauge(1);pb_all();}
if(gs_case=="complete_attachment_original_positive_witness")intersection(){gs_gauge(.9);let($fn=96)positive_hardware();}
if(gs_case=="attachment_control")intersection(){gs_gauge(1);translate([131.9,136.4,15.5])cube([.2,.2,.2]);}
