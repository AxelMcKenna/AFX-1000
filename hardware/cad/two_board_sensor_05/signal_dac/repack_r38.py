"""Explicit same-side translations of two entirely unrouted 0805 passives."""
import json,hashlib
from pathlib import Path
from hardware.electronics.common.sexpr import read_sexpr,children,first,sexpr
R=Path(__file__).resolve().parent
source=R/'native-r26/signal_main.kicad_pcb';capture=R/'capture-r26/capture.json';t=read_sexpr(source.read_text());c=json.loads(capture.read_text())
moves={'A_R303':([120,73],[109,82.5]),'A_R308':([116,68],[120.5,81])};changed=[]
for f in children(t,'footprint'):
 props={v[1]:v[2]for v in children(f,'property')};ref=props.get('Reference')
 if ref not in moves:continue
 before,after=moves[ref];at=first(f,'at');assert list(map(float,at[1:3]))==before and first(f,'layer')[1]=='F.Cu'
 pads=[o for o in c['objects']if o.get('ref')==ref];assert len(pads)==2
 for pad in pads:assert c['all_groups'][pad['group']]==[pad['uuid']],('existing connection would be disturbed',ref,pad['pin'])
 changed.append({'reference':ref,'uuid':first(f,'uuid')[1],'before_mm':before,'after_mm':after,'side':'F.Cu','footprint':f[1]});at[1:3]=after
assert len(changed)==2
out=R/'candidate-r38';out.mkdir(exist_ok=False);(out/'signal_main.kicad_pcb').write_text(sexpr(t)+'\n')
r={'expected_opens':198,'moves':changed,'source_sha256':{str(p.relative_to(R.parents[3])):hashlib.sha256(p.read_bytes()).hexdigest()for p in [Path(__file__),source,capture]}}
(out/'routing.json').write_text(json.dumps(r,indent=2)+'\n')
