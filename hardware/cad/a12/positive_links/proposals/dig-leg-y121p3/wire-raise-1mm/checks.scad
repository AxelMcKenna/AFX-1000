include </Users/axelmckrnna/dev/rmx-publish/hardware/cad/a12/positive_links/proposals/dig-leg-y121p3/native/checks.scad>

wr_case="none";
module wr_wire(m=0){pf_wire(0,m);}
if(wr_case=="new_wire_covered_positive_collision")intersection(){wr_wire(.25);pb_expand(.1)pb_all();}
if(wr_case=="new_wire_other_electronics_collision")intersection(){wr_wire(.25);ui_wire_obstacles();}
if(wr_case=="new_wire_PS01_body_collision")intersection(){wr_wire(.25);ps_body();}
if(wr_case=="new_wire_controls_case_collision")intersection(){wr_wire(.25);ui_environment();}
if(wr_case=="new_wire_returns_hardware_collision")intersection(){wr_wire(.25);union(){return_assembly();lower_shell_fasteners();ui_h9_head();tc2_posts();tc2_heads();}}
if(wr_case=="new_wire_pair_collision")intersection(){wr_wire(.25);pf_wire(1);}
if(wr_case=="new_wire_J8_attachment_collision")intersection(){wr_wire();pb_J8();}
if(wr_case=="new_wire_geometry")wr_wire();
if(wr_case=="wire_control")intersection(){wr_wire(.25);translate([160.9,120.4,12])cube([.2,.2,.2]);}
