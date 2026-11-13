// Exact module block from source recorded in obstacle-sources.json
module cable_segment(a,b,r=4.5){hull(){translate(a)sphere(r=r);translate(b)sphere(r=r);}}
module cable_route(){
 cable_segment([234,55,32],[246,62,32]);
 cable_segment([246,62,32],[265,69.1891892,28]);
 cable_segment([265,69.1891892,28],[283,76,28]);
 cable_segment([283,76,28],[293,82,25.1]);
}
module sensor_fanout(){for(y=[78,80.5,83,85.5])cable_segment([293,82,25.1],[298.2,y,25.1],.7);}
module main_mate(){translate([228.63,53.75,10.89])cube([10.36,2.5,14]);}
module main_fanout(){for(x=[230,232.54,235.08,237.62])cable_segment([x,55,24.89],[234,55,32],.7);}
module tbh05_harness_installed(){cable_route();sensor_fanout();main_mate();main_fanout();}
