// RECEIVING PROPOSAL ONLY: custom FR4 shims, material/process unaccepted.
shims=[["NF", 210, 42.5], ["NF", 310, 42.5], ["FPC", 31, 41.5], ["FPC", 68.5, 41.5]];
module thin_edge_shims(){for(p=shims)for(z=[3.5,p[2]-1.2])
translate([p[1]-3,181.7,z])cube([6,.4,1.2]);}
thin_edge_shims();
