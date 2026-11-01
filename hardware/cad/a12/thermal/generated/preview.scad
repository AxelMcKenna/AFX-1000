include <thermal-base.scad>
part="assembly";
if(part=="assembly")thermal_assembly();
if(part=="base")thermal_metal_base();
