// FI01 receiving prototype, unqualified mechanical/axial/material assumptions.
fi_fa_case="fi_only";
fi_case="fi_only";
module fi_fa_dispatch(name){
 fa_selector=name;
 include <fa-scoped.scad>
}
module fi_tray(){fi_fa_dispatch("tray_geometry");}
module fi_guards(){fi_fa_dispatch("guard_geometry");}
module fi_spacers(){fi_fa_dispatch("spacer_geometry");}
module fi_fans(){fi_fa_dispatch("fan_gauge_geometry");}
module fi_fan_fasteners(){fi_fa_dispatch("fastener_gauge_geometry");}
module fi_fan_stress(){fi_fa_dispatch("fan_stress_receiving");}
module fi_hardware_stress(){fi_fa_dispatch("hardware_stress_receiving");}
module fi_added(){fi_tray();fi_guards();fi_spacers();fi_fans();fi_fan_fasteners();}
if(fi_fa_case!="fi_only")fi_fa_dispatch(fi_fa_case);
// Contact planes are explicit; no otherbody/PCB clearances are omitted.
if(fi_case=="actual_base_tray_collision")intersection(){eb_base();translate([0,0,-.00002])fi_tray();}
if(fi_case=="actual_base_fan_stress_collision")intersection(){eb_base();fi_fan_stress();}
if(fi_case=="actual_base_hardware_sweep_collision")intersection(){eb_base();fi_hardware_stress();}
if(fi_case=="foot_screws_tray_collision")intersection(){eb_foot_screws();fi_tray();}
if(fi_case=="foot_screws_spacers_collision")intersection(){eb_foot_screws();fi_spacers();}
if(fi_case=="feet_spacers_contact_collision")intersection(){translate([0,0,-.00002])eb_feet_assembly();fi_spacers();}
if(fi_case=="actual_feet_tray_collision")intersection(){eb_feet_assembly();fi_tray();}
if(fi_case=="added_case_controls_collision")intersection(){fi_added();union(){eb_case_and_lid();ui_controls();eb_interfaces();}}
if(fi_case=="added_electronics_collision")intersection(){fi_added();ui_electronics();}
if(fi_case=="added_existing_power_collision")intersection(){fi_added();union(){eb_lower();eb_other_hardware();cp_pot_hardware();}}
if(fi_case=="added_existing_wires_collision")intersection(){fi_added();union(){pf_wires(.25);ui_all_joints(.25);}}
// Test-only nominal correlated bearing contacts: exact four planes, local to
// eight fan-bolt axes. Actual parts and all swept/floating contracts unchanged.
module fi_nominal_seat_guard(){for(p=[[80,165.5],[254,165.5]])for(x=[-16,16],y=[-16,16])for(z=[-27.7,-26.7,-26.2,-12.2])translate([p[0]+x,p[1]+y,z-.00002])cylinder(r=3.71,h=.00004,$fn=128);}
if(fi_case=="nominal_fan_hardware_mates_collision")difference(){intersection(){fi_fan_fasteners();union(){fi_tray();fi_guards();fi_fans();}}fi_nominal_seat_guard();}
// Fixed witnesses chosen from the actual sourcegrid, not ideal area estimates.
if(fi_case=="removed_pin_void_collision")intersection(){eb_base();translate(FI_REMOVED_WITNESS)cube([.2,.2,.2]);}
if(fi_case=="retained_pin_positive_control")intersection(){eb_base();translate(FI_RETAINED_WITNESS)cube([.2,.2,.2]);}
if(fi_case=="long_foot_screw_positive_control")intersection(){eb_foot_screws();translate([19.9,19.9,-18])cube([.2,.2,.2]);}
if(fi_case=="below_thread_tip_positive_control")intersection(){eb_feet_assembly();translate([21.3,19.95,-22])cube([.1,.1,.2]);}
if(fi_case=="engaged_thread_void_collision")intersection(){eb_feet_assembly();translate([21.3,19.95,-18])cube([.1,.1,.2]);}
