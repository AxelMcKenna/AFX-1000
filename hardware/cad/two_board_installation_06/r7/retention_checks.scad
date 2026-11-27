use <cooling_candidate.scad>
part="exhaust_escape_out";
if(part=="exhaust_escape_out")intersection(){for(y=[45,145])translate([1,0,0])tbh06_exhaust_mesh(y);for(y=[45,145])tbh06_exhaust_screen_frame(y);}
if(part=="exhaust_escape_in")intersection(){for(y=[45,145])translate([-1,0,0])tbh06_exhaust_mesh(y);tbh06_shell_variant();}
if(part=="bushing_escape_out")intersection(){for(y=[45,145])translate([-1,0,0])tbh06_bushing(y);for(y=[45,145])tbh06_pod(y);}
