import copy,json,unittest,xml.etree.ElementTree as ET
from pathlib import Path
from .verify import semantic,route_identity
H=Path(__file__).resolve().parent
class LocalTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.old=ET.parse(H.parent/'footprint_identity/native-01/candidate-netlist.xml');cls.new=ET.parse(H/'native-07/candidate-netlist.xml');cls.plan=json.loads((H/'direct-return-plan.json').read_text());cls.capture=json.loads((H/'capture-01/capture.json').read_text())
 def test_declared_semantic(self):semantic(self.old,self.new);route_identity(self.plan,self.capture)
 def test_extra_pin_rejected(self):
  b=copy.deepcopy(self.new);ET.SubElement(b.find('./nets/net'),'node',ref='P_C907',pin='3')
  with self.assertRaises(AssertionError):semantic(self.old,b)
 def test_old_pin_renet_rejected(self):
  b=copy.deepcopy(self.new);n=b.find('./nets/net');n.set('name','wrong')
  with self.assertRaises(AssertionError):semantic(self.old,b)
 def test_old_value_rejected(self):
  b=copy.deepcopy(self.new);b.find('./components/comp/value').text='wrong'
  with self.assertRaises(AssertionError):semantic(self.old,b)
 def test_ground_target_identity_rejected(self):
  p=copy.deepcopy(self.plan);p['routes'][1]['target']='P_U102.3'
  with self.assertRaises(AssertionError):route_identity(p,self.capture)
 def test_ground_pad_renet_rejected(self):
  c=copy.deepcopy(self.capture);next(o for o in c['objects'] if o.get('ref')=='P_U102' and o.get('pin')=='9')['net']='TT'
  with self.assertRaises(AssertionError):route_identity(self.plan,c)

from .immutable_inputs import check_recorded
class InputHashTests(unittest.TestCase):
 def test_exact_host_and_native_hashes(self):check_recorded({'status':'passed','input_sha256':{'p':'new'},'inputs_unchanged':{'p':True}},{'p':'new'})
 def test_stale_native_unchanged_true_rejected(self):
  with self.assertRaises(AssertionError):check_recorded({'status':'passed','input_sha256':{'p':'old'},'inputs_unchanged':{'p':True}},{'p':'new'})
 def test_missing_native_input_rejected(self):
  with self.assertRaises(AssertionError):check_recorded({'status':'passed','input_sha256':{},'inputs_unchanged':{}},{'p':'new'})
 def test_extra_native_input_rejected(self):
  with self.assertRaises(AssertionError):check_recorded({'status':'passed','input_sha256':{'p':'new','extra':'x'},'inputs_unchanged':{'p':True,'extra':True}},{'p':'new'})
