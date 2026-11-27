use <../r8/supports.scad>
use <../r8/terminal_harness.scad>
// TBH06 alternative only: external two-fan intake, opposite-side exhaust.
// Coordinate frame and sealed r6 source unchanged. No thermal release.
include <../../two_board_print_01/captured.scad>
use <../../two_board_print_01/housing.scad>
use <../../two_board_print_03/retention_r5.scad>
$fn=64;
part="shell_variant";
W=338;H=43.6;D=192.4;
tbh09_fan_centres=[45,145];
module tbh09_port(y,x=-1){translate([x,y-18,8])cube([5,36,30]);}
module tbh09_bolt(y,z){translate([-2,y,z])rotate([0,90,0])cylinder(d=3.4,h=9);}
module tbh09_nut(y,z){translate([2.8,y,z])rotate([0,90,0])cylinder(d=6.6,h=2.4,$fn=6);}
module tbh09_mounting_holes(){for(c=tbh09_fan_centres,y=[c-26.5,c+26.5],z=[8,38])tbh09_bolt(y,z);}
module tbh09_shell_variant(){difference(){shell();for(y=tbh09_fan_centres){tbh09_port(y);tbh09_port(y,W-4);}tbh09_mounting_holes();tbh09_exhaust_holes();for(y=tbh09_fan_centres)tbh09_lead_bore(y);for(c=tbh09_fan_centres,yy=[c-16,c+16],z=[6.8,38.8])translate([-1,yy,z])rotate([0,90,0])cylinder(d=4.8,h=5);}}
// Pod fan seat lies outside sealed shell: maximum body 40.5 square ×10.5.
// Body cavity 41.5 square. Axial gap shimmed after measuring actual fan.
module tbh09_pod_core(y=0){difference(){union(){
 translate([-15,y-22.75,.05])cube([15,45.5,45.5]);
 translate([-2,y-30,3])cube([2,60,39.6]);
 }translate([-15.1,y-20.75,2.05])cube([12.1,41.5,41.5]);
 hull(){translate([-3.1,y,22.8])rotate([0,90,0])cylinder(d=36,h=.2);translate([-.1,y-18,8])cube([.2,36,30]);}
 for(yy=[y-26.5,y+26.5],z=[8,38])tbh09_bolt(yy,z);
 for(yy=[y-16,y+16],z=[6.8,38.8])translate([-16,yy,z])rotate([0,90,0])cylinder(d=4.8,h=16);
 for(yy=[y-16,y+16],z=[6.8,38.8])translate([-3.4,yy,z])rotate([0,90,0])cylinder(d=7.8/cos(30),h=3.5,$fn=6);
}}
// Cable bay receives factory lead exit on the +Y edge after fan rotation.
// Slot spans fan depth; no unsupported assumption about axial lead emergence.
module tbh09_lead_bore(y){translate([-3,y+30.25,15])rotate([0,90,0])cylinder(d=8.4,h=7);}
module tbh09_lead_cavity(y){translate([-13,y+20.75,5])cube([11,13.65,37.5]);translate([-15.1,y+23,14])cube([2.2,11.4,24]);}
module tbh09_lead_bridge(y){difference(){translate([-10,y+25,9])cube([8.1,10.5,2]);for(yy=[y+26,y+32.9])translate([-5.75,yy,8.9])cube([3,1.4,2.2]);}}
module tbh09_pod(y=0){difference(){union(){difference(){union(){tbh09_pod_core(y);translate([-15,y+20.75,3.5])cube([15,14.75,41]);}tbh09_lead_cavity(y);translate([-15.1,y+20.2,28])cube([12.3,3,12]);}tbh09_lead_bridge(y);
 for(p=[[24.5,6],[32.5,42]])translate([-13,y+p[0]-2.5,p[1]-2.5])cube([7,5.5,5]);}
 tbh09_lead_bore(y);translate([-1.1,y+30.25,15])rotate([0,90,0])cylinder(d=10.4,h=1.2);
 for(p=[[24.5,6],[32.5,42]]){translate([-18,y+p[0],p[1]])rotate([0,90,0])cylinder(d=2.4,h=13);translate([-8.4,y+p[0],p[1]])rotate([0,90,0])cylinder(d=4.2/cos(30),h=1.8,$fn=6);}
}}
module tbh09_lead_cap(y=0){difference(){translate([-17,y+20.75,3.5])cube([2,14.75,41]);for(p=[[24.5,6],[32.5,42]])translate([-18,y+p[0],p[1]])rotate([0,90,0])cylinder(d=2.4,h=4);}}
module tbh09_bushing(y=0){difference(){union(){translate([-1,y+30.25,15])rotate([0,90,0])cylinder(d=8.2,h=4);translate([-1,y+30.25,15])rotate([0,90,0])cylinder(d=10,h=.9);}translate([-1.1,y+30.25,15])rotate([0,90,0])cylinder(d=6.2,h=4.2);translate([-1.01,y+30.25,15])rotate([0,90,0])cylinder(d1=7,d2=6.2,h=.5);translate([2.51,y+30.25,15])rotate([0,90,0])cylinder(d1=6.2,d2=7,h=.5);}}
module tbh09_lead_hardware(){for(y=tbh09_fan_centres,p=[[24.5,6],[32.5,42]]){translate([-18.6,y+p[0],p[1]])rotate([0,90,0])cylinder(d=4,h=1.6);translate([-17,y+p[0],p[1]])rotate([0,90,0])cylinder(d=2,h=12);translate([-8.3,y+p[0],p[1]])rotate([0,90,0])cylinder(d=4/cos(30),h=1.6,$fn=6);}}
module tbh09_lead_parts(){for(y=tbh09_fan_centres){tbh09_lead_cap(y);tbh09_bushing(y);}tbh09_lead_hardware();}
// Separate tbh09_guard: four M4 fan bolts with floating captive nuts retain body without crediting printed friction.
// Slots need a separately retained fine mesh for finger/wire exclusion.
module tbh09_guard(y=0){difference(){translate([-17,y-22.75,.05])cube([2,45.5,45.5]);
 translate([-18,y,22.8])rotate([0,90,0])cylinder(d=36,h=4);
 for(yy=[y-16,y+16],z=[6.8,38.8])translate([-18,yy,z])rotate([0,90,0])cylinder(d=4.8,h=4);
}}
module tbh09_fans(){for(y=tbh09_fan_centres)difference(){translate([-14,y-20.25,2.55])cube([10.5,40.5,40.5]);for(yy=[y-16,y+16],z=[6.8,38.8])translate([-15,yy,z])rotate([0,90,0])cylinder(d=4,h=13);}}
module tbh09_hardware(){for(c=tbh09_fan_centres,y=[c-26.5,c+26.5],z=[8,38]){translate([-4.5,y,z])rotate([0,90,0])cylinder(d=5.5,h=2.5);translate([-2,y,z])rotate([0,90,0])cylinder(d=3,h=8);tbh09_nut(y,z);}for(c=tbh09_fan_centres,y=[c-16,c+16],z=[6.8,38.8]){translate([-21,y,z])rotate([0,90,0])cylinder(d=7,h=4);translate([-17,y,z])rotate([0,90,0])cylinder(d=4,h=20);translate([-3.3,y,z])rotate([0,90,0])cylinder(d=7/cos(30),h=3.2,$fn=6);}}
// Howard 304 SS woven 10 mesh, .010 inch wire. Exact nominal wire visual.
// Cut 41×41, deburr, retain perimeter between guard and fan frame/shims.
module tbh09_mesh(y=0){difference(){intersection(){translate([-15,y-20.5,2.3])cube([.6,41,41]);union(){for(a=[-10:10]){translate([-14.85,y+a*2.54,0])cylinder(d=.254,h=46,$fn=12);translate([-14.596,y-23,22.8+a*2.54])rotate([-90,0,0])cylinder(d=.254,h=46,$fn=12);}}}for(yy=[y-16,y+16],z=[6.8,38.8])translate([-16,yy,z])rotate([0,90,0])cylinder(d=4.8,h=3);}}
module tbh09_meshes(){for(y=tbh09_fan_centres)tbh09_mesh(y);}
module tbh09_base_installed(){for(y=tbh09_fan_centres){tbh09_pod(y);tbh09_guard(y);}tbh09_hardware();tbh09_meshes();tbh09_exhausts();tbh09_lead_parts();}
module tbh09_exhaust_holes(){for(c=tbh09_fan_centres,y=[c-20,c+20],z=[6,40])translate([332,y,z])rotate([0,90,0])cylinder(d=2.4,h=11);}
// 44x38 mesh is positively trapped by a 36x30 aperture and four M2 bolts.
module tbh09_exhaust_screen_frame(y=0){difference(){translate([338,y-24,2])cube([3,48,42]);translate([337.9,y-18,8])cube([3.2,36,30]);translate([337.9,y-22.1,3.9])cube([.7,44.2,38.2]);for(yy=[y-20,y+20],z=[6,40])translate([337,yy,z])rotate([0,90,0])cylinder(d=2.4,h=5);}}
module tbh09_exhaust_mesh(y=0){difference(){intersection(){translate([338.01,y-22,4])cube([.58,44,38]);union(){for(a=[-10:10]){translate([338.15,y+a*2.54,0])cylinder(d=.254,h=46,$fn=12);translate([338.404,y-25,23+a*2.54])rotate([-90,0,0])cylinder(d=.254,h=50,$fn=12);}}}for(yy=[y-20,y+20],z=[6,40])translate([337,yy,z])rotate([0,90,0])cylinder(d=2.4,h=5);}}
module tbh09_exhaust_hardware(){for(c=tbh09_fan_centres,y=[c-20,c+20],z=[6,40]){translate([333,y,z])rotate([0,90,0])cylinder(d=2,h=8);translate([341,y,z])rotate([0,90,0])cylinder(d=4,h=1.6);translate([333.6,y,z])rotate([0,90,0])cylinder(d=4/cos(30),h=1.6,$fn=6);}}
module tbh09_exhausts(){for(y=tbh09_fan_centres){tbh09_exhaust_screen_frame(y);tbh09_exhaust_mesh(y);}tbh09_exhaust_hardware();}
if(part=="shell_variant")tbh09_shell_variant();
if(part=="pod")translate([0,30,0])tbh09_pod();
if(part=="guard")translate([0,22.75,0])tbh09_guard();
if(part=="exhaust_frame")translate([-338,24,-2])tbh09_exhaust_screen_frame();
if(part=="assembly"){color("gray")tbh09_shell_variant();color("orange")tbh09_installed();color("blue")tbh09_fans();}
if(part=="hardware_components")intersection(){tbh09_hardware();box_rows(component_boxes);}
if(part=="hardware_controls")intersection(){tbh09_hardware();box_rows(context_boxes);}
if(part=="pod_components")intersection(){tbh09_installed();box_rows(component_boxes);}
if(part=="mesh_fan_clearance")intersection(){tbh09_meshes();tbh09_fans();}
if(part=="fan_pod_clearance")intersection(){tbh09_fans();for(y=tbh09_fan_centres){tbh09_pod(y);tbh09_guard(y);}}
if(part=="shell_components")intersection(){tbh09_shell_variant();box_rows(component_boxes);}
if(part=="positive_control")intersection(){tbh09_installed();translate([-16,23,1])cube([2,2,2]);}

