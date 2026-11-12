"""Resolve BPM segment harness against the actual integrated signal board."""
import csv,json,hashlib
from pathlib import Path
from hardware.electronics.common.sexpr import read_sexpr,children,first
R=Path(__file__).resolve().parent;REPO=R.parents[2]
board=REPO/'hardware/fabrication/staging/two-board-signal-routed-native-03/signal_main.kicad_pcb'
channel=REPO/'hardware/electronics/led_driver/generated/channel-map.csv'
t=read_sexpr(board.read_text());nets={}
for f in children(t,'footprint'):
 props={p[1]:p[2] for p in children(f,'property')};ref=props['Reference']
 if ref not in ['D_J3002','D_J3003','D_J3004','D_J3005']:continue
 for p in children(f,'pad'):
  net=first(p,'net');nets.setdefault(net[-1],[]).append((ref,p[1]))
channels={r['Function']:int(r['Logical_channel']) for r in csv.DictReader(channel.open())}
segment_pins={'a':10,'b':9,'c':8,'d':5,'e':4,'f':2,'g':3,'dp':7};rows=[]
for digit in range(3):
 for seg,pin in segment_pins.items():
  ch=channels[f'digit_{digit}_{seg}'];net=f'/D_LED/LED_{ch:02d}';ends=nets[net];assert len(ends)==1
  rows.append(dict(display=f'DIGIT{digit}',manufacturer_pin=pin,function=seg,logical_channel=ch,main_connector=ends[0][0],main_pin=ends[0][1],net=net))
 for pin in [1,6]:
  # Each anode gets its own lead; joined only at the main header supply.
  ref='D_J3004' if digit==2 else 'D_J3005';ends=[(n,e) for n,es in nets.items() for e in es if e==(ref,'25')];assert len(ends)==1
  rows.append(dict(display=f'DIGIT{digit}',manufacturer_pin=pin,function='common_anode',logical_channel='',main_connector=ref,main_pin='25',net=ends[0][0]))
with (R/'display-wiring.csv').open('w') as f:
 w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
(R/'display-wiring-review.json').write_text(json.dumps(dict(rows=len(rows),source_sha256={str(p.relative_to(REPO)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [board,channel,Path(__file__),R/'display-wiring.csv']},scope='Source-bound pin mapping; crimp/splice capacity, conductor choice and route still require full harness acceptance'),indent=2)+'\n')
