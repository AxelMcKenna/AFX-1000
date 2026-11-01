include <generated/context-derived.scad>
p=ps_centres[fi_hw_index];
if(fi_hw_family==0)intersection(){translate([p[0],p[1],0])ps_hardware_max();ui_electronics(false,false);}
if(fi_hw_family==1)intersection(){translate([p[0],p[1],0])ps_hardware_max();cp_other_pot_bodies(p);}
if(fi_hw_family==2)intersection(){translate([p[0],p[1],0])ps_hardware_max();ui_power_only();}
if(fi_hw_family==3)intersection(){translate([p[0],p[1],0])ps_hardware_max();ps_other_controls();}
if(fi_hw_family==4)intersection(){translate([p[0],p[1],0])ps_hardware_max();pf_wires(.25);}
if(fi_hw_family==5)intersection(){translate([p[0],p[1],0])ps_hardware_max();ui_all_joints(.25);}
if(fi_hw_family==6)intersection(){translate([p[0],p[1],0])ps_hardware_max();translate([p[0]+3.9,p[1]-.1,47])cube([.2,.2,.2]);}
