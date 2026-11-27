include <../../../two_board_print_01/captured.scad>
// Nominal receiving models; thread crests and underhead fillet are not supplier CAD.
module main_fastener_unit_r1(post,length){
 seat=post+1.6+0.3;
 union(){
  translate([0,0,seat-length])cylinder(d=2,h=length,$fn=64);
  translate([0,0,seat])cylinder(d=3.8,h=2,$fn=64);
  translate([0,0,post+1.6])difference(){cylinder(d=4.5,h=.3,$fn=64);translate([0,0,-.01])cylinder(d=2.2,h=.32,$fn=64);}
  translate([0,0,.2])difference(){cylinder(d=4/cos(30),h=1.6,$fn=6);translate([0,0,-.01])cylinder(d=2,h=1.62,$fn=64);}
 }
}
module main_fasteners_nominal_r1(){for(m=mounts)if(m[0]!="D_H2"&&m[0]!="D_H5")translate([m[1],m[2],0])main_fastener_unit_r1(m[3],m[3]<7?10:12);}
module main_fastener_receiving_r1(){
 for(m=mounts)if(m[0]!="D_H2"&&m[0]!="D_H5")let(signal=m[3]<7,tip=signal?-1.89:-2.8,boardlo=signal?8.15:9.3,headhi=signal?10.9:12.05)translate([m[1],m[2],0])union(){
  translate([0,0,tip])cylinder(d=2.2/cos(180/64),h=headhi-tip,$fn=64);
  translate([0,0,.1])cylinder(d=(4/cos(30)+.1)/cos(180/64),h=1.8,$fn=64);
  translate([0,0,boardlo])cylinder(d=4.8/cos(180/64),h=headhi-boardlo,$fn=64);
 }
}
