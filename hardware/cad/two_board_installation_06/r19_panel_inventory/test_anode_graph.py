import copy,json,unittest,xml.etree.ElementTree as ET
from pathlib import Path
from hardware.cad.two_board_installation_06.r19_panel_inventory.anode_graph import validate_anodes
BASE=Path(__file__).resolve().parent.parent
class AnodeMutationTests(unittest.TestCase):
 def setUp(self):
  self.a=json.loads((BASE/'r11_distribution/anode-topology.json').read_text())
  self.n={(x.get('ref'),x.get('pin')):net.get('name') for net in ET.parse(BASE/'r11_distribution/reference/signal-netlist.xml').findall('.//nets/net') for x in net.findall('node')}
  self.p={(i['reference'],p['pin']):p for i in json.loads((BASE/'r7/interface-manifest.json').read_text())['interfaces'] for p in i['pads']}
 def check(self):return validate_anodes(self.a,self.n,self.p)
 def test_current(self):self.assertEqual(self.check()['segments'],72)
 def test_wrong_native_root(self):
  self.n['D_J3002','25']='LINK_AGND'
  with self.assertRaises(AssertionError):self.check()
 def test_wrong_captured_root(self):
  self.p['D_J3002','25']['net']='LINK_AGND'
  with self.assertRaises(AssertionError):self.check()
 def test_disconnected_receiver(self):
  self.a['edges']=[e for e in self.a['edges'] if e['to']!=self.a['receivers']['D_J3002'][0]['id']]
  with self.assertRaises(AssertionError):self.check()
 def test_cycle(self):
  e=next(e for e in self.a['edges'] if e['from'].endswith(':OUT_A'));e['to']=e['from'].rsplit(':',1)[0]+':IN'
  with self.assertRaises(AssertionError):self.check()
 def test_wrong_feed(self):
  e=[e for e in self.a['edges'] if e['from'].startswith('D_J')];e[0]['to'],e[1]['to']=e[1]['to'],e[0]['to']
  with self.assertRaises(AssertionError):self.check()
if __name__=='__main__':unittest.main()
