import csv,json,hashlib,math
from pathlib import Path
from hardware.electronics.common.sexpr import read_sexpr,children,first
R=Path(__file__).resolve().parent;REPO=R.parents[3];board=REPO/'hardware/fabrication/staging/two-board-signal-routed-native-03/signal_main.kicad_pcb';nets={}
for f in children(read_sexpr(board.read_text()),'footprint'):
 ref={p[1]:p[2] for p in children(f,'property')}['Reference']
 if ref not in ['D_J3002','D_J3003','D_J3004','D_J3005']:continue
 for p in children(f,'pad'):nets.setdefault(first(p,'net')[-1],[]).append((ref,p[1]))
c=json.loads((R/'contract.json').read_text());designs={b['name']:b for b in c['boards']};rows=[]
for i in c['instances']:
 ch=i['channel'];net=f'/D_LED/LED_{ch:02d}';ends=nets[net];assert len(ends)==1;ref,pin=ends[0];anodes=[n for n,es in nets.items() if (ref,'25') in es];assert len(anodes)==1
 for idx,(pad,pin,net,kind) in enumerate([('W1',pin,net,'cathode'),('W2','25',anodes[0],'anode_via_rated_splice')]):
  x,y,a=i['pose'];px,py=designs[i['design']]['wires'][idx];a=math.radians(a)
  rows.append(dict(button=i['id'],design=i['design'],pad=pad,pin=1,kind=kind,channel=ch if idx==0 else '',main_connector=ref,main_pin=pin,net=net,exit_x=round(x+px*math.cos(a)-py*math.sin(a),4),exit_y=round(y+px*math.sin(a)+py*math.cos(a),4),exit_z=42.9))
assert sorted(r['channel'] for r in rows if r['kind']=='cathode')==list(range(25))
with (R/'wiring.csv').open('w') as f:
 w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
paths=[board,R/'contract.json',R/'wiring.csv',Path(__file__)]
(R/'wiring-review.json').write_text(json.dumps(dict(rows=len(rows),source_sha256={str(p.relative_to(REPO)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},scope='All25 indicator sink channels and25 individual anode leads. Connector/crimp selection, rated positive distribution and full routing remain separate.'),indent=2)+'\n')
svg=['<svg xmlns="http://www.w3.org/2000/svg" width="50mm" height="25mm" viewBox="0 0 50 25"><g fill="none" stroke="black" stroke-width="0.05">']
for n in range(50):
 x=2.5+5*(n%10);y=2.5+5*(n//10);svg.extend([f'<circle cx="{x}" cy="{y}" r="2.1"/>',f'<circle cx="{x}" cy="{y}" r="1.2"/>'])
svg.append('</g></svg>');(R/'shim-washers-0p1mm-PET.svg').write_text('\n'.join(svg)+'\n')
