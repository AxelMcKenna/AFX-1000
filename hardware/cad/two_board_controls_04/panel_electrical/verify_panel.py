"""Independent exported-netlist functional checks and defect-injection tests."""
import sys,json,csv,copy,hashlib
from collections import Counter
from contracts import *
sys.path.insert(0,str(REPO/'hardware/electronics'))
from common.netlists import netlist
from common.sexpr import *

def verify(pins,m):
 instances={x['instance']:x for x in m['passive_board_instances']}
 assert len(instances)==34
 assert Counter(x['design'] for x in instances.values())==dict(settings=1,release=1,meter_input=1,meter_output=1,bank=4,ring=1,vertical=8,horizontal=2,scene=10,pad=3,pad1=1,vertical_top=1)
 def pin(instance,ref,num):return pins[instances[instance]['ref_map'][ref]][str(num)]
 # Assembly subgraph must be identical to each independent local circuit and frozen PCB.
 for name,inst in instances.items():
  spec=contract(inst['design'])
  for c in spec['components']:
   for p in c['pins']:assert pin(name,c['ref'],p['number'])==inst['net_map'][p['net']],(name,c['ref'],p)
 # Independently trace every logical function to its actual LED cathode, not just a manifest count.
 functions=list(csv.DictReader((REPO/'hardware/electronics/led_driver/generated/channel-map.csv').open()))
 for row in functions:
  ch=int(row['Logical_channel']);f=row['Function'];expected=f'D_LED__LED_{ch:02d}'
  if ch<25:assert pin(f,'D1',1)==expected and pin(f,'D1',2)=='D__5V_DIG'
  elif ch<65:
   b='meter_input' if ch<45 else 'meter_output';i=ch-(25 if ch<45 else 45)
   assert pin(b,'D'+str(i+1),1)==expected and pin(b,'D'+str(i+1),2)=='D__5V_DIG'
  elif ch<69:assert pin(f,'D1',1)==expected and pin(f,'D1',2)=='D__5V_DIG'
  elif ch<93:
   digit=(ch-69)//8;segment=(ch-69)%8;ref='DS'+str(digit+1)
   assert pins[ref][str([10,9,8,5,4,2,3,7][segment])]==expected
   assert pins[ref]['1']==pins[ref]['6']=='D__5V_DIG'
  else:
   color=ch-93
   for i in range(8):
    led='D'+str(i+1);res='R'+str(i*3+color+1);branch=pin('ring',led,color+2)
    assert pin('ring',led,1)=='D__5V_DIG'
    assert {pin('ring',res,1),pin('ring',res,2)}=={branch,expected}
    assert branch!=expected
 # Every channel and referenced common supply reaches exactly its native main-header boundary pin.
 mainpcb=read_sexpr((REPO/'hardware/fabrication/staging/two-board-signal-routed-native-03/signal_main.kicad_pcb').read_text());native={}
 for f in children(mainpcb,'footprint'):
  props={p[1]:p[2] for p in children(f,'property')}
  for p in children(f,'pad'):
   n=children(p,'net')
   if n:native[(props['Reference'],p[1])]=n[0][-1]
 boundaries={c['part'].split()[0]:c['ref'] for c in m['components'] if c['part'].endswith(' MAIN_BOUNDARY')}
 for e in m['main_boundary']:
  assert native[(e['reference'],e['pin'])]==e['net']
  assert pins[boundaries[e['reference']]][e['pin']]==e['net'].strip('/').replace('/','__')
 for ch in range(96):assert sum(n==f'D_LED__LED_{ch:02d}' for ref in boundaries.values() for n in pins[ref].values())==1
 # Exercise the switch truth tables, including unused poles and center-off release wiring.
 iface=json.loads((R/'reference/panel-contract.json').read_text())
 wanted={'settings':{'a':{29},'b':set()},'release':{'a':{31},'b':set(),'c':{30}}}
 for selector in iface['selectors']:
  name=selector['id']
  for state,pairs in selector['state_connections'].items():
   active=set()
   for a,b in pairs:
    nets={pin(name,'SW1',a),pin(name,'SW1',b)}
    if 'LINK_AGND' in nets:
     for n in nets:
      if n.startswith('D_CONTROLS__CONTROL_'):active.add(int(n.rsplit('_',1)[1]))
   assert active==wanted[name][state],(name,state,active)
 for i,front in enumerate(iface['front_inputs']):
  if front['receiver_kind']!='B3F-1000 momentary':continue
  ps=pins['SW'+str(900+i)];assert ps['1']==ps['2']==front['signal']['net'].strip('/').replace('/','__');assert ps['3']==ps['4']=='LINK_AGND'
 for i,pot in enumerate(iface['pots']):
  ps=pins['RV'+str(i+1)]
  assert ps=={e['pin']:e['net'].strip('/').replace('/','__') for e in pot['main']}
 return dict(passive_instances=34,distinct_layouts=12,sink_channels=96,momentary_controls=29,selector_states=5,potentiometers=10,direct_display_digits=3,rgb_branches=24,native_main_boundary_parity=True)
if __name__=='__main__':
 out=R/sys.argv[1];parts,pins=netlist(out/'netlist.xml');m=json.loads((R/'assembly-manifest.json').read_text());review=verify(pins,m);mutations={}
 def reject(name,mutator):
  p=copy.deepcopy(pins);mutator(p)
  try:verify(p,m)
  except AssertionError:mutations[name]='rejected'
  else:raise AssertionError('Verifier accepted '+name)
 inst={x['instance']:x for x in m['passive_board_instances']}
 def flip(p):
  ref=inst['quantize']['ref_map']['D1'];p[ref]['1'],p[ref]['2']=p[ref]['2'],p[ref]['1']
 reject('reversed_button_LED_polarity',flip)
 reject('wrong_display_segment',lambda p:p['DS1'].update({'10':'D_LED__LED_70'}))
 reject('missing_ring_branch_resistor_connection',lambda p:p[inst['ring']['ref_map']['R1']].update({'2':'BROKEN'}))
 reject('selector_common_ground_lost',lambda p:p[inst['release']['ref_map']['SW1']].update({'3':'BROKEN'}))
 reject('wrong_pot_wiper',lambda p:p['RV1'].update({'2':'LINK_AGND'}))
 review['fault_injection']=mutations
 sourcepaths=[R/'contracts.py',R/'generate.py',R/'panel.py',R/'assembly-manifest.json',R/'verify_panel.py',R/'native.py',R/'assembly_native.py',R/'reference/panel-contract.json',R/'reference/button-contact-contract.json']+[CONTROLS/p for p,l in DESIGNS.values()]+list((R/'assembly').rglob('*.kicad_sch'))+list((R/'layouts').rglob('*.kicad_sch'))
 review['source_sha256']={str(p.relative_to(CONTROLS)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sourcepaths}
 (out/'functional-review.json').write_text(json.dumps(review,indent=2)+'\n');print({k:v for k,v in review.items() if k!='source_sha256'})
