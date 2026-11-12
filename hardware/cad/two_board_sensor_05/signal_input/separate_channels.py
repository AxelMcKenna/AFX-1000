"""Separate opposite-channel sensitive routes with intervening In4 ground."""
import json,hashlib
from pathlib import Path
from hardware.electronics.common.sexpr import read_sexpr,sexpr,children,first
R=Path(__file__).resolve().parent;r=json.loads((R/'candidate-r6/routing.json').read_text());t=read_sexpr((R/'candidate-r6/signal_main.kicad_pcb').read_text());count=0
for row in children(t,'segment'):
 if first(row,'net')[1]=='/A_INPUT/HP_SRC_R'and first(row,'layer')[1]=='In3.Cu':first(row,'layer')[1]='In5.Cu';count+=1
assert count==7
for row in r['routes']:
 if row['net']=='/A_INPUT/HP_SRC_R'and row['layer']=='In3.Cu':row['layer']='In5.Cu'
r['channel_separation']={'net':'/A_INPUT/HP_SRC_R','old_layer':'In3.Cu','new_layer':'In5.Cu','intervening_reference':'In4.Cu','reason':'Opposite-channel amplifier input had4.998mm within1mm on same plane; no electrical crosstalk qualification implied','source_sha256':{str(p.relative_to(R.parents[3])):hashlib.sha256(p.read_bytes()).hexdigest()for p in [Path(__file__),R/'candidate-r6/signal_main.kicad_pcb',R/'candidate-r6/routing.json']}}
o=R/'candidate-r7';o.mkdir(exist_ok=False);(o/'signal_main.kicad_pcb').write_text(sexpr(t)+'\n');(o/'routing.json').write_text(json.dumps(r,indent=2)+'\n')
