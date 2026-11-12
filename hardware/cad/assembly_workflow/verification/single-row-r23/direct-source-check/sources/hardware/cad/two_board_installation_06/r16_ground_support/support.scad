// Lid-carried splice cage candidate. Uses existing settings PCB mounting holes.
use <../../two_board_controls_04/selectors.scad>
$fn=64;
module gs_nut(af=4,h=1.6){cylinder(d=af/cos(30),h=h,$fn=6);}
module gs_mount_foot(y){difference(){translate([307,y,36.5])cylinder(d=6,h=1.6);translate([307,y,36.4])cylinder(d=2.4,h=1.8);if(y<30)translate([302,20.2,36])cube([10,5,3]);else translate([302,28.8,36])cube([10,5,3]);}}
module gs_bar(a,b,size=[3,3,1.3]){hull(){translate(a)cube(size,center=true);translate(b)cube(size,center=true);}}
module gs_cap_footprints(z,h){
 for(p=[[289.5,26.5],[289.5,37.5]])hull(){translate([p[0],p[1],z])cylinder(r=3.3,h=h);translate([p[0]<293?291:295,p[1]<32?28.5:35.5,z])cylinder(r=2.5,h=h);}
}
module gs_cavity(){translate([280.4,32,29.5])rotate([0,90,0])cylinder(d=6.5,h=25.2);}
module ground_splice_saddle(){difference(){union(){
 for(y=[17.5,36.5]){gs_mount_foot(y);gs_bar([304.8,y,37.15],[296,y,37.15]);}
 translate([294.5,16,36.5])cube([3,22,1.6]);
 gs_bar([296,36.5,37.3],[296,40,34.5],[3,3,3]);
 translate([294.5,38.5,24.5])cube([3,3,10]);
 gs_bar([296,40,25.2],[293,32,25.2],[3,3,1.4]);
 // Continuous lower cage, with narrow wire apertures at both axial stops.
 translate([279.5,27.6,24.5])cube([27,8.8,1.7]);
 for(y=[27.6,35.35])translate([280.5,y,26.2])cube([25,1.05,3.3]);
 translate([279.4,28.2,25.4])cube([1,7.6,7.6]);
 translate([305.6,28.2,25.4])cube([1,7.6,7.6]);
 translate([290,27,24.5])cube([6,10,5]);
 gs_cap_footprints(24.5,5);
 }
 for(y=[17.5,36.5])translate([307,y,36.4])cylinder(d=2.4,h=1.8);
 // Cavity cuts only the inner body space, preserving axial end-stop plates.
 gs_cavity();
 translate([279.3,32,29.5])rotate([0,90,0])cylinder(d=1.4,h=1.4);
 for(y=[31,33])translate([305.4,y,29.5])rotate([0,90,0])cylinder(d=1.4,h=1.4);
 for(p=[[289.5,26.5],[289.5,37.5]]){translate([p[0],p[1],24.4])cylinder(d=2.4,h=6);translate([p[0],p[1],24.4])gs_nut(4.2,4);}
}}
module ground_splice_cap(){difference(){union(){
 intersection(){translate([290,32,29.5])rotate([0,90,0])cylinder(d=8.9,h=6);translate([289,26,29.5])cube([8,12,6]);}
 gs_cap_footprints(29.5,4);
 }gs_cavity();for(p=[[289.5,26.5],[289.5,37.5]])translate([p[0],p[1],29.4])cylinder(d=2.4,h=5);}}
module ground_splice_cap_hardware(){for(p=[[289.5,26.5],[289.5,37.5]])translate([p[0],p[1],0]){
 translate([0,0,26])cylinder(d=2,h=8);translate([0,0,34])cylinder(d=4.5,h=2.2);
 translate([0,0,33.5])difference(){cylinder(d=4.5,h=.5);translate([0,0,-.1])cylinder(d=2.4,h=.7);}
 translate([0,0,26.8])difference(){gs_nut();translate([0,0,-.1])cylinder(d=1.6,h=1.8);}
}}
module gs_settings_m2x12(){for(y=[17.5,36.5])translate([307,y,0]){
 translate([0,0,33.6])cylinder(d=2,h=12);translate([0,0,45.6])cylinder(d=4.5,h=2.2);
 translate([0,0,36])difference(){cylinder(d=4.5,h=.5);translate([0,0,-.1])cylinder(d=2.4,h=.7);}
 translate([0,0,34.4])difference(){gs_nut();translate([0,0,-.1])cylinder(d=1.6,h=1.8);}
}}
module gs_release_original_hardware(){difference(){tbh04_selector_fasteners();for(y=[17.5,36.5])translate([304, y-3,33.5])cube([6,6,15]);}}
module ground_supported_selectors(){tbh04_selector_brackets();tbh04_selector_pcbs();tbh04_selector_bodies();tbh04_selector_leads();gs_release_original_hardware();gs_settings_m2x12();}
module ground_splice_support_prints(){ground_splice_saddle();ground_splice_cap();}
module ground_splice_support(){ground_splice_support_prints();ground_splice_cap_hardware();}
module gs_pcb_seat_masks(){for(y=[17.5,36.5])translate([307,y,38.09])cylinder(r=3.1,h=.02);}
module gs_hardware_seat_masks(){for(y=[17.5,36.5])translate([307,y,36.49])cylinder(r=2.35,h=.02);for(p=[[289.5,26.5],[289.5,37.5]])for(z=[28.4,33.5])translate([p[0],p[1],z-.01])cylinder(r=2.5,h=.02);}
module gs_half_seat_masks(){translate([285,22,29.49])cube([16,20,.02]);}
