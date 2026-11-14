// Independent assembly-motion check using the exact final housing source.
include <housing.scad>
module seated_nut(p,offset=[0,0]) {
 translate([p[0]+offset[0],p[1]+offset[1],40.7])
 rotate([0,0,nut_angle(p)])nut(4,1.6);
}
if(part=="lid_nut_insertion_collision")intersection(){
 shell();
 for(p=lid_fasteners)hull(){
  seated_nut(p);
  seated_nut(p,nut_entry(p));
 }
}
