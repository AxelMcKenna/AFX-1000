"""Exact remaining panel wire/cavity inventory against frozen native netlist."""
from pathlib import Path
import json,csv,hashlib,xml.etree.ElementTree as ET
from collections import Counter
HERE=Path(__file__).resolve().parent;BASE=HERE.parent;REPO=HERE.parents[3];sources=[]
def read(p):sources.append(p);return json.loads(p.read_text())
p=read(BASE/'r11_distribution/reference/panel-contract.json');a=read(BASE/'r11_distribution/anode-topology.json');g=read(BASE/'r15_right_ground/ground-contract.json');interfaces=read(BASE/'r7/interface-manifest.json');mates=read(BASE/'r10_interfaces/mate-envelopes.json')
x=BASE/'r11_distribution/reference/signal-netlist.xml';sources.append(x)
nets={(node.get('ref'),node.get('pin')):net.get('name') for net in ET.parse(x).findall('.//nets/net') for node in net.findall('node')}
pads={(i['reference'],v['pin']):v for i in interfaces['interfaces'] for v in i['pads']}
wires=[]
def add(kind,ref,pin,net,target):
 assert nets[ref,pin]==net and pads[ref,pin]['net']==net
 wires.append(dict(kind=kind,source=ref+':'+pin,net=net,target=target,source_xy_mm=pads[ref,pin]['xy'],status='unrouted'))
selectors={int(w['main']['net'].split('_')[-1]):s['id']+':'+w['pad'] for s in p['selectors'] for w in s['wires'] if 'CONTROL_' in w['main']['net']}
for i in p['front_inputs']:
 v=i['signal'];add('input_signal',v['reference'],v['pin'],v['net'],selectors.get(i['logical_index'],'button_'+i['id']+':1'))
for pot in p['pots']:
 for v in pot['main']:add('pot',v['reference'],v['pin'],v['net'],'pot_'+pot['id']+':'+v['pin'])
for name in ['button_follow_on/wiring.csv','led_follow_on/wiring.csv','ring_follow_on/wiring.csv','display-wiring.csv']:
 path=BASE/'r11_distribution/reference'/name;sources.append(path)
 for row in csv.DictReader(path.open()):
  if not row['net'].startswith('/D_LED/LED_'):continue
  ref=row.get('main_connector',row.get('connector'));pin=row['main_pin']
  if 'button' in row:target='button_indicator_'+row['button']+':'+row['pad']+'.'+row['pin']
  elif 'board' in row:target=row['board']+':'+row['pad']+'.'+row['pin']
  elif 'ring_pad' in row:target='touch_ring:'+row['ring_pad']+'.'+row['pin']
  else:target=row['display']+':'+row['manufacturer_pin']
  add('led_sink',ref,pin,row['net'],target)
for e in a['edges']:
 wires.append(dict(kind='anode_distribution',source=e['from'],target=e['to'],net='D__5V_DIG',status='topology_only_unrouted'))
counts=dict(Counter(w['kind'] for w in wires));assert counts==dict(input_signal=32,pot=30,led_sink=96,anode_distribution=72)
used={w['source'] for w in wires if w['source'].startswith('D_J')};used|={'D_J2002:15','D_J2002:16'}
assert len(used)==164
refs={key.split(':')[0] for key in used};selected={m['ref'] for m in mates['mates']};cavities=[]
for ref,pin in sorted(pads):
 if ref not in refs:continue
 key=ref+':'+pin;cavities.append(dict(id=key,net=nets[ref,pin],used=key in used,xy_mm=pads[ref,pin]['xy'],mate_status='conditional_receiving_selected' if ref in selected else 'unselected',outgoing_wires=[w for w in wires if w['source']==key],ground_feed=key in ['D_J2002:15','D_J2002:16']))
assert len(cavities)==171
assert {c['id'] for c in cavities if not c['used']}=={'D_J2001:15','D_J2001:16','D_J2003:1',*[f'D_J300{i}:26' for i in range(2,6)]}
assert len({w['source'] for w in wires if w['kind']!='anode_distribution'})==158
sources.append(Path(__file__))
out=dict(source_sha256={str(f.relative_to(REPO)):hashlib.sha256(f.read_bytes()).hexdigest() for f in sources},counts=counts,remaining_unrouted_segments=230,formed_ground_segments=32,planned_total_external_segments=262,anode_splices=34,anode_receivers=38,main_header_cavities=171,used_cavities=164,unused_cavities=7,cavities=cavities,wires=wires,scope='Panel inputs, pots and LED sinks/anode distribution only. Other installation interfaces remain in r7 inventory. Ground follows r15 rather than superseded r11 ground topology.',complete_harness=False,fabrication_released=False)
(HERE/'inventory.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(counts))
