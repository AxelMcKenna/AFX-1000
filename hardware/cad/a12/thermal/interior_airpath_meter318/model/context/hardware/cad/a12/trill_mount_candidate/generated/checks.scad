use </Users/axelmckrnna/dev/rmx-publish/hardware/cad/a12/thermal/interior_airpath_meter318/model/context/hardware/cad/a12/trill_mount_candidate/sources/hardware/cad/a11/controls.scad>
$fn=64;panel_z=43.6;candidate_case="saddle";
mounts=[[130.0871, 134.422], [93.0871, 134.4352]];
bodies=[[80.83602209408176, 126.78102209408175, 32.2, 4.69015581183649, 15.358155811836497, 6.4], [105.54318953743822, 130.40618953743822, 32.2, 8.107820925123548, 8.107820925123548, 6.4], [113.9062680285159, 137.9290680285159, 32.2, 1.7954639429682118, 0.8354639429682038, 6.4], [87.94802209408176, 142.02102209408176, 32.2, 38.21815581183648, 4.69015581183649, 6.4], [87.94802209408176, 122.20902209408176, 32.2, 38.21815581183648, 4.690155811836476, 6.4], [115.4658680285159, 134.0068680285159, 32.2, 0.8354639429682038, 1.7954639429682118, 6.4], [99.04231157169083, 131.05691157169082, 32.2, 1.8573768566183304, 0.8373768566183344, 6.4], [99.04231157169083, 136.96291157169082, 32.2, 1.8573768566183304, 0.8373768566183344, 6.4], [91.99331157169084, 128.98681157169082, 32.2, 1.8573768566183304, 0.8373768566183344, 6.4], [125.85267965644036, 125.06167965644036, 32.2, 4.242640687119291, 4.242640687119291, 6.4], [125.85267965644036, 139.53967965644037, 32.2, 4.242640687119291, 4.242640687119263, 6.4], [98.31421318113401, 132.470857181134, 32.2, 4.402775637731992, 3.8027756377319974, 6.4], [92.06951157169084, 139.10871157169083, 32.2, 1.8573768566183304, 0.8373768566183344, 6.4]];
tails=[[84.1971, 128.1101], [84.1971, 130.6501], [84.1971, 133.1901], [84.1971, 135.7301], [84.1971, 138.2701], [84.1971, 140.8101], [89.2771, 143.3501], [91.8171, 143.3501], [94.3571, 143.3501], [96.8971, 143.3501], [99.4371, 143.3501], [101.9771, 143.3501], [104.5171, 143.3501], [107.0571, 143.3501], [109.5971, 143.3501], [112.1371, 143.3501], [114.6771, 143.3501], [117.2171, 143.3501], [119.7571, 143.3501], [122.2971, 143.3501], [124.8371, 143.3501], [124.8371, 125.5701], [122.2971, 125.5701], [119.7571, 125.5701], [117.2171, 125.5701], [114.6771, 125.5701], [112.1371, 125.5701], [109.5971, 125.5701], [107.0571, 125.5701], [104.5171, 125.5701], [101.9771, 125.5701], [99.4371, 125.5701], [96.8971, 125.5701], [94.3571, 125.5701], [91.8171, 125.5701], [89.2771, 125.5701]];

module corners(){for(x=[73,143],y=[123,145])translate([x,y,0])children();}
module saddle(){difference(){union(){
 // Outer lower rails and crossbeam stay beneath the declared3mm solder tails.
 for(y=[123,145])translate([70.1,y-2.9,24.6])cube([75.8,5.8,1.6]);
 for(x=[73,143])translate([x-2.9,120.1,24.6])cube([5.8,27.8,1.6]);
 translate([73,131.4,24.6])cube([70,6,1.6]);
 for(m=mounts)translate([m[0],m[1],26.2])cylinder(d=5.4,h=4.4);
 corners()translate([0,0,26.2])cylinder(d=5.8,h=16);
 }for(m=mounts)translate([m[0],m[1],24.5])cylinder(d=3.4,h=6.2);
 // UnselectedM2-class corner interface: no thread or material strength credit.
 corners()translate([0,0,26.3])cylinder(d=2.2,h=16);
}}
module board(){difference(){translate([82,123.5,30.6])cube([53.848,21.844,1.6]);
 for(m=mounts)translate([m[0],m[1],30.5])cylinder(d=3.2,h=1.8);
}}
module components(){for(b=bodies)translate([b[0],b[1],b[2]])cube([b[3],b[4],b[5]]);}
module tails(){for(p=tails)translate([p[0],p[1],27.6])cylinder(r=.8,h=3);}
module hardware(){for(m=mounts){
 translate([m[0],m[1],32.2])cylinder(d=6.4,h=3.2);
 translate([m[0],m[1],24.6])cylinder(d=3,h=7.6);
}}
module aperture(){translate([75.5,126.5,42.1])cube([65,15,4]);}
if(candidate_case=="saddle")saddle();
if(candidate_case=="board")board();
if(candidate_case=="hardware_requirements")hardware();
if(candidate_case=="saddle_board")intersection(){translate([0,0,-.00002])saddle();board();}
if(candidate_case=="saddle_components")intersection(){saddle();components();}
if(candidate_case=="saddle_tails")intersection(){saddle();tails();}
if(candidate_case=="saddle_backer")intersection(){translate([0,0,-.00002])saddle();touch_backer();}
if(candidate_case=="heads_components")intersection(){hardware();components();}
if(candidate_case=="heads_backer")intersection(){hardware();touch_backer();}
if(candidate_case=="central_aperture")intersection(){saddle();aperture();}
if(candidate_case=="known_board_collision")intersection(){board();translate([100,130,31])cube([.2,.2,.2]);}
if(candidate_case=="known_head_collision")intersection(){hardware();translate([130,134.4,34])cube([.2,.2,.2]);}
if(candidate_case=="backer_contact")intersection(){translate([0,0,.01])saddle();touch_backer();}
