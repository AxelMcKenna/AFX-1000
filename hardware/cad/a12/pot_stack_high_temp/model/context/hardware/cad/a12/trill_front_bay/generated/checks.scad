include </Users/axelmckrnna/dev/rmx-publish/hardware/cad/a12/pot_stack_high_temp/model/context/hardware/cad/a12/trill_front_bay/generated/context-derived.scad>
tc2_centres=[[130.0871, 168.922], [93.0871, 168.9352]];
tc2_shift=[0, 34.5, -10.6];
tc2_growth=[[0.0, 0.0], [156.0, 0.0], [156.0, 37.012881], [155.816918, 37.179158], [155.643037, 37.355036], [155.478861, 37.540004], [155.324862, 37.733529], [155.181488, 37.93505], [155.049152, 38.143987], [154.928236, 38.359734], [154.819091, 38.581667], [154.722032, 38.809146], [154.637338, 39.041513], [154.565256, 39.278096], [154.505994, 39.518211], [154.459722, 39.761164], [154.426575, 40.006253], [154.406649, 40.252769], [154.4, 40.5], [154.406649, 40.747231], [154.426575, 40.993747], [154.459722, 41.238836], [154.505994, 41.481789], [154.565256, 41.721904], [154.637338, 41.958487], [154.722032, 42.190854], [154.819091, 42.418333], [154.928236, 42.640266], [155.049152, 42.856013], [155.181488, 43.06495], [155.324862, 43.266471], [155.478861, 43.459996], [155.643037, 43.644964], [155.816918, 43.820842], [156.0, 43.987119], [156.0, 54.5], [5.0, 54.5], [5.0, 35.0], [0.0, 35.0]];
tc2_before=[[0.0, 0.0], [156.0, 0.0], [156.0, 37.012881], [155.816918, 37.179158], [155.643037, 37.355036], [155.478861, 37.540004], [155.324862, 37.733529], [155.181488, 37.93505], [155.049152, 38.143987], [154.928236, 38.359734], [154.819091, 38.581667], [154.722032, 38.809146], [154.637338, 39.041513], [154.565256, 39.278096], [154.505994, 39.518211], [154.459722, 39.761164], [154.426575, 40.006253], [154.406649, 40.252769], [154.4, 40.5], [154.406649, 40.747231], [154.426575, 40.993747], [154.459722, 41.238836], [154.505994, 41.481789], [154.565256, 41.721904], [154.637338, 41.958487], [154.722032, 42.190854], [154.819091, 42.418333], [154.928236, 42.640266], [155.049152, 42.856013], [155.181488, 43.06495], [155.324862, 43.266471], [155.478861, 43.459996], [155.643037, 43.644964], [155.816918, 43.820842], [156.0, 43.987119], [156.0, 45.25], [5.0, 45.25], [5.0, 35.0], [0.0, 35.0]];