if(part=="mesh_hardware_clearance")intersection(){tbh09_meshes();tbh09_hardware();}

if(part=="exhaust_components")intersection(){tbh09_exhausts();box_rows(component_boxes);}
if(part=="exhaust_controls")intersection(){tbh09_exhausts();box_rows(context_boxes);}
if(part=="exhaust_lever")intersection(){tbh09_exhausts();union(){guard();bracket_world();axial_motion();}}
if(part=="exhaust_mesh_frame")intersection(){for(y=tbh09_fan_centres)tbh09_exhaust_mesh(y);for(y=tbh09_fan_centres)tbh09_exhaust_screen_frame(y);}
if(part=="exhaust_positive")intersection(){for(y=tbh09_fan_centres)tbh09_exhaust_screen_frame(y);translate([338.5,21.5,3])cube([1,1,1]);}

if(part=="lead_cap")translate([17,-20.75,-3.5])tbh09_lead_cap();
if(part=="lead_bushing")translate([1,-30.25,-10])tbh09_bushing();
if(part=="lead_components")intersection(){tbh09_lead_parts();box_rows(component_boxes);}
if(part=="lead_controls")intersection(){tbh09_lead_parts();box_rows(context_boxes);}
if(part=="lead_fans")intersection(){tbh09_lead_parts();tbh09_fans();}
if(part=="bushing_shell")intersection(){for(y=tbh09_fan_centres)tbh09_bushing(y);tbh09_shell_variant();}
if(part=="bushing_pod")intersection(){for(y=tbh09_fan_centres)tbh09_bushing(y);for(y=tbh09_fan_centres)tbh09_pod(y);}
if(part=="bushing_retention_positive")intersection(){for(y=tbh09_fan_centres)translate([1,0,0])tbh09_bushing(y);tbh09_shell_variant();}

