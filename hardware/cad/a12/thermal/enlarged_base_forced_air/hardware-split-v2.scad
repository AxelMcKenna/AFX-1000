include <generated/context-derived.scad>
fi_hw_index=0;fi_hw_family=0;
module fi_hw_evaluate(idx,fam){p=ps_centres[idx];
if(fam==0)intersection(){translate([p[0],p[1],0])ps_hardware_max();ui_electronics(false,false);}
if(fam==1)intersection(){translate([p[0],p[1],0])ps_hardware_max();cp_other_pot_bodies(p);}
if(fam==2)intersection(){translate([p[0],p[1],0])ps_hardware_max();ui_power_only();}
if(fam==3)intersection(){translate([p[0],p[1],0])ps_hardware_max();ps_other_controls();}
if(fam==4)intersection(){translate([p[0],p[1],0])ps_hardware_max();pf_wires(.25);}
if(fam==5)intersection(){translate([p[0],p[1],0])ps_hardware_max();ui_all_joints(.25);}
if(fam==6)intersection(){translate([p[0],p[1],0])ps_hardware_max();translate([p[0]+3.9,p[1]-.1,47])cube([.2,.2,.2]);}
}
fi_hw_evaluate(fi_hw_index,fi_hw_family);
