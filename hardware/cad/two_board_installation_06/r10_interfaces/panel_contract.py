"""Bind panel logical endpoints to current actual main-board pad nets."""
from pathlib import Path
import hashlib,json,xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[4]
HERE=Path(__file__).resolve().parent
controls=Path('/private/tmp/rmx-control-carriers-20261112/hardware/cad/two_board_controls_04')
manifest=ROOT/'hardware/cad/two_board_installation_06/r7/interface-manifest.json'
firmware=ROOT/'hardware/firmware/control-inputs.json'
netlist=ROOT/'hardware/fabrication/staging/two-board-signal-routed-native-03/netlist.xml'
interfaces={x['reference']:x for x in json.loads(manifest.read_text())['interfaces'] if x['board']=='signal'}
nets={}
for n in ET.parse(netlist).findall('./nets/net'):
 for p in n.findall('node'): nets[p.attrib['ref'],p.attrib['pin']]=n.attrib['name']
def endpoint(ref,pin):
 p=next(p for p in interfaces[ref]['pads'] if p['pin']==str(pin))
 assert nets[ref,str(pin)]==p['net'],(ref,pin)
 return {'reference':ref,**p}
front=[]
for c in json.loads(firmware.read_text())['front_inputs']:
 i=c['logical_index']; matches=[endpoint(r,p['pin']) for r in ['D_J2001','D_J2002','D_J2003'] for p in interfaces[r]['pads'] if p['net'].endswith(f'/CONTROL_{i:02}')]
 assert len(matches)==1
 front.append({'id':c['id'],'logical_index':i,'active':c['active'],'signal':matches[0], 'receiver_kind':'B3F-1000 momentary' if i<29 else 'selector'})
assert len(front)==32
pots=[]
for i,name in enumerate(('input','output','low','mid','high','scene_depth','x_level','x_pitch','scene_time','scene_resonance')):
 pots.append({'id':name,'value_ohm':10000,'main':[endpoint(f'D_J{1020+i}',j) for j in (1,2,3)],'pot_terminal_assignment':{'1':'AGND','2':'wiper','3':'V3V3_ANALOG'},'direction_acceptance':'Verify wiper increases on clockwise rotation at receiving inspection; manufacturer schematic confirms wiper2 but does not label endpoint rotation.'})
selectors=[{'id':'settings','mpn':'JS202011CQN','common_pins':[2,5],'state_connections':{'a':[[2,3],[5,6]],'b':[[2,1],[5,4]]},'wires':[{'pad':'W2.1','main':endpoint('D_J2003',1)},{'pad':'W3.1','main':endpoint('D_J2003',3)}],'no_wire':['W1.1','W4.1','W5.1','W6.1'],'logical_states':{'a':'settings active','b':'settings inactive'}}, {'id':'release','mpn':'JS203011SCQN','common_pins':[3,7],'state_connections':{'a':[[3,4],[7,8]],'b':[[3,2],[7,6]],'c':[[3,1],[7,5]]},'wires':[{'pad':'W3.1','main':endpoint('D_J2003',1)},{'pad':'W1.1','main':endpoint('D_J2003',4)},{'pad':'W4.1','main':endpoint('D_J2003',5)}],'no_wire':['W2.1','W5.1','W6.1','W7.1','W8.1'],'logical_states':{'a':'vinyl brake','b':'neither input asserted','c':'back spin'}}]
sources=[manifest,firmware,netlist,controls/'selector-contract.json',controls/'reference/ck-js.pdf',controls/'led_follow_on/reference/PTV09.pdf',ROOT/'hardware/wiring/system.py']
out={'scope':'Panel electrical endpoint contract; connector selection, wire distribution, physical routing and receiving tests remain separate. Shared AGND endpoints require rated distribution, not unspecified multiple wires in a contact.','sources':[{'path':str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sources], 'manufacturer_sources':{'selectors':'C&K JS series 22 Sep 2022 p4, circuit diagrams visually inspected','pots':'https://www.bourns.com/docs/product-datasheets/PTV09.pdf p1 schematic / p3 PTV09A-6 terminal layout'},'front_inputs':front,'pots':pots,'selectors':selectors,'button_contact_assignment':'Pending exact B3F-1000 terminal diagram; do not infer pin pairs from schematic symbol orientation.','fabrication_released':False}
(HERE/'panel-contract.json').write_text(json.dumps(out,indent=2)+'\n')
print('Verified 32 control endpoints, 30 pot endpoints and 5 selector leads against current native netlist and pad inventory.')
if __name__=='__main__': pass
