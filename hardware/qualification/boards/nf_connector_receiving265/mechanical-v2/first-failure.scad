case_name="old_pair";
module box(x,y,z,w,d,h){translate([x,y,z])cube([w,d,h]);}
if(case_name=="old_pair")intersection(){box(65.35,18.35,-.25,10.3,5.3,3.6);box(75.6,18.6,0,9.8,4.8,3.1);}
if(case_name=="new_pair")intersection(){box(65.35,18.35,-.25,10.3,5.3,3.6);box(76.6,18.6,0,9.8,4.8,3.1);}
