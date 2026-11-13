"""Add exactly two buffered-reference joins, preserving every existing authored object."""
import json,hashlib,uuid
from pathlib import Path
from hardware.electronics.common.sexpr import read_sexpr,sexpr,a
R=Path(__file__).resolve().parent;REPO=R.parents[3];plan=json.loads((R/'adc-surface-r130.json').read_text());t=read_sexpr((R/'native-r125/signal_main.kicad_pcb').read_text());assert len(plan['routes'])==2
for j,row in enumerate(plan['routes']):
 for i,(p,q)in enumerate(zip(row['path_mm'],row['path_mm'][1:])):t.append([a('segment'),[a('start'),*[round(v,6)for v in p]],[a('end'),*[round(v,6)for v in q]],[a('width'),.2],[a('layer'),'F.Cu'],[a('net'),row['net']],[a('uuid'),str(uuid.uuid5(uuid.NAMESPACE_URL,f'TBH-ADC-r131-{j}-{i}'))]])
r={'routes':plan['routes'],'vias':[],'transitions':[],'declared_removed':[],'expected_opens':164,'all_existing_authored_objects_unchanged':True,'analog_qualified':False,'source_sha256':{str(p.relative_to(REPO)):hashlib.sha256(p.read_bytes()).hexdigest()for p in [Path(__file__),R/'adc-surface-r130.json',R/'native-r125/signal_main.kicad_pcb',R/'native-r125/signal_main.kicad_dru']}}
o=R/'candidate-r131';o.mkdir();(o/'signal_main.kicad_pcb').write_text(sexpr(t)+'\n');(o/'signal_main.kicad_dru').write_bytes((R/'native-r125/signal_main.kicad_dru').read_bytes());(o/'routing.json').write_text(json.dumps(r,indent=2)+'\n');print('two surface joins, no poses/vias/rework')
