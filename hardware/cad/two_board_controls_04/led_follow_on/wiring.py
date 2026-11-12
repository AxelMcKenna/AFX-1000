"""Bind the 44 implemented meter/bank sinks to actual integrated main-board nets."""
import csv,json,hashlib
from pathlib import Path
from hardware.electronics.common.sexpr import read_sexpr,children,first
R=Path(__file__).resolve().parent;REPO=R.parents[3]
board=REPO/'hardware/fabrication/staging/two-board-signal-routed-native-03/signal_main.kicad_pcb'
channel=REPO/'hardware/electronics/led_driver/generated/channel-map.csv'
nets={}
for f in children(read_sexpr(board.read_text()),'footprint'):
 ref={p[1]:p[2] for p in children(f,'property')}['Reference']
 if ref not in ['D_J3002','D_J3003','D_J3004','D_J3005']:continue
 for p in children(f,'pad'):nets.setdefault(first(p,'net')[-1],[]).append((ref,p[1]))
channels={int(r['Logical_channel']):r['Function'] for r in csv.DictReader(channel.open())};rows=[]
for ch in range(25,69):
 name=channels[ch];ends=nets[f'/D_LED/LED_{ch:02d}'];assert len(ends)==1
 target='meter_input' if ch<45 else 'meter_output' if ch<65 else 'bank_'+str(ch-65)
 pad='W'+str(ch-24 if ch<45 else ch-44 if ch<65 else 1)
 rows.append(dict(board=target,pad=pad,pin=1,function=name,channel=ch,main_connector=ends[0][0],main_pin=ends[0][1],net=f'/D_LED/LED_{ch:02d}'))
# Each board has one dedicated positive lead; approved harness splices distribute supply.
for target,ref,pad in [('meter_input','D_J3003','WA'),('meter_output','D_J3004','WA')]+[('bank_'+str(i),'D_J3004','W2') for i in range(4)]:
 match=[net for net,ends in nets.items() if (ref,'25') in ends];assert len(match)==1
 rows.append(dict(board=target,pad=pad,pin=1,function='common_anode_supply_via_splice',channel='',main_connector=ref,main_pin=25,net=match[0]))
with (R/'wiring.csv').open('w') as f:
 w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
paths=[board,channel,Path(__file__),R/'wiring.csv']
(R/'wiring-review.json').write_text(json.dumps(dict(rows=len(rows),sink_channels=44,anode_leads=6,source_sha256={str(p.relative_to(REPO)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},limitations=['Anode supplies require properly rated harness splices, not multiple wires in one crimp.','Local CAD includes lead exit reserves only; complete harness routing/strain relief is separate.','Meter colors and brightness require final population/optical acceptance.']),indent=2)+'\n')
