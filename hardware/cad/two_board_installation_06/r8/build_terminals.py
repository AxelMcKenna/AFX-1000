"""Emit source-defined, separated individual wire fanouts; frozen support geometry unchanged."""
import json,sys,math
from pathlib import Path
import numpy as np
R=Path(__file__).resolve().parent;sys.path.insert(0,str(R.parent/'r7'));from optimize_fans_swapped import bern
D=json.loads((R/'terminal-routes.json').read_text());assert D['accepted'];s=['use <../r7/fan_harness.scad>','use <../r7/cooling_candidate.scad>','use <supports.scad>','$fn=32;','part="harness";']
for i,row in enumerate(D['rows']):
 cp=np.array(row['control_points']);pts=bern(5,np.linspace(0,1,161))@cp
 amax=np.linalg.norm(20*np.diff(cp,n=2,axis=0),axis=1).max();required=(.95+amax/(8*160**2))/math.cos(math.pi/32)**2;assert required<.97
 pts=np.concatenate([pts,[pts[-1]-[0,0,3]]]);s += [f'tbh08_wire_points_{i}='+json.dumps(pts.tolist())+';',f'module tbh08_wire_{i}(){{for(k=[0:160])hull(){{translate(tbh08_wire_points_{i}[k])sphere(r=.97);translate(tbh08_wire_points_{i}[k+1])sphere(r=.97);}}}}']
s+=['module tbh08_terminal_wires(){'+''.join(f'tbh08_wire_{i}();' for i in range(6))+'}','module tbh08_harness(){tbh06_route_0();tbh06_route_1();tbh08_terminal_wires();}','if(part=="harness")tbh08_harness();','if(part=="supports")intersection(){tbh08_harness();tbh08_supports();}','if(part=="components")union(){intersection(){union(){tbh08_wire_0();tbh08_wire_1();tbh08_wire_2();}tbh06_obstacles_0();}intersection(){union(){tbh08_wire_3();tbh08_wire_4();tbh08_wire_5();}tbh06_obstacles_1();}}','if(part=="shell")intersection(){tbh08_harness();tbh06_shell_variant();}']
s+=['if(part=="mutual_wires")union(){'+''.join(f'intersection(){{tbh08_wire_{i}();tbh08_wire_{j}();}}' for i in range(6) for j in range(i))+'}','if(part=="positive")intersection(){tbh08_harness();translate([2,74,14])cube([3,3,3]);}']
(R/'terminal_harness.scad').write_text('\n'.join(s)+'\n')
