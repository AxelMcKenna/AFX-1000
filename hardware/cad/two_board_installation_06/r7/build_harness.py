"""Emit editable route CAD from reviewed numerical controls; no optimization at build time."""
import json
from pathlib import Path
import numpy as np
from optimize_fans_swapped import bern,obs
R=Path(__file__).resolve().parent;d=json.loads((R/'route-pair-search.json').read_text());s=['use <cooling_candidate.scad>','use <../../two_board_print_01/housing.scad>','$fn=24;','part="harness";']
for i,(ref,p) in enumerate(d['control_points'].items()):
 p=np.array(p);pts=bern(5,np.linspace(0,1,161))@p
 # Circumscribing facet/deviation allowance; spheres are deliberately oversized.
 s += ['tbh06_points_'+str(i)+'='+json.dumps(pts.tolist())+';',f'module tbh06_route_{i}(){{for(k=[0:159])hull(){{translate(tbh06_points_{i}[k])sphere(r=2.56);translate(tbh06_points_{i}[k+1])sphere(r=2.56);}}}}']
 # Three terminal wires emerge parallel to the housing, spread within final 10% of route.
 s += [f'module tbh06_terminal_{i}(){{']
 for dx in [-2.5,0,2.5]:
  top=(pts[-1]+[dx,0,0]).tolist();bot=(pts[-1]+[dx,0,-3]).tolist();start=pts[144].tolist()
  s += [f'hull(){{translate({json.dumps(start)})sphere(r=1);translate({json.dumps(top)})sphere(r=1);}}hull(){{translate({json.dumps(top)})sphere(r=1);translate({json.dumps(bot)})sphere(r=1);}}']
 s+=['}',f'module tbh06_obstacles_{i}(){{']
 for name,b in obs:
  if name==ref:continue
  s += [f'translate({json.dumps(b[:3].tolist())})cube({json.dumps((b[3:]-b[:3]).tolist())});']
 s += ['}',f'if(part=="route_{i}_obstacles")intersection(){{union(){{tbh06_route_{i}();tbh06_terminal_{i}();}}tbh06_obstacles_{i}();}}']
s+=['module tbh06_harness(){tbh06_route_0();tbh06_route_1();tbh06_terminal_0();tbh06_terminal_1();}', 'if(part=="harness")tbh06_harness();','if(part=="mutual")intersection(){union(){tbh06_route_0();tbh06_terminal_0();}union(){tbh06_route_1();tbh06_terminal_1();}}','if(part=="shell")intersection(){tbh06_harness();tbh06_shell_variant();}','if(part=="boards")intersection(){tbh06_harness();pcbs();}','if(part=="positive")intersection(){tbh06_harness();translate([2,74,14])cube([3,3,3]);}']
(R/'fan_harness.scad').write_text('\n'.join(s)+'\n')