tc2_case="geometry";
module tc2_posts(m=0){for(p=tc2_centres)difference(){translate([p[0],p[1],2.7])cylinder(d=(7.2+2*m)/cos(180/128),h=17.3,$fn=128);translate([p[0],p[1],15.3])cylinder(d=2.05,h=4.71,$fn=128);}}
module tc2_board(){translate(tc2_shift)tc_board();}
// Explicit source-derived centres keep the minimum-bore acceptance screen independent.
module tc2_min_board(){difference(){translate([82,158,20])cube([53.848,21.844,1.6]);for(p=tc2_centres)translate([p[0],p[1],19.99])cylinder(d=3.1,h=1.62,$fn=128);}}
module tc2_components(){translate(tc2_shift){tc_components();tc_tails();}}
module tc2_heads(){for(p=tc2_centres){translate([p[0],p[1],21.6])cylinder(d=6.4,h=2.2,$fn=128);translate([p[0],p[1],15.6])cylinder(d=2.5,h=6,$fn=128);}}
module tc2_tool(){for(p=tc2_centres)translate([p[0],p[1],21.6])cylinder(d=6.5,h=38.5,$fn=128);}
module tc2_relative(m){for(p=tc2_centres)translate([p[0],p[1],19.9])cylinder(r=(1.25+m+.005)/cos(180/128),h=1.8,$fn=128);}
module tc2_hardware(){tc2_posts();tc2_heads();}
module tc2_new_material(){tc2_posts();tc2_heads();tc2_board();tc2_components();}
module tc2_existing(){for(b=ui_native_boards)ui_native_PCB(b);ui_receiver();for(b=ui_other_boards)board_reserve(b);ui_components(false);ui_receiver_joint();ui_source_joint();ui_h9_head();}
module tc2_growth_slab(){translate([8,108.5,4.8])linear_extrude(2.1)difference(){polygon(tc2_growth);polygon(tc2_before);}}
module tc2_growth_external(m){tc2_posts(m);}
module tc2_above_floor(){intersection(){tc2_new_material();translate([0,0,2.80002])cube([334,188.4,100]);}}
module tc2_case_open(){ui_shell();rear_panel();thermal_metal_base();}
if(tc2_case=="geometry")tc2_new_material();
if(tc2_case=="posts_geometry")tc2_posts();
if(tc2_case=="growth_slab_geometry")tc2_growth_slab();
if(tc2_case=="existing_collision")intersection(){tc2_new_material();tc2_existing();}
if(tc2_case=="case_collision")intersection(){tc2_above_floor();tc2_case_open();}
if(tc2_case=="controls_collision")intersection(){tc2_new_material();ui_controls_and_lid();}
if(tc2_case=="power_collision")intersection(){tc2_new_material();ui_power_only();}
if(tc2_case=="wire_collision")intersection(){tc2_new_material();pf_wires(.25);}
if(tc2_case=="posts_component_tail_collision")intersection(){tc2_posts();tc2_components();}
if(tc2_case=="heads_components_collision")intersection(){tc2_heads();tc2_components();}
if(tc2_case=="posts_board_collision")intersection(){translate([0,0,-.00002])tc2_posts();tc2_board();}
if(tc2_case=="shank_board_collision")intersection(){translate([0,0,.00002])tc2_heads();tc2_board();}
if(tc2_case=="bore_relative_0p2_collision")intersection(){tc2_relative(.2);tc2_min_board();}
if(tc2_case=="bore_relative_0p3_rejected_sensitivity")intersection(){tc2_relative(.3);tc2_min_board();}
if(tc2_case=="growth_nominal_collision")intersection(){tc2_new_material();tc2_growth_slab();}
if(tc2_case=="growth_0p45_collision")intersection(){tc2_growth_external(.45);tc2_growth_slab();}
if(tc2_case=="growth_0p90_collision")intersection(){tc2_growth_external(.90);tc2_growth_slab();}
if(tc2_case=="openlid_tool_electronics_collision")intersection(){tc2_tool();union(){tc2_existing();tc2_components();}}
if(tc2_case=="openlid_tool_power_case_collision")intersection(){tc2_tool();union(){tc2_case_open();ui_power_only();}}
if(tc2_case=="guide_left_in_place_blocked_witness")intersection(){tc2_tool();translate([0,0,panel_z-guide_thick])guide_plate();}
if(tc2_case=="floor_bond")intersection(){tc2_posts();ui_shell();}
if(tc2_case=="post_positive_control")intersection(){tc2_posts();translate([132.9,168.8,10])cube([.2,.2,.2]);}
if(tc2_case=="body_positive_control")intersection(){tc2_board();translate([100,160,20.5])cube([.2,.2,.2]);}
if(tc2_case=="growth_positive_control")intersection(){tc2_growth_slab();translate([100,160,5.5])cube([.2,.2,.2]);}
if(tc2_case=="tool_positive_control")intersection(){tc2_tool();translate([129.9,168.8,30])cube([.2,.2,.2]);}