// Loose pre-tightening strap path, 2.5 width x1.1 thickness, received T18R.
module tbh09_tie_paths(){for(y=tbh09_fan_centres){for(yy=[y+26.1,y+33])translate([-5.5,yy,7.4])cube([2.5,1.1,13]);for(z=[7.4,19.3])translate([-5.5,y+26.1,z])cube([2.5,8,1.1]);}}
if(part=="tie_bridge_clearance")intersection(){tbh09_tie_paths();for(y=tbh09_fan_centres)tbh09_lead_bridge(y);}
if(part=="tie_retention_positive")intersection(){translate([1,0,0])tbh09_tie_paths();for(y=tbh09_fan_centres)tbh09_lead_bridge(y);}

module tbh09_installed(){difference(){tbh09_base_installed();for(y=[118.5,171.5])translate([2.7,y-4,34])cube([5,8,8]);}tbh08_supports();tbh08_replacement_fasteners();}

tbh09_external_points=[[-11, 22.85, 34.65608616365865], [-11, 23.007495323511016, 34.612295227510174], [-11, 23.16425377745702, 34.565935653169404], [-11, 23.32023347218083, 34.51701982903789], [-11, 23.475392726128614, 34.46556082660909], [-11, 23.629690076988172, 34.411572396975316], [-11, 23.783084292768706, 34.3550689671531], [-11, 23.935534382818997, 34.29606563622799], [-11, 24.086999608781085, 34.23457817131967], [-11, 24.237439495476572, 34.17062300336861], [-11, 24.386813841722542, 34.10421722274533], [-11, 24.535082731074322, 34.03537857468344], [-11, 24.682206542492093, 33.96412545453768], [-11, 24.82814596092861, 33.89047690286821], [-11, 24.97286198783513, 33.81445260035256], [-11, 25.11631595158277, 33.73607286252645], [-11, 25.258469517796502, 33.655358634354975], [-11, 25.399284699599033, 33.572331484635626], [-11, 25.53872386776181, 33.48701360023457], [-11, 25.676749760760462, 33.39942778015778], [-11, 25.81332549473199, 33.309597429458606], [-11, 25.94841457333103, 33.21754655298335], [-11, 26.081980897482538, 33.123299748956626], [-11, 26.213988775028376, 33.026882202408075], [-11, 26.34440293026509, 32.92831967844236], [-11, 26.47318851337044, 32.82763851535405], [-11, 26.60031110971613, 32.724865617589465], [-11, 26.72573674906421, 32.620028448557086], [-11, 26.849431914644768, 32.51315502328869], [-11, 26.971363552112397, 32.404273900953086], [-11, 27.091499078379147, 32.293414177224356], [-11, 27.2098063903215, 32.18060547650684], [-11, 27.326253873359093, 32.06587794401874], [-11, 27.440810409902916, 31.949262237736598], [-11, 27.553445387670685, 31.830789520202757], [-11, 27.66412870786717, 31.710491450197956], [-11, 27.77283079322735, 31.588400174281336], [-11, 27.87952259592014, 31.464548318200123], [-11, 27.984175605310696, 31.338968978171206], [-11, 28.086761855579162, 31.21169571203705], [-11, 28.187253933193773, 31.08276253029822], [-11, 28.285624984236453, 30.95220388702495], [-11, 28.38184872157882, 30.820054670650176], [-11, 28.475899431906733, 30.686350194646515], [-11, 28.567751982591535, 30.551126188089636], [-11, 28.657381828406077, 30.41441878611059], [-11, 28.74476501808381, 30.276264520239632], [-11, 28.829878200719147, 30.136700308644098], [-11, 28.912698632007377, 29.995763446262995], [-11, 28.99320418032251, 29.853491594840868], [-11, 29.071373332631374, 29.7099227728637], [-11, 29.147185200242415, 29.565095345399406], [-11, 29.22061952438768, 29.419048013845803], [-11, 29.291656681636425, 29.27181980558864], [-11, 29.360277689139, 29.123450063572513], [-11, 29.426464209699493, 28.973978435787526], [-11, 29.490198556675903, 28.823444864674336], [-11, 29.551463698706424, 28.671889576450603], [-11, 29.610243264260646, 28.519353070361547], [-11, 29.6665215460144, 28.365876107857584], [-11, 29.72028350504719, 28.211499701701864], [-11, 29.771514774860883, 28.056265105010677], [-11, 29.820201665218853, 27.900213800229615], [-11, 29.866331165804297, 27.74338748804848], [-11, 29.909890949696944, 27.585828076257798], [-11, 29.950869376667065, 27.427577668550096], [-11, 29.98925549628607, 27.268678553268753], [-11, 30.025039050852687, 27.109173192107516], [-11, 30.0582104781341, 26.94910420876373], [-11, 30.088760913921185, 26.788514377548246], [-11, 30.11668219439726, 26.62744661195508], [-11, 30.14196685831965, 26.465943953193896], [-11, 30.16460814901349, 26.304049558688355], [-11, 30.184600016177317, 26.141806690543394], [-11, 30.201937117499813, 25.979258703984556], [-11, 30.216614820087425, 25.816449035772408], [-11, 30.22862920170238, 25.653421192595214], [-11, 30.237977051810795, 25.490218739442845], [-11, 30.244655872440624, 25.326885287965222], [-11, 30.24866387884917, 25.163464484818167], [-11, 30.25, 25.0], [-10.998072404820649, 30.25, 24.803663075393718], [-10.992290362407228, 30.25, 24.607401842409313], [-10.982656101847159, 30.25, 24.41129196348811], [-10.969173337331279, 30.25, 24.21540904272155], [-10.95184726672197, 30.25, 24.019828596704393], [-10.930684569549262, 30.25, 23.824626025421622], [-10.905693404435773, 30.25, 23.62987658318032], [-10.876883405951379, 30.25, 23.435655349597692], [-10.844265680898916, 30.25, 23.242037200656455], [-10.807852804032304, 30.25, 23.049096779838717], [-10.767658813208724, 30.25, 22.85690846934949], [-10.723699203976766, 30.25, 22.665546361440946], [-10.675990923602598, 30.25, 22.47508422984842], [-10.624552364536473, 30.25, 22.285595501349256], [-10.569403357322088, 30.25, 22.097153227455376], [-10.510565162951535, 30.25, 21.909830056250527], [-10.44806046466878, 30.25, 21.723698204383066], [-10.381913359224841, 30.25, 21.53882942922507], [-10.312149347588036, 30.25, 21.355295001208503], [-10.238795325112868, 30.25, 21.1731656763491], [-10.16187957117136, 30.25, 20.99251166896859], [-10.081431738250814, 30.25, 20.81340262462572], [-9.997482840522215, 30.25, 20.63590759326658], [-9.910065241883679, 30.25, 20.460095002604533], [-9.819212643483551, 30.25, 20.286032631740024], [-9.724960070727972, 30.25, 20.11378758503045], [-9.627343859777918, 30.25, 19.943426266220154], [-9.526401643540924, 30.25, 19.77501435284051], [-9.422172337162866, 30.25, 19.60861677089], [-9.314696123025453, 30.25, 19.44429766980398], [-9.204014435255136, 30.25, 19.28212039772388], [-9.090169943749475, 30.25, 19.122147477075266], [-8.973206537727071, 30.25, 18.964440580464284], [-8.853169308807448, 30.25, 18.80906050690166], [-8.730104533627369, 30.25, 18.656067158363545], [-8.60405965600031, 30.25, 18.505519516698165], [-8.47508326862597, 30.25, 18.357475620887183], [-8.343225094356855, 30.25, 18.211992544670583], [-8.208535967029189, 30.25, 18.069126374543643], [-8.071067811865476, 30.25, 17.928932188134524], [-7.93087362545636, 30.25, 17.791464032970815], [-7.788007455329418, 30.25, 17.656774905643147], [-7.6425243791128175, 30.25, 17.52491673137403], [-7.494480483301838, 30.25, 17.39594034399969], [-7.343932841636455, 30.25, 17.26989546637263], [-7.190939493098339, 30.25, 17.14683069119255], [-7.035559419535713, 30.25, 17.026793462272927], [-6.877852522924732, 30.25, 16.909830056250527], [-6.717879602276124, 30.25, 16.795985564744868], [-6.555702330196023, 30.25, 16.685303876974547], [-6.391383229110004, 30.25, 16.577827662837137], [-6.224985647159489, 30.25, 16.473598356459078], [-6.056573733779846, 30.25, 16.372656140222084], [-5.88621241496955, 30.25, 16.27503992927203], [-5.713967368259976, 30.25, 16.180787356516447], [-5.539904997395468, 30.25, 16.08993475811632], [-5.3640924067334215, 30.25, 16.002517159477787], [-5.186597375374282, 30.25, 15.918568261749188], [-5.0074883310314116, 30.25, 15.838120428828642], [-4.826834323650898, 30.25, 15.761204674887132], [-4.644704998791496, 30.25, 15.687850652411964], [-4.4611705707749305, 30.25, 15.618086640775159], [-4.276301795616934, 30.25, 15.55193953533122], [-4.0901699437494745, 30.25, 15.489434837048465], [-3.902846772544625, 30.25, 15.430596642677912], [-3.714404498650743, 30.25, 15.375447635463527], [-3.524915770151581, 30.25, 15.324009076397402], [-3.334453638559055, 30.25, 15.276300796023234], [-3.1430915306505067, 30.25, 15.232341186791276], [-2.9509032201612833, 30.25, 15.192147195967696], [-2.7579627993435443, 30.25, 15.155734319101082], [-2.564344650402309, 30.25, 15.123116594048621], [-2.3701234168196823, 30.25, 15.094306595564227], [-2.175373974578377, 30.25, 15.069315430450738], [-1.9801714032956077, 30.25, 15.048152733278032], [-1.78459095727845, 30.25, 15.030826662668721], [-1.58870803651189, 30.25, 15.017343898152841], [-1.3925981575906867, 30.25, 15.007709637592772], [-1.1963369246062825, 30.25, 15.001927595179351], [-1.0000000000000007, 30.25, 15.0], [3, 30.25, 15]];
module tbh09_external_leads(){for(y=tbh09_fan_centres,k=[0:160])hull(){translate(tbh09_external_points[k]+[0,y,0])sphere(r=2.57,$fn=32);translate(tbh09_external_points[k+1]+[0,y,0])sphere(r=2.57,$fn=32);}}
module tbh09_tie_head_reservations(){for(y=tbh09_fan_centres)translate([-8,y+27.7,5.1])cube([5.5,5.5,3.4]);}
module tbh09_harness(){tbh08_harness();tbh09_external_leads();}
if(part=="external_pod")intersection(){tbh09_external_leads();for(y=tbh09_fan_centres)tbh09_pod(y);}
if(part=="external_parts")intersection(){tbh09_external_leads();tbh09_lead_parts();}
if(part=="external_fans")intersection(){tbh09_external_leads();tbh09_fans();}
if(part=="external_ties")intersection(){tbh09_external_leads();tbh09_tie_paths();}
if(part=="ties_pod")intersection(){tbh09_tie_paths();for(y=tbh09_fan_centres)tbh09_pod(y);}
if(part=="ties_parts")intersection(){tbh09_tie_paths();tbh09_lead_parts();}
if(part=="head_pod")intersection(){tbh09_tie_head_reservations();for(y=tbh09_fan_centres)tbh09_pod(y);}
if(part=="head_parts")intersection(){tbh09_tie_head_reservations();tbh09_lead_parts();}
if(part=="head_leads")intersection(){tbh09_tie_head_reservations();tbh09_external_leads();}
if(part=="external_harness")tbh09_harness();
if(part=="tie_positive")intersection(){translate([1,0,0])tbh09_tie_paths();for(y=tbh09_fan_centres)tbh09_lead_bridge(y);}
