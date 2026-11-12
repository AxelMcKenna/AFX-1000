"""Generate bolt-retained fan bundle saddle candidates from frozen r7 curves."""
import json,sys
from pathlib import Path
import numpy as np
R=Path(__file__).resolve().parent
sys.path.insert(0,str(R.parent/'r7'))
from optimize_fans_swapped import bern,obs
p=json.loads((R.parent/'r7/route-pair-search.json').read_text())['control_points']
seats=[]
for ref,t,bolt in [('F_J202',.4,171.5),('F_J203',.5,118.5),('F_J203',.84,171.5)]:
 pts=bern(5,np.array([t-.015,t,t+.015]))@np.array(p[ref]);seats.append([ref,pts.tolist(),bolt])
s=['use <../r7/fan_harness.scad>','use <../r7/cooling_candidate.scad>','$fn=32;','part="supports";','tbh08_seats='+json.dumps(seats)+';']
s += ['tbh08_curves='+json.dumps([(bern(5,np.linspace(0,1,161))@np.array(v)).tolist() for v in p.values()])+';']
s += ['''module tbh08_bore(y){translate([2,y,38])rotate([0,90,0])cylinder(d=3.4,h=7);}
module tbh08_plate(y){difference(){translate([2.8,y-4,21])cube([1.6,8,21]);tbh08_bore(y);}}
module tbh08_saddle(row){p=row[1][1];y=row[2];difference(){union(){
 hull(){translate([3.2,y-2,p[2]-4.5])cube([1.2,4,1.5]);translate([p[0]-4,p[1]-2,p[2]-4.5])cube([8,4,1.5]);}
 hull(){for(v=[row[1][0],row[1][2]])translate(v)sphere(r=3.8);}
 }hull(){for(v=[row[1][0],row[1][2]])translate(v)sphere(r=2.95);}
}}

module tbh08_channels(){for(curve=tbh08_curves,k=[0:159])hull(){translate(curve[k])sphere(r=2.95);translate(curve[k+1])sphere(r=2.95);}}
module tbh08_supports(){difference(){union(){for(y=[118.5,171.5])tbh08_plate(y);for(row=tbh08_seats)tbh08_saddle(row);}tbh08_channels();}}
module tbh08_replacement_fasteners(){for(y=[118.5,171.5]){translate([2.7,y,38])rotate([0,90,0])cylinder(d=3,h=5.3);translate([4.5,y,38])rotate([0,90,0])cylinder(d=6.6,h=2.4,$fn=6);}}
module tbh08_installed(){difference(){tbh06_installed();for(y=[118.5,171.5])translate([2.7,y-4,34])cube([5,8,8]);}tbh08_supports();tbh08_replacement_fasteners();}
module tbh08_obstacles(){''']
for name,b in obs:s+=[f'translate({json.dumps(b[:3].tolist())})cube({json.dumps((b[3:]-b[:3]).tolist())});']
s+=['}', 'if(part=="supports")tbh08_supports();','if(part=="components")intersection(){tbh08_supports();tbh08_obstacles();}','if(part=="harness")intersection(){tbh08_supports();tbh06_harness();}','if(part=="shell")intersection(){tbh08_supports();difference(){tbh06_shell_variant();for(y=[118.5,171.5])translate([2.79,y-4.01,20.99])cube([.02,8.02,21.02]);}}','if(part=="hardware")intersection(){tbh08_supports();tbh08_replacement_fasteners();}','if(part=="retention_positive")intersection(){tbh08_supports();translate([2,0,0])tbh06_harness();}','if(part=="positive")intersection(){tbh08_supports();translate([3,115,24])cube([1,1,1]);}']
(R/'supports.scad').write_text('\n'.join(s)+'\n');(R/'support-datums.json').write_text(json.dumps(seats,indent=2)+'\n')
