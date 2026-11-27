import copy,unittest,xml.etree.ElementTree as ET
from hardware.electronics.common.sexpr import read_sexpr,children
from .verify import schematic_delta,netlist_delta
class DeltaTests(unittest.TestCase):
 def setUp(self):
  self.a=read_sexpr('(kicad_sch (symbol (uuid "u") (property "Reference" "P_C900") (property "Footprint" "old") (property "Value" "1u")))');self.b=copy.deepcopy(self.a);children(children(self.b,'symbol')[0],'property')[1][2]='AUX_ROUTE:new';self.changes={'P_C900':{'before':'old','after':'AUX_ROUTE:new'}}
 def test_declared_field(self):schematic_delta(self.a,self.b,self.changes)
 def test_value_change_rejected(self):
  children(children(self.b,'symbol')[0],'property')[2][2]='10u'
  with self.assertRaises(AssertionError):schematic_delta(self.a,self.b,self.changes)
 def test_uuid_change_rejected(self):
  children(children(self.b,'symbol')[0],'uuid')[0][1]='wrong'
  with self.assertRaises(AssertionError):schematic_delta(self.a,self.b,self.changes)
 def test_unexpected_pin_rejected(self):
  a=ET.ElementTree(ET.fromstring('<export><components/><nets><net name="GND"><node ref="X" pin="1"/></net></nets></export>'));b=copy.deepcopy(a);ET.SubElement(b.find('./nets/net'),'node',ref='X',pin='2')
  with self.assertRaises(AssertionError):netlist_delta(a,b,{})
 def test_renet_rejected(self):
  a=ET.ElementTree(ET.fromstring('<export><components/><nets><net name="GND"><node ref="X" pin="1"/></net></nets></export>'));b=copy.deepcopy(a);b.find('./nets/net').set('name','VCC')
  with self.assertRaises(AssertionError):netlist_delta(a,b,{})
