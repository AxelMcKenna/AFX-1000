if(proof_case=="solid")cube([1,1,1]);
if(proof_case=="witness")intersection(){cube([1,1,1]);translate([.4,.4,.4])cube([.2,.2,.2]);}
if(proof_case=="empty")intersection(){cube([1,1,1]);translate([2,2,2])cube([1,1,1]);}
