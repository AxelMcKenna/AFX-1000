"""Bind checked native PCB placements to conservative populated mechanical envelopes."""
import json,hashlib
from pathlib import Path
from hardware.electronics.common.sexpr import read_sexpr,children,first
R=Path(__file__).resolve().parent
p=R/'pcb/native-r3/sensor.kicad_pcb'
t=read_sexpr(p.read_text());placements={}
for fp in children(t,'footprint'):
 ref=next(v[2] for v in children(fp,'property') if v[1]=='Reference')
 at=first(fp,'at');placements[ref]=[float(v) for v in at[1:3]]
assert placements['U1']==[10,10] and placements['C1']==[4.8,8.095]
s='include <spring.scad>\nmodule actual_population(){\n'
for ref,size,height in [('U1',[7.2,5.4],1.75),('C1',[2.8,1.46],1.0)]:
 x,y=placements[ref];s+=f'translate([301.3,{72+x-size[0]/2},{21.6+y-size[1]/2}])cube([{height},{size[0]},{size[1]}]);\n'
for ref in ['W1','W2','W3','W4']:
 x,y=placements[ref];s+=f'translate([298.2,{72+x-.9},{21.6+y-.9}])cube([3.7,1.8,1.8]);\n'
s+='sensor_wiring_envelope();}\n'
s+='if(part=="population_carrier_clearance")intersection(){actual_population();union(){carrier_complete();sensor_cap();}}\n'
s+='if(part=="population_shell_clearance")intersection(){actual_population();shell();}\n'
s+='if(part=="population_controls_clearance")intersection(){actual_population();union(){translate([0,0,H])lid();guide_installed();holders_installed();}}\n'
s+='if(part=="population_rotor_clearance")intersection(){actual_population();union(){spring_arm_sweep(.5);spring_bracket_world();spring_installed_envelope();}}\n'
(R/'population.scad').write_text(s)
(R/'population-contract.json').write_text(json.dumps({'checked_pcb_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'placements_mm':placements,'population_scad_sha256':hashlib.sha256(s.encode()).hexdigest(),'scope':'Conservative physical courtyard and solder/wire envelope; field, solder workmanship and harness qualification pending'},indent=2)+'\n')
