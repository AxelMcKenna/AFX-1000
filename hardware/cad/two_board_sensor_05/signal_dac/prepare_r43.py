"""Retain the productive R303 translation and route; restore unrouted R308."""
import json,hashlib,math
from pathlib import Path
from hardware.electronics.common.sexpr import read_sexpr,sexpr,children,first
R=Path(__file__).resolve().parent
old=json.loads((R/'candidate-r26/routing.json').read_text());new=json.loads((R/'candidate-r42/routing.json').read_text());moves=json.loads((R/'candidate-r38/routing.json').read_text())['moves'];t=read_sexpr((R/'candidate-r42/signal_main.kicad_pcb').read_text())
assert not new['planned_ground_returns'] and {v['net']for v in new['routes']}=={'/A_DAC/CM_DRV_L'}
for f in children(t,'footprint'):
 if any(v[1]=='Reference'and v[2]=='A_R308'for v in children(f,'property')):first(f,'at')[1:3]=[116,68]
new['routes']=old['routes']+new['routes'];new['vias']=old['vias']+new['vias'];new['moves']=[m for m in moves if m['reference']=='A_R303'];new['blocked']=[b for b in old['blocked']if b['net']!='/A_DAC/CM_DRV_L']
new['transitions']=old['transitions'][:];c=json.loads((R/'capture-r26/capture.json').read_text())
for v in new['used_return_sites']:
 q=next(o for o in c['objects']if o['kind']=='PCB_VIA'and o['net']=='LINK_AGND'and o['position_mm']==v['return_at'])
 new['transitions'].append({**v,'return_uuid':q['uuid'],'kind':'existing native ground via','distance_mm':math.dist(v['signal_at'],v['return_at'])})
new['assembly_source_sha256']={str(p.relative_to(R.parents[3])):hashlib.sha256(p.read_bytes()).hexdigest()for p in [Path(__file__),R/'candidate-r26/routing.json',R/'candidate-r42/routing.json',R/'candidate-r42/signal_main.kicad_pcb',R/'candidate-r38/routing.json',R/'capture-r26/capture.json']}
out=R/'candidate-r43';out.mkdir(exist_ok=False);(out/'signal_main.kicad_pcb').write_text(sexpr(t)+'\n');(out/'routing.json').write_text(json.dumps(new,indent=2)+'\n')
