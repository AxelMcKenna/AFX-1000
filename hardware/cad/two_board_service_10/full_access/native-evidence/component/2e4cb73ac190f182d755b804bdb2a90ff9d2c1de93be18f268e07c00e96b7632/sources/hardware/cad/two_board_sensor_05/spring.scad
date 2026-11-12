// TBH05 spring assembly: raised fixed eye and lowered moving eye.
include <carrier.scad>
// All shaft axes X. Brass bolts/sleeves reduce nearby ferromagnetic material.
// Full spring loops slide onto a removable smooth sleeve, not through eye holes.
// Smooth headed clevis pin; washer and split pin give positive capture.
// Body: Ø2, 17mm under-head length. Cross hole Ø0.6 at15.6mm from head.
module spring_pin(y,z){
 translate([311.4,y,z])rotate([0,90,0])cylinder(d=3.8,h=1.6);
 difference(){translate([313,y,z])rotate([0,90,0])cylinder(d=2,h=17);translate([328.6,y-2,z])rotate([-90,0,0])cylinder(d=.6,h=4);}
 translate([319,y,z])rotate([0,90,0])difference(){cylinder(d=4,h=8.15);translate([0,0,-.01])cylinder(d=2.2,h=8.17);}
 translate([327.85,y,z])rotate([0,90,0])difference(){cylinder(d=4,h=.4);translate([0,0,-.01])cylinder(d=2.1,h=.42);}
 // Receiving envelope for installed bent Ø0.5 split pin; orient legs along Y.
 translate([328.2,y-3,z-1.2])cube([1.8,6,2.4]);
}
module lever_arm_spring(angle=0) {
    // Pull toward front (+Y); 0..35 degrees. Sensor magnet is on the left end.
    translate([316,82,24]) rotate([-angle,0,0]) {
        difference() {
            union() {
                rotate([0,90,0]) cylinder(h=14,d=10,center=true,$fn=48);
                translate([-11,0,0]) rotate([0,90,0]) cylinder(h=4,d=8,$fn=48);
                translate([-2,-2,0]) cube([4,4,24]);
                translate([-8,-4,22]) cube([16,8,4]);
                translate([-2,-1.5,-10]) cube([4,3,7]);
                translate([-3,-2,5.5]) cube([6,4,4]);
            }
            translate([-1,0,0]) rotate([0,90,0]) cylinder(h=10,d=3.2,$fn=48);
            // Tap M3 after printing for a radial grub screw clamping the pivot.
            translate([4,6,0]) rotate([90,0,0]) cylinder(h=7,d=2.5,$fn=32);
            // Captive diametric magnet socket. Retention/adhesive tested on coupon.
            translate([-11.1,0,0]) rotate([0,90,0]) cylinder(h=2.2,d=6.2,$fn=48);
            translate([-4,0,7.5]) rotate([0,90,0]) cylinder(h=8,d=2.2,$fn=32);
        }
    }
}


