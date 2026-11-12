"""Apply two verified surface detours without changing via/zone/part geometry."""
import json,uuid,hashlib
from pathlib import Path
from hardware.electronics.common.sexpr import read_sexpr,sexpr,children,first,a
R=Path(__file__).resolve().parent;I=R.parent/'signal_input'
r=json.loads((R/'reference-detours-r25/routing.json').read_text());d=json.loads((R/'reference-detours-r25/diagnostic.json').read_text());assert not d['blocked'];assert len(d['changes'])==2
assert all(x['net']in ['/A_DAC/IV_P_R','/A_DAC/CM_SUM_R']for x in d['changes'])
b=read_sexpr((I/'native-r7/signal_main.kicad_pcb').read_text());old={first(s,'uuid')[1]for s in children(b,'segment')};t=read_sexpr((R/'candidate-r24/signal_main.kicad_pcb').read_text());t[:]=[v for v in t if not(isinstance(v,list)and v and v[0]=='segment'and first(v,'uuid')[1]not in old)]
for k,x in enumerate(r['routes']):
 for j,(p,q)in enumerate(zip(x['path_mm'],x['path_mm'][1:])):t.append([a('segment'),[a('start'),*p],[a('end'),*q],[a('width'),x['width_mm']],[a('layer'),x['layer']],[a('net'),x['net']],[a('uuid'),str(uuid.uuid5(uuid.NAMESPACE_URL,f'TBH-dac-r26-{k}-{j}'))]])
o=R/'candidate-r26';o.mkdir(exist_ok=False);(o/'signal_main.kicad_pcb').write_text(sexpr(t)+'\n');r['strict_reference_detours']=d['changes'];r['final_detour_source_sha256']={str(p.relative_to(R.parents[3])):hashlib.sha256(p.read_bytes()).hexdigest()for p in [Path(__file__),R/'candidate-r24/signal_main.kicad_pcb',R/'candidate-r24/routing.json',R/'reference-detours-r25/routing.json',R/'reference-detours-r25/diagnostic.json']};(o/'routing.json').write_text(json.dumps(r,indent=2)+'\n');print('Applied two F.Cu detours; original objects and all vias/zones retained')
