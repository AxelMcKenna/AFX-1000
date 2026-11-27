"""Explicit five-root control ground trees, with no shared contact cavities."""
from pathlib import Path
import json,hashlib,collections,xml.etree.ElementTree as ET
HERE=Path(__file__).resolve().parent
contract=json.loads((HERE/'reference/panel-contract.json').read_text())
netlist=ET.parse(HERE/'reference/signal-netlist.xml')
pins={(n.get('ref'),n.get('pin')):net.get('name')for net in netlist.findall('./nets/net')for n in net.findall('node')}
groups=collections.defaultdict(list)
buttons=[r for r in contract['front_inputs']if r['receiver_kind']=='B3F-1000 momentary']
for header in ['D_J2001','D_J2002']:
 rows=sorted((r for r in buttons if r['signal']['reference']==header),key=lambda r:r['logical_index']);assert len(rows)==14
 for i,r in enumerate(rows):groups[header+(':'+str(15+i//7))].append({'id':'button_'+r['id']+':3','receiver':'button_'+r['id'],'terminal':'3'})
for r in buttons:
 if r['signal']['reference']=='D_J2003':groups['D_J2003:1'].append({'id':'button_'+r['id']+':3','receiver':'button_'+r['id'],'terminal':'3'})
for r in contract['selectors']:
 ground=[w for w in r['wires']if w['main']['net']=='LINK_AGND'];assert len(ground)==1
 w=ground[0];groups[w['main']['reference']+':'+w['main']['pin']].append({'id':r['id']+':'+w['pad'],'receiver':r['id'],'terminal':w['pad']})
nodes=[];edges=[]
for root,leaves in sorted(groups.items()):
 ref,pin=root.split(':');assert pins[ref,pin]=='LINK_AGND';counter=[0]
 def tree(rows,up):
  if len(rows)==1:edges.append({'from':up,'to':rows[0]['id'],'wire':'Alpha5853 26AWG7/34'});return
  counter[0]+=1;name='GROUND_'+root.replace(':','_')+'_'+str(counter[0]).zfill(2)
  nodes.append({'id':name,'net':'LINK_AGND','hardware':'TE34130','ports':['IN','OUT_A','OUT_B'],'wire_count':3,'insulation':'TE505872P034 receiving condition'})
  edges.append({'from':up,'to':name+':IN','wire':'Alpha5853 26AWG7/34'})
  mid=(len(rows)+1)//2;tree(rows[:mid],name+':OUT_A');tree(rows[mid:],name+':OUT_B')
 tree(leaves,root)
assert len(nodes)==26 and len(edges)==57 and sum(map(len,groups.values()))==31
ports=collections.Counter(v for e in edges for v in [e['from'],e['to']]);assert set(ports.values())=={1}
assert set(r['id']for rows in groups.values()for r in rows)=={'button_'+r['id']+':3'for r in buttons}|{'settings:W2.1','release:W3.1'}
out={'net':'LINK_AGND','sources':{str(p.relative_to(HERE)):hashlib.sha256(p.read_bytes()).hexdigest()for p in [Path(__file__),HERE/'reference/panel-contract.json',HERE/'reference/signal-netlist.xml']},'groups':groups,'nodes':nodes,'edges':edges,'scope':'Five independently wired ground trees terminating existing same-net main-board pins. All29buttons plus2selectorcommons represented. One wire/contact orspliceport. Mainboard common ground remains, no extra panelPCB. Input pullup/fault current and physical routing stillrequireverification.','fabrication_released':False}
(HERE/'ground-topology.json').write_text(json.dumps(out,indent=2)+'\n');print('Ground:31receivers26junctions57wires5roots')
