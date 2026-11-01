include </Users/axelmckrnna/dev/rmx-publish/hardware/cad/a12/enclosure_growth/integration_repaired/generated/checks.scad>
diag_rows=[["e19_J29", 96.65, 76.23, 8.1, 9.62, 4.54, 11.31], ["e19_J29_lead_1", 103.0, 77.50000000000001, 3.35, 2, 2, 3.15], ["e19_J29_lead_2", 100.46000000000001, 77.50000000000001, 3.35, 2, 2, 3.15], ["e19_J29_lead_3", 97.91999999999999, 77.50000000000001, 3.35, 2, 2, 3.15]];

diag_case="pedestal";
module diag_J29(){ui_boxes([for(b=ui_inherited_envelopes)if(b[0]=="e19_J29")b]);}
module diag_pedestal(){import("/Users/axelmckrnna/dev/rmx-publish/hardware/cad/a12/positive_links/generated/BONDED-PEDESTAL.stl");}
module diag_proposal(){ui_boxes(diag_rows,.25);}
module diag_existing(){for(b=ui_native_boards)ui_native_PCB(b);for(b=ui_other_boards)board_reserve(b);ui_components();ui_receiver_joint();ui_source_joint();tc2_board();tc2_posts();tc2_heads();}
if(diag_case=="pedestal")intersection(){diag_pedestal();diag_J29();}
if(diag_case=="copper_collision")intersection(){import("/Users/axelmckrnna/dev/rmx-publish/hardware/cad/a12/positive_links/generated/DIG-CU.stl");diag_J29();}
if(diag_case=="returns_collision")intersection(){return_assembly();diag_J29();}
if(diag_case=="without_pedestal_collision")intersection(){difference(){ui_power_only();diag_pedestal();}diag_J29();}
if(diag_case=="proposed_geometry")diag_proposal();
if(diag_case=="proposed_electronics_collision")intersection(){diag_proposal();diag_existing();}
if(diag_case=="proposed_power_collision")intersection(){diag_proposal();ui_power_only();}
if(diag_case=="proposed_controls_case_collision")intersection(){diag_proposal();ui_environment();}
if(diag_case=="proposed_positive_control")intersection(){diag_proposal();translate([100,78,10])cube([.2,.2,.2]);}
