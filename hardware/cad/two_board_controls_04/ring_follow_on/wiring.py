import csv,json,hashlib
from pathlib import Path
from hardware.electronics.common.sexpr import read_sexpr,children,first
R=Path(__file__).resolve().parent;REPO=R.parents[3];board=REPO/'hardware/fabrication/staging/two-board-signal-routed-native-03/signal_main.kicad_pcb';nets={}
for f in children(read_sexpr(board.read_text()),'footprint'):
 ref={p[1]:p[2] for p in children(f,'property')}['Reference']
 if ref not in ['D_J3002','D_J3003','D_J3004','D_J3005']:continue
 for p in children(f,'pad'):nets.setdefault(first(p,'net')[-1],[]).append((ref,p[1]))
rows=[]
for i,color in enumerate(['red','green','blue']):
 net=f'/D_LED/LED_{93+i}';ends=nets[net];assert len(ends)==1
 rows.append(dict(ring_pad=f'W{i+2}',pin=1,function=color,logical_channel=93+i,connector=ends[0][0],main_pin=ends[0][1],net=net))
ref=rows[0]['connector'];anodes=[net for net,ends in nets.items() if (ref,'25') in ends];assert len(anodes)==1
rows.append(dict(ring_pad='W1',pin=1,function='common_anode',logical_channel='',connector=ref,main_pin='25',net=anodes[0]))
with (R/'wiring.csv').open('w') as f:
 w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
paths=[board,R/'ring.kicad_pcb',R/'wiring.csv',Path(__file__)]
(R/'wiring-review.json').write_text(json.dumps(dict(source_sha256={str(p.relative_to(REPO)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},scope='Four-wire mapping only; three sink channels shared across eight RGB packages with24 branch resistors. Current sharing/brightness and complete wire routing require powered acceptance.'),indent=2)+'\n')
