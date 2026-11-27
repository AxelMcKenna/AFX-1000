"""Offset only the new RX_NEG_L join from the foreign RX_NEG_R via reference opening."""
import json,uuid,hashlib,copy
from pathlib import Path
from hardware.electronics.common.sexpr import read_sexpr,sexpr,children,first,a
R=Path(__file__).resolve().parent
r=json.loads((R/'candidate-r56/routing.json').read_text());t=read_sexpr((R/'candidate-r56/signal_main.kicad_pcb').read_text());v=r['routes'][-1]
assert v['net']=='/A_DAC/RX_NEG_L' and v['layer']=='In5.Cu' and v['path_mm']==[[127.02,72.27375],[120.6125,80.0]]
u=str(uuid.uuid5(uuid.NAMESPACE_URL,'TBH-dac-r56-4-0'));row=next(x for x in children(t,'segment')if first(x,'uuid')[1]==u);t.remove(row)
v['path_mm'][1:1]=[[121.60765,78.8],[121.2,79.7]]
for k,(p,q)in enumerate(zip(v['path_mm'],v['path_mm'][1:])):
 x=copy.deepcopy(row);first(x,'start')[1:]=p;first(x,'end')[1:]=q;first(x,'uuid')[1]=str(uuid.uuid5(uuid.NAMESPACE_URL,f'TBH-dac-r61-detour-{k}'));t.append(x)
r['detour_source_sha256']={str(p.relative_to(R.parents[3])):hashlib.sha256(p.read_bytes()).hexdigest()for p in [Path(__file__),R/'candidate-r56/routing.json',R/'candidate-r56/signal_main.kicad_pcb',R/'reference-review-r58.json']}
o=R/'candidate-r61';o.mkdir(exist_ok=False);(o/'signal_main.kicad_pcb').write_text(sexpr(t)+'\n');(o/'routing.json').write_text(json.dumps(r,indent=2)+'\n')