module spring_bracket_world(){difference(){union(){bracket_world();translate([313,68,33.6])cube([6,4,7]);}translate([312,70,38.6])rotate([0,90,0])cylinder(d=2.2,h=8);}}
module fixed_pin(){spring_pin(70,38.6);}
module moving_pin(a=0){translate([0,82,31.6])rotate([-a,0,0])translate([0,-82,-31.6])spring_pin(82,39.1);}
// Full connected spring occupied volume, including loop and coil maxima.
// Spring center X327.5 with ±0.6 assembly/loop play and 0.10 radial allowance.
module attached_spring_corridor(){for(a=[0:1:34])hull(){
 for(dx=[-.6,.6])translate([327.5+dx,70,38.6])sphere(d=3.38,$fn=32);
 for(t=[a,a+1],dx=[-.6,.6])translate([327.5+dx,82+7.5*sin(t),31.6+7.5*cos(t)])sphere(d=3.38,$fn=32);
}}
module pin_sweep(){for(a=[0:1:34])hull()for(dx=[-.5,.5],t=[a,a+1])translate([dx,0,0])moving_pin(t);}
module spring_installed_envelope(){fixed_pin();pin_sweep();attached_spring_corridor();}
if(part=="spring_hardware_controls_clearance")intersection(){spring_installed_envelope();union(){translate([0,0,H])lid();guide_installed();holders_installed();}}
if(part=="spring_hardware_shell_clearance")intersection(){spring_installed_envelope();shell();}
if(part=="spring_hardware_components_clearance")intersection(){spring_installed_envelope();box_rows(component_boxes);}
if(part=="spring_hardware_carrier_clearance")intersection(){spring_installed_envelope();tbh05_installed();}
// Full spring body and loops; no end regions omitted from lever checks.
module spring_body_at(t){hull(){
 fy=70;fz=38.6;my=82+7.5*sin(t);mz=31.6+7.5*cos(t);l=sqrt(pow(my-fy,2)+pow(mz-fz,2));
 for(f=[0,1],dx=[-.6,.6])translate([327.5+dx,fy+(my-fy)*f,fz+(mz-fz)*f])sphere(d=3.38,$fn=32);
}}
if(part=="spring_body_lever_clearance")union()for(a=[0:1:34])intersection(){hull(){spring_body_at(a);spring_body_at(a+1);}union(){spring_bracket_world();guard();for(index=[0:5])hull()for(dx=[-.5,.5],t=[a,a+1])translate([dx,0,0])spring_arm_piece(index,t);}}
if(part=="lever_arm_spring")translate([-305,-77,-14])lever_arm_spring(0);

if(part=="spring_bracket")translate([-303,-66,-14.6])spring_bracket_world();

module spring_arm_piece(index,angle){
 if(index<5)translate([0,0,7.6])lever_occupied_piece(index,angle);
 else translate([316,82,31.6])rotate([-angle,0,0])translate([-3.1,-2.1,5.4])cube([6.2,4.2,4.2]);
}
module spring_arm_sweep(delta=.5){for(index=[0:5],a=[0:1:34])hull()for(dx=[-delta,delta],t=[a,a+1])translate([dx,0,0])spring_arm_piece(index,t);}
if(part=="spring_arm_shell_clearance")intersection(){spring_arm_sweep();shell();}
if(part=="spring_arm_components_clearance")intersection(){spring_arm_sweep();box_rows(component_boxes);}
if(part=="spring_arm_controls_clearance")intersection(){spring_arm_sweep();union(){translate([0,0,H])lid();guide_installed();holders_installed();}}
if(part=="spring_arm_carrier_clearance")intersection(){spring_arm_sweep();tbh05_installed();}
if(part=="spring_arm_bracket_clearance")intersection(){spring_arm_sweep(.3);union(){spring_bracket_world();guard();}}
if(part=="spring_bracket_controls_clearance")intersection(){spring_bracket_world();union(){translate([0,0,H])lid();guide_installed();holders_installed();}}
if(part=="spring_bracket_carrier_clearance")intersection(){translate([0,0,-.01])spring_bracket_world();tbh05_installed();}
if(part=="spring_stop_positive")intersection(){spring_bracket_world();translate([0,0,7.6])lever_arm_spring(38);}
if(part=="spring_negative_stop_positive")intersection(){spring_bracket_world();translate([0,0,7.6])lever_arm_spring(-3);}
if(part=="spring_arm_preservation_clearance")difference(){union(){difference(){translate([0,0,7.6])lever_arm(0);translate([0,0,7.6])lever_arm_spring(0);}difference(){translate([0,0,7.6])lever_arm_spring(0);translate([0,0,7.6])lever_arm(0);}}translate([312,79.9,37])cube([8,4.2,6.7]);}
if(part=="spring_bracket_preservation_clearance")difference(){union(){difference(){bracket_world();spring_bracket_world();}difference(){spring_bracket_world();bracket_world();}}translate([312.9,67.9,33.5])cube([6.2,4.2,7.2]);}
module loop_ring(x){translate([x,82,39.1])rotate([0,90,0])difference(){cylinder(d=3.18,h=.36,$fn=48);translate([0,0,-.01])cylinder(d=2.46,h=.38,$fn=48);}}
if(part=="spring_loop_right_retention_positive")intersection(){loop_ring(328);moving_pin(0);}
if(part=="spring_loop_left_retention_positive")intersection(){loop_ring(327);moving_pin(0);}
