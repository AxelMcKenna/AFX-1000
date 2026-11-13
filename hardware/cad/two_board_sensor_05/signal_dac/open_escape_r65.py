"""Remove only five agent-added CM_DRV_L objects to evaluate a different escape."""
import json,hashlib
from pathlib import Path
from hardware.electronics.common.sexpr import read_sexpr,sexpr,children,first
R=Path(__file__).resolve().parent;B=R/'native-r62';t=read_sexpr((B/'signal_main.kicad_pcb').read_text());baseline=read_sexpr((R.parent/'signal_input/native-r7/signal_main.kicad_pcb').read_text());old={first(x,'uuid')[1]for tag in ['segment','via']for x in children(baseline,tag)}
remove=['248c314b-addf-57f7-abd8-d56336a80bf6','8ebbc319-48a1-5d8a-b92c-7629dfaea8ac','e42d5abc-43ca-5bf2-a4cd-00f46bae27d1','fae11e9b-c5a2-5be1-94fe-244829570f8a','13338da4-66a1-5c6f-b10c-6d295e7123c3'];assert not set(remove)&old
inventory=[]
for u in remove:
 x=next(x for tag in ['segment','via']for x in children(t,tag)if first(x,'uuid')[1]==u);assert first(x,'net')[1]=='/A_DAC/CM_DRV_L';inventory.append({'uuid':u,'net':'/A_DAC/CM_DRV_L','before_sexpr':sexpr(x)});t.remove(x)
r=json.loads((R/'candidate-r62/routing.json').read_text());r['routes']=[x for x in r['routes']if not(x['net']=='/A_DAC/CM_DRV_L'and x['layer']=='B.Cu'and x['role']=='escape')]
route=next(x for x in r['routes']if x['net']=='/A_DAC/CM_DRV_L'and x['layer']=='In3.Cu');assert route['path_mm'][0]==[128.525,75.905];route['path_mm']=route['path_mm'][1:]
r['vias']=[x for x in r['vias']if x['uuid']not in remove];r['transitions']=[x for x in r['transitions']if x['signal_at']!=[128.525,75.905]];r['expected_opens']=193;r['declared_removed_agent_copper']=inventory;r['reference_additions_pending']=True
r['rework_source_sha256']={str(p.relative_to(R.parents[3])):hashlib.sha256(p.read_bytes()).hexdigest()for p in [Path(__file__),B/'signal_main.kicad_pcb',R/'candidate-r62/routing.json',R.parent/'signal_input/native-r7/signal_main.kicad_pcb']}
o=R/'candidate-r65';o.mkdir(exist_ok=False);(o/'signal_main.kicad_pcb').write_text(sexpr(t)+'\n');(o/'routing.json').write_text(json.dumps(r,indent=2)+'\n')
