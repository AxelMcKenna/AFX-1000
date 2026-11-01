// NEW test-only nominal-contact masks; actual AP02parts are unchanged.
mg=.00002;
module mg_Z(z){translate([-1,-1,z-mg])cube([336,191,2*mg]);}
module mg_Y(y){translate([-1,y-mg,-40])cube([336,2*mg,120]);}
module mg_upper(z){intersection(){union(){translate([0,0,-mg])ap_upper_gaskets();translate([0,0,mg])ap_upper_gaskets();}mg_Z(z);}}
module mg_frame(z){intersection(){union(){translate([0,0,-mg])ap_frame_gaskets();translate([0,0,mg])ap_frame_gaskets();}mg_Z(z);}}
module mg_M3(){for(p=ap_fans)for(x=[-16,16],y=[-16,16])for(z=[-28.2,-27.7,-26.7,-26.2,-12.2])translate([p[0]+x,p[1]+y,z-mg])cylinder(r=3.71,h=2*mg,$fn=128);}
module mg_M2(){for(p=ap_fans)for(x=[-7,7],y=[139,144])translate([p[0]+x,y-mg,-8.9])rotate([-90,0,0])cylinder(r=2.73,h=2*mg,$fn=128);}
module mg_boss_cylinders(){for(p=ap_fans)for(x=[-16,16],y=[-16,16])translate([p[0]+x,p[1]+y,-25.2-mg])difference(){cylinder(r=3.1+mg,h=.5+2*mg,$fn=96);translate([0,0,-mg])cylinder(r=3.1-mg,h=.5+4*mg,$fn=96);}}
module mg_meter(){intersection(){union(){translate([0,-mg,0])ap_meter_gaskets();translate([0,mg,0])ap_meter_gaskets();}union(){mg_Y(141.5);mg_Y(142);}}}
module mg_feedthrough(){
 intersection(){union(){translate([0,-mg,0])ap_feedthroughs();translate([0,mg,0])ap_feedthroughs();}union(){mg_Y(142);mg_Y(144);}}
 for(x=[46,235.5])translate([x,142-mg,-10])rotate([-90,0,0])difference(){cylinder(r=2.2+mg,h=2+2*mg,$fn=96);translate([0,0,-mg])cylinder(r=2.2-mg,h=2+4*mg,$fn=96);}
}
module mate_guard_for(name){
 if(name=="M3_hardware_nominal_mates")mg_M3();
 if(name=="M2_hardware_nominal_mates")mg_M2();
 if(name=="upper_gasket_base")mg_upper(-6.2);
 if(name=="upper_gasket_tray")mg_upper(-6.7);
 if(name=="frame_gasket_tray"){mg_frame(-25.2);mg_boss_cylinders();}
 if(name=="frame_gasket_fan")mg_frame(-24.7);
 if(name=="meter_gasket_wall_plate")mg_meter();
 if(name=="feedthrough_wall")mg_feedthrough();
}
