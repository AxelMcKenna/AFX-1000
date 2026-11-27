"""Open the added common-mode-sum escape, retaining all original feedback copper."""
import json,hashlib
from pathlib import Path
from hardware.electronics.common.sexpr import read_sexpr,sexpr,children,first
R=Path(__file__).resolve().parent;B=R/'native-r65b';t=read_sexpr((B/'signal_main.kicad_pcb').read_text());baseline=read_sexpr((R.parent/'signal_input/native-r7/signal_main.kicad_pcb').read_text());old={first(x,'uuid')[1]for tag in ['segment','via']for x in children(baseline,tag)}
remove=['aee0ad2f-43a2-5207-8dca-8915ee588c17','11df4be0-1af2-5492-938d-4413e4a9e79a','14b0b9b5-305a-54d0-ab7c-65366103d2a3'];assert not set(remove)&old
r=json.loads((R/'candidate-r65/routing.json').read_text())
for u in remove:
 x=next(x for tag in ['segment','via']for x in children(t,tag)if first(x,'uuid')[1]==u);assert first(x,'net')[1]=='/A_DAC/CM_SUM_L';r['declared_removed_agent_copper'].append({'uuid':u,'net':'/A_DAC/CM_SUM_L','before_sexpr':sexpr(x)});t.remove(x)
r['routes']=[x for x in r['routes']if not(x['net']=='/A_DAC/CM_SUM_L'and x['layer']=='B.Cu'and x['path_mm'][-1]==[127.925,74.235])]
route=next(x for x in r['routes']if x['net']=='/A_DAC/CM_SUM_L'and x['layer']=='In3.Cu');assert route['path_mm'][-1]==[127.925,74.235];route['path_mm']=route['path_mm'][:-1]
r['vias']=[x for x in r['vias']if x['uuid']not in remove];r['transitions']=[x for x in r['transitions']if x['signal_at']!=[127.925,74.235]];r['expected_opens']=194
r['sum_rework_source_sha256']={str(p.relative_to(R.parents[3])):hashlib.sha256(p.read_bytes()).hexdigest()for p in [Path(__file__),B/'signal_main.kicad_pcb',R/'candidate-r65/routing.json',R.parent/'signal_input/native-r7/signal_main.kicad_pcb']}
o=R/'candidate-r67';o.mkdir(exist_ok=False);(o/'signal_main.kicad_pcb').write_text(sexpr(t)+'\n');(o/'routing.json').write_text(json.dumps(r,indent=2)+'\n')
